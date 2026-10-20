"""Referências de provas versionadas; corte informado não é previsão pessoal."""
from dataclasses import asdict,dataclass
import json
import uuid
from .planning import _date,_number
from .storage import utc_now


@dataclass(frozen=True)
class ExamTarget:
    institution: str
    exam_date: str
    cutoff_score: float
    max_score: float
    cutoff_source: str
    exam_year: int | None = None
    registration_deadline: str | None = None
    cutoff_confidence: str = 'informado'
    notes: str = ''

    def validate(self):
        if not isinstance(self.institution,str) or not self.institution.strip(): raise ValueError('Informe a instituição da prova.')
        if not isinstance(self.cutoff_source,str) or not self.cutoff_source.strip(): raise ValueError('Informe a fonte do corte, como edital, documento ou link.')
        _date(self.exam_date)
        if self.registration_deadline is not None:
            _date(self.registration_deadline)
            if self.registration_deadline>self.exam_date: raise ValueError('A inscrição deve terminar até a data da prova.')
        if self.exam_year is not None: _number(self.exam_year,'Ano da edição',integer=True,positive=True,maximum=9999)
        _number(self.max_score,'Nota máxima',positive=True)
        _number(self.cutoff_score,'Nota de corte',maximum=self.max_score)
        if self.cutoff_confidence not in {'informado','conferido','estimado'}: raise ValueError('Escolha como a fonte do corte foi conferida.')
        if not isinstance(self.notes,str): raise ValueError('Observações inválidas.')
        return self

    def to_dict(self): return asdict(self)


def migrate_exam_targets(db):
    if db.execute('PRAGMA user_version').fetchone()[0]>=10: return
    db.execute('BEGIN IMMEDIATE')
    db.execute('''CREATE TABLE IF NOT EXISTS exam_targets (
        id INTEGER PRIMARY KEY,target_id TEXT NOT NULL,version INTEGER NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('save','void')),payload TEXT NOT NULL,
        created_at TEXT NOT NULL,UNIQUE(target_id,version))''')
    db.execute('PRAGMA user_version=10')


def exam_events(repo):
    with repo._connection() as db:
        return [{**dict(r),'target':json.loads(r['payload'])} for r in db.execute('SELECT * FROM exam_targets ORDER BY id')]


def active_exams(repo):
    latest={}
    for e in exam_events(repo): latest[e['target_id']]=e
    return sorted([e for e in latest.values() if e['action']=='save'],key=lambda e:(e['target']['exam_date'],e['target']['institution'],e['target_id']))


def principal_exam(profile,exams,today):
    chosen=next((e for e in exams if e['target_id']==profile.primary_exam_id),None)
    if chosen: return chosen
    future=[e for e in exams if e['target']['exam_date']>=today]
    if future: return min(future,key=lambda e:(e['target']['exam_date'],e['target_id']))
    return max(exams,key=lambda e:(e['target']['exam_date'],e['target_id'])) if exams else None


class ExamGoals:
    def __init__(self,repo):
        from .study_storage import StudyStore
        self.repository=repo
        StudyStore(repo)

    def events(self): return exam_events(self.repository)
    def active(self): return active_exams(self.repository)

    def _append(self,target,target_id,expected_version,action):
        target.validate()
        if type(expected_version) is not int or expected_version<0: raise ValueError('Versão de prova inválida.')
        if not isinstance(target_id,str) or not target_id.strip(): raise ValueError('Identificador de prova inválido.')
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM exam_targets WHERE target_id=? ORDER BY version DESC LIMIT 1',(target_id,)).fetchone()
            if (old['version'] if old else 0)!=expected_version or action=='void' and (not old or old['action']!='save'):
                raise ValueError('A prova foi atualizada em outra tela. Reabra antes de salvar.')
            if action=='void': payload=old['payload']
            else: payload=json.dumps(target.to_dict(),ensure_ascii=False,sort_keys=True,allow_nan=False)
            event_id=db.execute('INSERT INTO exam_targets(target_id,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                               (target_id,expected_version+1,action,payload,utc_now())).lastrowid
        return next(e for e in self.events() if e['id']==event_id)

    def save(self,target,*,target_id=None,expected_version=0):
        return self._append(target,target_id or uuid.uuid4().hex,expected_version,'save')

    def void(self,target_id,expected_version):
        # A fonte e o restante do payload da versão anterior são preservados.
        old=next((e for e in reversed(self.events()) if e['target_id']==target_id),None)
        if not old: raise ValueError('A prova mudou ou não está cadastrada.')
        return self._append(ExamTarget(**old['target']),target_id,expected_version,'void')
