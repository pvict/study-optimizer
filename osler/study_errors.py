"""Erros declarados pelo usuário, com histórico aditivo e sinal conservador."""
from collections import Counter
import csv
from dataclasses import asdict, dataclass
from io import StringIO
import json
import re
import uuid

from .exports import _safe_cell
from .models import normalize_path
from .planning import _date
from .planner_service import today_local, valid_date
from .storage import utc_now
from .study_storage import StudyStore


CAUSES = {
    'lacuna_de_conteudo': 'Lacuna de conteúdo',
    'confundiu_conceitos': 'Confundi conceitos',
    'erro_de_atencao_ou_interpretacao': 'Atenção ou interpretação',
    'chute': 'Chute',
    'nao_lembrei_conduta_ou_dose': 'Não lembrei a conduta ou dose',
    'outro': 'Outro motivo',
}


@dataclass(frozen=True)
class StudyError:
    path: list[str]
    day: str
    cause: str
    note: str = ''
    source_session_id: str | None = None
    critical: bool = False
    flashcard_hint: str | None = None

    def validate(self):
        if not isinstance(self.path, list) or not self.path or any(not isinstance(p, str) or not p.strip() for p in self.path):
            raise ValueError('Escolha um tema específico pelo caminho completo.')
        _date(self.day)
        if not isinstance(self.cause, str) or self.cause not in CAUSES:
            raise ValueError('Escolha o motivo do erro.')
        if not isinstance(self.note, str) or len(self.note) > 280:
            raise ValueError('Resuma o conceito que faltou em até 280 caracteres.')
        if type(self.critical) is not bool:
            raise ValueError('Marcação de erro crítico inválida.')
        if self.source_session_id is not None and (not isinstance(self.source_session_id, str) or not re.fullmatch(r'[\w.-]{1,128}', self.source_session_id)):
            raise ValueError('Sessão de origem inválida.')
        if self.flashcard_hint is not None and (not isinstance(self.flashcard_hint, str) or len(self.flashcard_hint) > 280):
            raise ValueError('Resuma a ideia para o cartão em até 280 caracteres.')
        return self

    def to_dict(self):
        return asdict(self)


def _record(row):
    return {**dict(row), 'path': json.loads(row['topic_path']), 'critical': bool(row['critical'])}


def _active_events(events, as_of):
    _date(as_of)
    latest = {}
    for event in events:
        latest[event['error_key']] = event
    return sorted((e for e in latest.values() if e['action'] == 'save' and e['day'] <= as_of),
                  key=lambda e: (e['day'], e['id']), reverse=True)


def adverse_error_paths(repo, as_of):
    """Consulta pura para fluxos antigos: não inicializa Store nem migra schema."""
    day = _date(as_of)
    with repo._connection() as db:
        if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='study_errors'").fetchone():
            return []
        events = [_record(row) for row in db.execute('SELECT * FROM study_errors ORDER BY id')]
    opened = _active_events(events, as_of)
    counts = Counter((tuple(e['path']), e['cause']) for e in opened if 0 <= (day - _date(e['day'])).days <= 30)
    paths = {tuple(e['path']) for e in opened if e['critical']}
    paths.update(path for (path, _cause), count in counts.items() if count >= 2)
    return sorted(paths)


class ErrorStore:
    def __init__(self, repo, catalog=None):
        self.repository = repo
        self.catalog = catalog
        StudyStore(repo)
        from .lote_b_schema import migrate_lote_b
        with repo._connection() as db:
            migrate_lote_b(db)

    def events(self):
        with self.repository._connection() as db:
            return [_record(row) for row in db.execute('SELECT * FROM study_errors ORDER BY id')]

    def active(self, as_of):
        """Último estado de cada erro, limitado à data declarada do registro.

        Assim como StudyStore, usa as correções atuais, sem ressuscitar erros
        resolvidos ao consultar uma data anterior. Não é replay por timestamp.
        """
        return _active_events(self.events(), as_of)

    def adverse_paths(self, as_of):
        return adverse_error_paths(self.repository, as_of)

    def _validate_catalog(self, error):
        if self.catalog is None:
            return
        topics = self.catalog(today_local().isoformat(), include_parents=True)[0] if callable(self.catalog) else self.catalog
        path = normalize_path(error.path)
        matches = [t for t in topics if normalize_path(t['path']) == path]
        if len(matches) != 1 or not matches[0].get('is_leaf', True):
            raise ValueError('Escolha um tema específico reconhecido de forma única no relatório atual.')

    def _append(self, error, error_key, expected_version, action):
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError('Versão do erro inválida.')
        if not isinstance(error_key, str) or not re.fullmatch(r'[\w.-]{1,128}', error_key):
            raise ValueError('Identificador de erro inválido.')
        if action == 'save':
            error.validate()
            valid_date(error.day, past=True)
            self._validate_catalog(error)
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            last = db.execute('SELECT * FROM study_errors WHERE error_key=? ORDER BY version DESC LIMIT 1', (error_key,)).fetchone()
            if (last['version'] if last else 0) != expected_version or (action != 'save' and (not last or last['action'] != 'save')):
                raise ValueError('O erro foi atualizado em outra tela. Reabra antes de salvar.')
            if action == 'save':
                path = normalize_path(error.path)
                if error.source_session_id is not None:
                    session = db.execute('SELECT * FROM study_events WHERE session_id=? ORDER BY version DESC LIMIT 1', (error.source_session_id,)).fetchone()
                    entry = json.loads(session['payload']) if session else None
                    if not session or session['action'] != 'save' or normalize_path(entry['path']) != path or entry['day'] != error.day:
                        raise ValueError('A sessão de origem mudou ou pertence a outro tema ou dia. Reabra o registro.')
                values = (json.dumps(path, ensure_ascii=False), error.day, error.source_session_id,
                          error.cause, error.note.strip(), int(error.critical), error.flashcard_hint)
            else:
                values = tuple(last[k] for k in ('topic_path', 'day', 'source_session_id', 'cause', 'note', 'critical', 'flashcard_hint'))
            event_id = db.execute('''INSERT INTO study_errors
                (error_key,version,action,topic_path,day,source_session_id,cause,note,critical,flashcard_hint,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                (error_key, expected_version + 1, action, *values, utc_now())).lastrowid
            return _record(db.execute('SELECT * FROM study_errors WHERE id=?', (event_id,)).fetchone())

    def save(self, error, *, error_key=None, expected_version=0):
        return self._append(error, uuid.uuid4().hex if error_key is None else error_key, expected_version, 'save')

    def resolve(self, error_key, expected_version):
        return self._append(None, error_key, expected_version, 'resolve')

    def void(self, error_key, expected_version):
        return self._append(None, error_key, expected_version, 'void')

    def export_csv(self):
        """Todas as versões, incluindo resolução e desconsideração."""
        stream = StringIO(newline='')
        columns = ['id', 'error_key', 'version', 'action', 'topic_path', 'day', 'source_session_id',
                   'cause', 'note', 'critical', 'flashcard_hint', 'created_at']
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter=';', lineterminator='\n')
        writer.writeheader()
        for event in self.events():
            writer.writerow({key: _safe_cell(event[key]) for key in columns})
        return stream.getvalue().encode('utf-8-sig')
