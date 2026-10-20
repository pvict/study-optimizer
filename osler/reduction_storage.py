"""Declarações opcionais em lote, com histórico e sem estados de aprovação."""
import hashlib
import json

from .guide_storage import GuideStore
from .storage import utc_now
from .study_signals import study_event_token


class ReductionStore:
    def __init__(self, repo):
        self.repository = repo
        GuideStore(repo)
        with repo._connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS reduction_actions (id INTEGER PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)')
            if db.execute('PRAGMA user_version').fetchone()[0] < 7:
                db.execute('PRAGMA user_version=7')

    def events(self):
        with self.repository._connection() as db:
            return [{'id': r['id'], **json.loads(r['payload'])} for r in db.execute('SELECT * FROM reduction_actions ORDER BY id')]

    @staticmethod
    def _token(db):
        counters = tuple(db.execute(f'SELECT COALESCE(MAX(id),0) FROM {table}').fetchone()[0]
                         for table in ['observation_events', 'matching_events', 'guide_days', 'incidence_datasets', 'planner_events'])
        return (*counters, study_event_token(db), *tuple(db.execute('SELECT COUNT(*),COALESCE(MAX(imported_at),?) FROM reports', ('',)).fetchone()))

    def evidence_token(self):
        with self.repository._connection() as db:
            return self._token(db)

    def append(self, payload, expected_id, evidence_token):
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if self._token(db) != evidence_token:
                raise ValueError('As evidências foram atualizadas durante o registro. Atualize a lista.')
            last = db.execute('SELECT id,payload FROM reduction_actions ORDER BY id DESC LIMIT 1').fetchone()
            if last and json.loads(last['payload']) == payload:
                return last['id']
            previous = last['id'] if last else 0
            if previous != expected_id:
                raise ValueError('A lista foi atualizada em outra tela. Atualize antes de registrar.')
            digest = hashlib.sha256(f'{previous}:{encoded}'.encode()).hexdigest()
            return db.execute('INSERT INTO reduction_actions(payload,digest,created_at) VALUES(?,?,?)', (encoded, digest, utc_now())).lastrowid
