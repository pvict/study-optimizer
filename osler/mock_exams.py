"""Simulados locais versionados; a conversão de temas em blocos é sempre explícita."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import uuid

from .models import normalize_path
from .planning import _date, _number
from .planner_service import today_local, valid_date
from .review_queue import review_queue
from .storage import utc_now
from .study_models import StudyEntry
from .study_storage import StudyStore, _encoded


@dataclass(frozen=True)
class MockExam:
    day: str
    questions: int
    correct: int
    kind: str = 'outro'
    institution: str | None = None
    target_id: str | None = None
    name: str = 'Simulado'
    blank: int | None = None
    minutes_used: float | None = None
    minutes_allowed: float | None = None
    score: float | None = None
    max_score: float | None = None
    conditions: str = 'nao_realista'
    unseen_questions: bool = False
    note: str = ''
    areas: list[dict] = field(default_factory=list)
    topics: list[dict] = field(default_factory=list)

    def validate(self):
        _date(self.day)
        _number(self.questions, 'Questões', integer=True, positive=True, maximum=1000000)
        _number(self.correct, 'Acertos', integer=True, maximum=self.questions)
        if self.blank is not None:
            _number(self.blank, 'Em branco', integer=True, maximum=self.questions-self.correct)
        for value in (self.minutes_used, self.minutes_allowed):
            if value is not None: _number(value, 'Minutos', positive=True, maximum=1440)
        if (self.score is None) != (self.max_score is None):
            raise ValueError('Informe a nota e a nota máxima juntas, ou deixe ambas vazias.')
        if self.score is not None:
            _number(self.max_score, 'Nota máxima', positive=True)
            _number(self.score, 'Nota', maximum=self.max_score)
        if self.kind not in {'prova_anterior', 'simulado_cursinho', 'outro'}:
            raise ValueError('Escolha o tipo de simulado.')
        if self.conditions not in {'realista', 'nao_realista'} or type(self.unseen_questions) is not bool:
            raise ValueError('Informe as condições e se as questões eram inéditas.')
        for value, label, maximum in ((self.name, 'Nome', 160), (self.note, 'Observação', 1000)):
            if not isinstance(value, str) or len(value)>maximum or label=='Nome' and not value.strip():
                raise ValueError(f'{label} inválido.')
        for value in (self.institution, self.target_id):
            if value is not None and (not isinstance(value, str) or not value.strip() or len(value)>200):
                raise ValueError('Instituição ou prova inválida.')
        for rows, identity in ((self.areas, 'area'), (self.topics, 'path')):
            if not isinstance(rows, list): raise ValueError('Resultados detalhados inválidos.')
            keys = []
            for row in rows:
                if not isinstance(row, dict) or set(row)!={identity, 'questions', 'correct'}:
                    raise ValueError('Informe o tema/área, as questões e os acertos de cada linha.')
                path = row[identity] if identity=='path' else [row[identity]]
                if not isinstance(path, list) or not path or any(not isinstance(p, str) or not p.strip() for p in path):
                    raise ValueError('Informe o caminho completo do tema ou o nome da área.')
                key = tuple(normalize_path(path))
                if any(key[:len(k)]==k or k[:len(key)]==key for k in keys):
                    raise ValueError('Não repita nem sobreponha temas ou áreas.')
                keys.append(key)
                _number(row['questions'], 'Questões detalhadas', integer=True, positive=True, maximum=self.questions)
                _number(row['correct'], 'Acertos detalhados', integer=True, maximum=row['questions'])
            if (sum(r['questions'] for r in rows)>self.questions or sum(r['correct'] for r in rows)>self.correct
                    or sum(r['questions']-r['correct'] for r in rows)>self.questions-self.correct):
                raise ValueError('Os resultados detalhados excedem o total ou os acertos do simulado.')
        return self

    def to_dict(self):
        return asdict(self)


def _prefix(exam_key):
    return 'mock-' + hashlib.sha256(exam_key.encode()).hexdigest()[:32] + '-'


def _sessions(db):
    latest = {}
    for row in db.execute('SELECT * FROM study_events ORDER BY id'):
        latest[row['session_id']] = {**dict(row), 'entry': json.loads(row['payload'])}
    return latest


def _converted(db, exam_key):
    return [r for sid, r in _sessions(db).items() if sid.startswith(_prefix(exam_key)) and r['action']=='save']


def _latest(db, exam_key, expected_version):
    if not isinstance(exam_key, str) or not exam_key.strip() or type(expected_version) is not int or expected_version<0:
        raise ValueError('Identificador ou versão de simulado inválido.')
    row = db.execute('SELECT * FROM mock_exams WHERE exam_key=? ORDER BY version DESC LIMIT 1', (exam_key,)).fetchone()
    if (row['version'] if row else 0)!=expected_version:
        raise ValueError('O simulado foi atualizado em outra tela. Reabra antes de salvar.')
    return row


class MockExams:
    def __init__(self, repo):
        self.repository = repo
        StudyStore(repo)

    def events(self):
        with self.repository._connection() as db:
            return [{**dict(r), 'exam': json.loads(r['payload'])} for r in db.execute('SELECT * FROM mock_exams ORDER BY id')]

    def active(self):
        latest = {}
        for row in self.events(): latest[row['exam_key']] = row
        return sorted([r for r in latest.values() if r['action']=='save'], key=lambda r: (r['exam']['day'], r['id']))

    def save(self, exam, *, exam_key=None, expected_version=0):
        exam.validate()
        valid_date(exam.day, past=True)
        return self._append(exam, exam_key or uuid.uuid4().hex, expected_version, 'save')

    def void(self, exam_key, expected_version):
        return self._append(None, exam_key, expected_version, 'void')

    def _append(self, exam, exam_key, expected_version, action):
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            old = _latest(db, exam_key, expected_version)
            if action=='void' and (not old or old['action']!='save'):
                raise ValueError('O simulado mudou ou já foi desconsiderado.')
            if _converted(db, exam_key):
                raise ValueError('Retire explicitamente os blocos convertidos antes de corrigir ou desconsiderar o simulado.')
            if exam is not None and exam.target_id:
                target = db.execute('SELECT * FROM exam_targets WHERE target_id=? ORDER BY version DESC LIMIT 1', (exam.target_id,)).fetchone()
                if not target or target['action']!='save': raise ValueError('Escolha uma prova cadastrada e ativa.')
                institution = json.loads(target['payload'])['institution']
                if exam.institution and normalize_path([exam.institution])!=normalize_path([institution]):
                    raise ValueError('A instituição deve corresponder à prova escolhida.')
            payload = old['payload'] if action=='void' else _encoded(exam.to_dict())
            event_id = db.execute('INSERT INTO mock_exams(exam_key,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                                  (exam_key, expected_version+1, action, payload, utc_now())).lastrowid
            details = json.loads(payload)
            for row in details['areas']:
                db.execute('INSERT INTO mock_exam_areas(mock_exam_id,area,questions,correct) VALUES(?,?,?,?)',
                           (event_id, row['area'], row['questions'], row['correct']))
            for row in details['topics']:
                db.execute('INSERT INTO mock_exam_topics(mock_exam_id,path,questions,correct) VALUES(?,?,?,?)',
                           (event_id, _encoded(row['path']), row['questions'], row['correct']))
            return {'id': event_id, 'exam_key': exam_key, 'version': expected_version+1, 'action': action, 'payload': payload,
                    'created_at': db.execute('SELECT created_at FROM mock_exams WHERE id=?', (event_id,)).fetchone()[0], 'exam': details}


MockExamStore = MockExams


def _entries(service, exam_key, exam):
    if not exam.unseen_questions or not exam.topics:
        raise ValueError('A conversão exige questões inéditas e resultados por tema específico. Grandes áreas não geram blocos.')
    catalog, _ = service.catalog(today_local().isoformat(), include_parents=True)
    by_path = {}
    for topic in catalog:
        by_path.setdefault(tuple(normalize_path(topic['path'])), []).append(topic)
    entries = []
    for row in exam.topics:
        key = tuple(normalize_path(row['path']))
        matches = by_path.get(key, [])
        if len(matches)!=1 or not matches[0].get('is_leaf', True):
            raise ValueError('Escolha temas específicos reconhecidos de forma única no catálogo atual.')
        entry = StudyEntry(matches[0]['path'], exam.day, row['questions'], correct=row['correct'], source=f'Simulado {exam.name}')
        entry.validate()
        sid = _prefix(exam_key) + hashlib.sha256(_encoded(list(key)).encode()).hexdigest()[:24]
        entries.append((sid, entry))
    return entries


def convert_to_entries(service, exam_key, expected_version):
    """Uma transação valida a versão do simulado e todos os temas antes de criar blocos."""
    with service.repository._connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row = _latest(db, exam_key, expected_version)
        if not row or row['action']!='save': raise ValueError('O simulado mudou ou foi desconsiderado.')
        exam = MockExam(**json.loads(row['payload'])).validate()
        entries = _entries(service, exam_key, exam)
        current = _sessions(db)
        proposed = dict(current)
        for sid, entry in entries: proposed[sid] = {'session_id': sid, 'action': 'save', 'entry': entry.to_dict()}
        review_queue([r for r in proposed.values() if r['action']=='save'])
        ids = []
        for sid, entry in entries:
            previous = current.get(sid)
            if previous and previous['action']=='save':
                if previous['entry']!=entry.to_dict():
                    raise ValueError('Um bloco convertido foi corrigido. Confira os blocos antes de converter novamente.')
                ids.append(previous['id'])
                continue
            ids.append(db.execute('INSERT INTO study_events(session_id,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                                  (sid, previous['version']+1 if previous else 1, 'save', _encoded(entry.to_dict()), utc_now())).lastrowid)
        return ids


def retract_conversion(service, exam_key, expected_version):
    """Retira explicitamente os blocos, preservando eventos e impedindo perda de correções manuais."""
    with service.repository._connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row = _latest(db, exam_key, expected_version)
        if not row or row['action']!='save': raise ValueError('O simulado mudou ou foi desconsiderado.')
        exam = MockExam(**json.loads(row['payload']))
        expected = {sid: entry.to_dict() for sid, entry in _entries(service, exam_key, exam)}
        converted = _converted(db, exam_key)
        if any(r['entry']!=expected.get(r['session_id']) for r in converted):
            raise ValueError('Há blocos corrigidos manualmente. Confira e desconsidere esses blocos no Registro primeiro.')
        removing = {r['session_id'] for r in converted}
        review_queue([r for sid, r in _sessions(db).items() if r['action']=='save' and sid not in removing])
        for record in converted:
            db.execute('INSERT INTO study_events(session_id,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                       (record['session_id'], record['version']+1, 'void', record['payload'], utc_now()))
        return len(converted)
