"""Parâmetros explícitos e imutáveis. Registrar não seleciona nem calibra."""
from dataclasses import dataclass,asdict,fields
from functools import lru_cache
import json
from .storage import utc_now
from .planning import _number


@dataclass(frozen=True)
class AlgorithmParameters:
    version: int = 1
    first_interval: int = 7
    second_interval: int = 14
    max_contact_gap: int = 30
    failure_interval: int = 3
    failure_threshold: float = .6
    raw_low_threshold: float = .7
    intermediate_threshold: float = .8
    initial_low_interval: int = 7
    initial_mid_interval: int = 14
    initial_near_interval: int = 21
    initial_good_interval: int = 28
    initial_min_sample: int = 10
    sufficient_sample: int = 30
    minimum_block: int = 10
    diagnostic_dose: int = 20
    gap_dose: float = 10
    uncertainty_dose: float = 5
    incidence_dose: float = 5
    maintenance_incidence_dose: float = 3
    incidence_factor: float = .5
    exploration_reserve: float = .05
    spaced_min_days: int = 3
    mastery_wilson_lower: float = .8
    default_ease: float = 2.5
    min_ease: float = 1.3
    max_ease: float = 3.
    ease_step: float = .1
    ease_penalty: float = .08
    ease_penalty_squared: float = .02

    def validate(self):
        _number(self.version,'Versão de parâmetros',positive=True,integer=True)
        for f in fields(self):
            if f.name=='version': continue
            _number(getattr(self,f.name),f.name,positive=True)
        for name in ('failure_threshold','raw_low_threshold','intermediate_threshold','incidence_factor','exploration_reserve','mastery_wilson_lower'):
            if getattr(self,name)>1: raise ValueError('Proporção de parâmetro inválida.')
        for name in ('first_interval','second_interval','max_contact_gap','failure_interval','initial_low_interval',
                     'initial_mid_interval','initial_near_interval','initial_good_interval','initial_min_sample',
                     'sufficient_sample','minimum_block','diagnostic_dose','spaced_min_days'):
            _number(getattr(self,name),name,integer=True,positive=True,maximum=1000)
        if self.min_ease>self.default_ease or self.default_ease>self.max_ease: raise ValueError('Faixa de facilidade inválida.')
        if self.version==1 and 'V1' in globals() and self!=V1: raise ValueError('A versão 1 é imutável e deve preservar os valores originais.')
        return self

    def to_dict(self): return asdict(self)


V1=AlgorithmParameters()


@lru_cache(maxsize=64)
def _validated_values(items):
    return AlgorithmParameters(**{name:value for name,kind,value in items}).validate()


def parameters_from_values(values):
    """Reutiliza apenas configurações numéricas imutáveis, validadas por conteúdo."""
    if not isinstance(values,dict) or any(type(v) not in (int,float) for v in values.values()):
        return AlgorithmParameters(**values).validate()
    # Tipo compõe a chave: True não pode reutilizar um inteiro já validado.
    return _validated_values(tuple((k,type(v),v) for k,v in sorted(values.items())))


def current_parameters(repo):
    """Somente leitura, inclusive em chamadas de relatórios."""
    with repo._connection() as db:
        row=db.execute('SELECT s.id,p.payload FROM algorithm_selections s JOIN algorithm_parameters p ON p.version=s.parameter_version ORDER BY s.id DESC LIMIT 1').fetchone()
        if row: return {'id':row['id'],'parameters':AlgorithmParameters(**json.loads(row['payload'])).validate()}
    return {'id':0,'parameters':V1}


class ParameterStore:
    def __init__(self,repo):
        self.repository=repo
        from .study_storage import StudyStore
        StudyStore(repo)

    def versions(self):
        with self.repository._connection() as db:
            return [dict(r) for r in db.execute('SELECT * FROM algorithm_parameters ORDER BY version')]

    def current(self): return current_parameters(self.repository)

    def history(self):
        with self.repository._connection() as db: return [dict(r) for r in db.execute('SELECT * FROM algorithm_selections ORDER BY id')]

    def register(self,parameters,expected_latest):
        parameters.validate()
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            latest=db.execute('SELECT COALESCE(MAX(version),0) FROM algorithm_parameters').fetchone()[0]
            if latest!=expected_latest or parameters.version<=latest: raise ValueError('A versão já existe ou o cadastro mudou.')
            db.execute('INSERT INTO algorithm_parameters(version,payload,created_at) VALUES(?,?,?)',
                       (parameters.version,json.dumps(parameters.to_dict(),sort_keys=True),utc_now()))

    def select(self,version,expected_id):
        if type(version) is not int or type(expected_id) is not int: raise ValueError('Versão inválida.')
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            latest=db.execute('SELECT COALESCE(MAX(id),0) FROM algorithm_selections').fetchone()[0]
            if latest!=expected_id: raise ValueError('A seleção mudou. Atualize a tela.')
            if not db.execute('SELECT 1 FROM algorithm_parameters WHERE version=?',(version,)).fetchone(): raise ValueError('Versão não cadastrada.')
            return db.execute('INSERT INTO algorithm_selections(parameter_version,created_at) VALUES(?,?)',(version,utc_now())).lastrowid
