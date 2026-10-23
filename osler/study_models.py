"""Blocos, contatos e fotografias cumulativas com denominadores explícitos."""
from dataclasses import asdict, dataclass, field

from .planning import _date, _number
from .models import normalize_path


@dataclass(frozen=True)
class StudyEntry:
    path: list[str]
    day: str
    questions: int = 0
    correct: int | None = None
    percent: float | None = None
    kind: str = 'bloco'
    mode: str = 'novas'
    minutes: float | None = None
    last_contact: str | None = None
    source: str = 'Informado pelo usuário'
    confident_correct: int | None = None
    review_of: str | None = None

    def validate(self):
        if not isinstance(self.path, list) or not self.path or any(not isinstance(p,str) or not p.strip() for p in self.path):
            raise ValueError('Escolha um tema pelo caminho completo.')
        _date(self.day)
        if self.kind not in {'bloco','acumulado','contato'} or self.mode not in {'novas','repetidas','mistas'}:
            raise ValueError('Tipo de registro ou modalidade inválida.')
        _number(self.questions, 'Questões', integer=True, maximum=1000000)
        if self.correct is not None:
            _number(self.correct, 'Acertos', integer=True, maximum=self.questions)
        if self.percent is not None:
            _number(self.percent, 'Percentual', maximum=100)
        if self.correct is not None and self.percent is not None:
            raise ValueError('Informe acertos ou percentual, não ambos.')
        if self.confident_correct is not None:
            if self.correct is None: raise ValueError('Informe acertos exatos antes de registrar convicção.')
            _number(self.confident_correct,'Acertos com convicção',integer=True,maximum=self.correct)
        if self.review_of is not None:
            if not isinstance(self.review_of,str) or not self.review_of.strip() or self.kind!='bloco' or self.mode!='repetidas' or self.confident_correct is None:
                raise ValueError('Revisão vinculada exige bloco de repetidas e acertos com convicção.')
        if self.kind == 'contato':
            if self.questions or self.correct is not None or self.percent is not None or self.confident_correct is not None:
                raise ValueError('Contato sem questões não pode produzir rendimento.')
        elif not self.questions or (self.correct is None and self.percent is None):
            raise ValueError('Informe questões e acertos (ou percentual aproximado).')
        if self.minutes is not None:
            _number(self.minutes, 'Minutos', positive=True, maximum=1440)
        if self.last_contact and _date(self.last_contact) > _date(self.day):
            raise ValueError('Último contato não pode ser posterior ao registro.')
        if not isinstance(self.source,str) or not self.source.strip():
            raise ValueError('Informe a origem do registro.')
        return self

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class AdaptiveProfile:
    target_accuracy: float = 90
    exam_date: str = '2027-11-30'
    max_questions: int = 60
    minutes_per_question: float = 3
    max_topics: int = 4
    new_share: float = .2
    institution_weights: dict[str,float] = field(default_factory=dict)
    uncertainty_weight: float = .5
    recent_days: int = 90
    min_block: int = 10
    max_contact_gap: int = 30
    area_targets: dict[str,float] = field(default_factory=dict)
    primary_exam_id: str | None = None
    start_date: str | None = None
    workload_mode: str = 'fixed'
    mock_cadence_days: int = 0
    approach_days: int = 30
    exam_weights: dict[str,float] = field(default_factory=dict)

    def validate(self):
        _number(self.mock_cadence_days,'Intervalo entre simulados',integer=True,maximum=365)
        _number(self.approach_days,'Aviso de aproximação',integer=True,maximum=90)
        if not isinstance(self.exam_weights,dict) or any(not isinstance(k,str) or not k.strip() for k in self.exam_weights):
            raise ValueError('Pesos das provas inválidos.')
        for weight in self.exam_weights.values(): _number(weight,'Importância da prova',positive=True)
        if self.workload_mode not in {'fixed','adaptive'}: raise ValueError('Escolha divisão fixa ou adaptativa.')
        _number(self.target_accuracy, 'Meta de acerto', positive=True, maximum=100)
        _date(self.exam_date)
        if self.start_date is not None: _date(self.start_date)
        _number(self.max_questions, 'Limite de questões', integer=True, positive=True, maximum=1000)
        _number(self.max_topics, 'Temas por dia', integer=True, positive=True, maximum=10)
        _number(self.minutes_per_question, 'Minutos por questão', positive=True, maximum=1440)
        _number(self.new_share, 'Reserva para temas novos', maximum=1)
        _number(self.uncertainty_weight, 'Exploração da incerteza', maximum=2)
        _number(self.recent_days, 'Janela recente', positive=True, integer=True, maximum=730)
        _number(self.min_block,'Mínimo por bloco',positive=True,integer=True,maximum=100)
        _number(self.max_contact_gap,'Intervalo máximo',positive=True,integer=True,maximum=90)
        if not isinstance(self.institution_weights,dict) or any(not isinstance(k,str) or not k.strip() for k in self.institution_weights):
            raise ValueError('Instituições inválidas.')
        if len(set(normalize_path(list(self.institution_weights)))) != len(self.institution_weights):
            raise ValueError('Use cada instituição uma única vez, sem duplicar grafias.')
        for value in self.institution_weights.values():
            _number(value, 'Peso da instituição', positive=True)
        if not isinstance(self.area_targets,dict) or any(not isinstance(k,str) or not k.strip() for k in self.area_targets):
            raise ValueError('Metas por área inválidas.')
        if len(set(normalize_path(list(self.area_targets))))!=len(self.area_targets): raise ValueError('Use cada área uma única vez.')
        for value in self.area_targets.values(): _number(value,'Meta de acerto nos temas',positive=True,maximum=100)
        if self.primary_exam_id is not None and (not isinstance(self.primary_exam_id,str) or not self.primary_exam_id.strip()):
            raise ValueError('Prova principal inválida.')
        return self

    def target_for_area(self,area):
        key=normalize_path([area])[0]
        return next((v for k,v in self.area_targets.items() if normalize_path([k])[0]==key),self.target_accuracy)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class StudyDay:
    questions: int = 60
    kind: str = 'normal'
    extra_topics: list[dict] = field(default_factory=list)

    def validate(self):
        _number(self.questions,'Meta diária',integer=True,positive=True,maximum=1000)
        if self.kind not in {'normal','plantao','descanso'}: raise ValueError('Tipo de dia inválido.')
        if not isinstance(self.extra_topics,list): raise ValueError('Revisões adicionais inválidas.')
        seen=set()
        for extra in self.extra_topics:
            if not isinstance(extra,dict) or set(extra)!={'extra_id','topic_id','questions','after_event_id'}:
                raise ValueError('Revisão adicional inválida.')
            key=extra['extra_id']
            if not isinstance(key,str) or not key or key in seen: raise ValueError('Revisão adicional repetida ou inválida.')
            if not isinstance(extra['topic_id'],str) or not extra['topic_id']: raise ValueError('Tema adicional inválido.')
            seen.add(key)
            _number(extra['questions'],'Questões adicionais',integer=True,positive=True,maximum=1000)
            _number(extra['after_event_id'],'Corte do histórico',integer=True,maximum=1000000000)
        if sum(e['questions'] for e in self.extra_topics)>1000: raise ValueError('Limite de 1.000 questões adicionais por dia.')
        return self

    def to_dict(self):
        return asdict(self)
