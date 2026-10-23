"""Histórico aditivo de sessões e versões de perfil; acumulados não são sessões."""
import hashlib
import json
import re
from dataclasses import replace

from .reduction_storage import ReductionStore
from .storage import utc_now
from .study_models import AdaptiveProfile, StudyDay, StudyEntry
from .review_queue import review_queue
from .planning import _date


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class StudyStore:
    def __init__(self, repo):
        self.repository = repo
        ReductionStore(repo)
        with repo._connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS study_events (id INTEGER PRIMARY KEY,session_id TEXT NOT NULL,version INTEGER NOT NULL,action TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(session_id,version));
                CREATE TABLE IF NOT EXISTS study_profiles (id INTEGER PRIMARY KEY,payload TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS study_plan_runs (id INTEGER PRIMARY KEY,payload TEXT NOT NULL,digest TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS study_days (day TEXT PRIMARY KEY,revision INTEGER NOT NULL,payload TEXT NOT NULL,updated_at TEXT NOT NULL);
            ''')
            if db.execute('PRAGMA user_version').fetchone()[0] < 9:
                db.execute('PRAGMA user_version=9')
            from .exam_goals import migrate_exam_targets
            migrate_exam_targets(db)
            from .lote_b_schema import migrate_lote_b
            migrate_lote_b(db)

    def day(self,day,default_questions=60):
        _date(day)
        with self.repository._connection() as db:
            row=db.execute('SELECT * FROM study_days WHERE day=?',(day,)).fetchone()
            return {'day':day,'revision':row['revision'],'settings':json.loads(row['payload'])} if row else {'day':day,'revision':0,'settings':StudyDay(questions=default_questions).to_dict()}

    def save_day(self,day,settings,expected_revision):
        _date(day)
        settings.validate()
        if type(expected_revision) is not int or expected_revision<0: raise ValueError('Versão do dia inválida.')
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision FROM study_days WHERE day=?',(day,)).fetchone()
            if (row['revision'] if row else 0)!=expected_revision:
                raise ValueError('O plano do dia foi atualizado em outra tela. Recarregue antes de salvar.')
            db.execute('INSERT INTO study_days(day,revision,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(day) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at',
                       (day,expected_revision+1,_encoded(settings.to_dict()),utc_now()))
            return expected_revision+1

    def days(self):
        with self.repository._connection() as db:
            return {r['day']:json.loads(r['payload']) for r in db.execute('SELECT day,payload FROM study_days')}

    def save_batch(self, changes):
        if not changes or len({c[0] for c in changes}) != len(changes):
            raise ValueError('Selecione sessões distintas.')
        for session_id, entry, version in changes:
            if not isinstance(session_id,str) or not re.fullmatch(r'[\w.-]{1,128}',session_id) or type(version) is not int or version < 0:
                raise ValueError('Identidade ou versão da sessão inválida.')
            entry.validate()
        ids = []
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            current={e['session_id']:e for e in self.active('9999-12-31')}
            for sid,entry,version in changes: current[sid]={'session_id':sid,'entry':entry.to_dict()}
            review_queue(list(current.values()))
            for session_id, entry, version in changes:
                payload = _encoded(entry.to_dict())
                previous = db.execute('SELECT * FROM study_events WHERE session_id=? ORDER BY version DESC LIMIT 1',(session_id,)).fetchone()
                if previous and previous['action']=='save' and StudyEntry(**json.loads(previous['payload'])).to_dict()==entry.to_dict():
                    ids.append(previous['id'])
                    continue
                if (previous['version'] if previous else 0) != version:
                    raise ValueError('A sessão foi atualizada em outra tela. Reabra antes de salvar.')
                ids.append(db.execute('INSERT INTO study_events(session_id,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                                      (session_id,version+1,'save',payload,utc_now())).lastrowid)
        return ids

    def events(self):
        with self.repository._connection() as db:
            return [{**dict(r),'entry':json.loads(r['payload'])} for r in db.execute('SELECT * FROM study_events ORDER BY id')]

    def active(self, as_of):
        latest = {}
        first = {}
        for event in self.events():
            latest[event['session_id']] = event
            first.setdefault(event['session_id'],event['id'])
        return [{**e,'first_event_id':first[e['session_id']]} for e in latest.values() if e['action']=='save' and e['entry']['day']<=as_of]

    def void(self, session_id, expected_version):
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            last = db.execute('SELECT * FROM study_events WHERE session_id=? ORDER BY version DESC LIMIT 1',(session_id,)).fetchone()
            if not last or last['version']!=expected_version:
                raise ValueError('A sessão mudou. Atualize a tela.')
            review_queue([e for e in self.active('9999-12-31') if e['session_id']!=session_id])
            return db.execute('INSERT INTO study_events(session_id,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                              (session_id,expected_version+1,'void',last['payload'],utc_now())).lastrowid

    def profile(self):
        with self.repository._connection() as db:
            row = db.execute('SELECT * FROM study_profiles ORDER BY id DESC LIMIT 1').fetchone()
        configured=AdaptiveProfile(**json.loads(row['payload'])) if row else AdaptiveProfile()
        from .exam_goals import active_exams,principal_exam
        from .planner_service import today_local
        principal=principal_exam(configured,active_exams(self.repository),today_local().isoformat())
        effective=replace(configured,exam_date=principal['target']['exam_date']) if principal else configured
        if configured.exam_weights:
            weights={}
            for e in active_exams(self.repository):
                weight=configured.exam_weights.get(e['target_id'])
                if weight is not None:
                    name=e['target']['institution']
                    weights[name]=max(weights.get(name,0),weight)
            # IDs vinculados substituem nomes livres apenas quando configurados.
            effective=replace(effective,institution_weights=weights)
        return {'id':row['id'] if row else 0,'profile':effective.to_dict(),'configured_profile':configured.to_dict()}

    def save_profile(self, profile, expected_id):
        profile.validate()
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COALESCE(MAX(id),0) FROM study_profiles').fetchone()[0] != expected_id:
                raise ValueError('O planejamento foi atualizado. Reabra antes de salvar.')
            return db.execute('INSERT INTO study_profiles(payload,created_at) VALUES(?,?)',(_encoded(profile.to_dict()),utc_now())).lastrowid

    def save_plan(self, plan):
        payload = _encoded(plan)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.repository._connection() as db:
            db.execute('INSERT OR IGNORE INTO study_plan_runs(payload,digest,created_at) VALUES(?,?,?)',(payload,digest,utc_now()))
            return db.execute('SELECT id FROM study_plan_runs WHERE digest=?',(digest,)).fetchone()[0]
