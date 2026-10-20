"""Cenários de tempo e capacidade; sem inferência de agendamento individual."""
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
import math

DAY_TYPES = {"normal", "plantao", "descanso", "minimo"}


def _date(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError("Data deve estar em AAAA-MM-DD e ser válida.") from None
    return parsed


def _number(value, label, *, positive=False, maximum=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (integer and type(value) is not int) or value < 0 or (positive and value == 0) or (maximum is not None and value > maximum):
        raise ValueError(f"{label}: valor inválido.")


@dataclass(frozen=True)
class DayProfile:
    minutes: float
    questions: int
    general_cards: int
    error_cards: int

    def validate(self):
        _number(self.minutes, "Minutos do dia", maximum=1440)
        for field_name in ("questions", "general_cards", "error_cards"):
            _number(getattr(self, field_name), field_name, integer=True, maximum=100000)
        return self


def _default_profiles():
    return {"normal": DayProfile(240, 60, 100, 30), "plantao": DayProfile(45, 10, 20, 10),
            "descanso": DayProfile(0, 0, 0, 0), "minimo": DayProfile(15, 3, 5, 5)}


@dataclass(frozen=True)
class RoutineConfig:
    start_date: str
    days: int = 90
    daily_limit: int = 150
    seconds_per_general: float = 20
    seconds_per_error: float = 30
    minutes_per_question: float = 3
    profiles: dict[str, DayProfile] = field(default_factory=_default_profiles)
    weekday_types: dict[int, str] = field(default_factory=dict)
    overrides: dict[str, str] = field(default_factory=dict)
    exam_every_days: int = 14
    exam_minutes: float = 240

    def validate(self):
        _date(self.start_date)
        _number(self.days, "Dias", positive=True, integer=True, maximum=366)
        _number(self.daily_limit, "Teto diário", integer=True, maximum=100000)
        for name in ("seconds_per_general", "seconds_per_error", "minutes_per_question", "exam_minutes"):
            _number(getattr(self, name), name, positive=True, maximum=86400)
        _number(self.exam_every_days, "Intervalo de provas", integer=True, maximum=366)
        if set(self.profiles) != DAY_TYPES:
            raise ValueError("Informe os quatro perfis de dia: normal, plantao, descanso e minimo.")
        for profile in self.profiles.values():
            if not isinstance(profile, DayProfile):
                raise ValueError("Perfil de dia inválido.")
            profile.validate()
        if any(type(k) is not int or not 0 <= k <= 6 or v not in DAY_TYPES for k, v in self.weekday_types.items()):
            raise ValueError("Dias da semana inválidos.")
        for day, kind in self.overrides.items():
            _date(day)
            if kind not in DAY_TYPES:
                raise ValueError("Tipo de exceção de dia inválido.")
        return self

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        values = dict(data)
        values["profiles"] = {k: DayProfile(**v) for k, v in values["profiles"].items()}
        values["weekday_types"] = {int(k): v for k, v in values.get("weekday_types", {}).items()}
        return cls(**values).validate()


@dataclass(frozen=True)
class Measurement:
    kind: str
    count: int
    observed_date: str
    source: str
    horizon_days: int | None = None
    approximate: bool = False
    note: str = ""

    def validate(self):
        if self.kind not in {"revisoes_periodo", "revisoes_high_yield", "cartoes_pendentes"}:
            raise ValueError("Tipo de medição inválido.")
        _number(self.count, "Contagem", integer=True)
        _date(self.observed_date)
        if not isinstance(self.source, str) or not self.source.strip() or not isinstance(self.note, str) or type(self.approximate) is not bool:
            raise ValueError("Informe origem textual e confiabilidade da medição.")
        if self.kind != "cartoes_pendentes":
            _number(self.horizon_days, "Horizonte", positive=True, integer=True, maximum=366)
        elif self.horizon_days is not None:
            raise ValueError("Cartões pendentes não representam revisões de um horizonte.")
        return self


def plan_days(config):
    cfg = config.validate()
    start, days = _date(cfg.start_date), []
    for index in range(cfg.days):
        current = start+timedelta(days=index)
        kind = cfg.overrides.get(current.isoformat(), cfg.weekday_types.get(current.weekday(), "normal"))
        profile = cfg.profiles[kind]
        available = profile.minutes*60
        warning = ""
        exam = 0
        if cfg.exam_every_days and (index+1) % cfg.exam_every_days == 0:
            if available >= cfg.exam_minutes*60:
                exam = cfg.exam_minutes
            else:
                warning = "A prova antiga não cabe neste dia; escolha outra data ou duração. Sem dívida automática."
        remaining = available-exam*60
        questions = min(profile.questions, math.floor((remaining+1e-8)/(cfg.minutes_per_question*60)))
        remaining -= questions*cfg.minutes_per_question*60
        errors = min(profile.error_cards, math.floor((remaining+1e-8)/cfg.seconds_per_error))
        remaining -= errors*cfg.seconds_per_error
        general = min(profile.general_cards, cfg.daily_limit, math.floor((remaining+1e-8)/cfg.seconds_per_general))
        remaining -= general*cfg.seconds_per_general
        nominal = cfg.daily_limit if available > 0 else 0
        reserved_remaining = max(0, available-exam*60-profile.questions*cfg.minutes_per_question*60-profile.error_cards*cfg.seconds_per_error)
        time_capacity = min(nominal, math.floor((reserved_remaining+1e-8)/cfg.seconds_per_general))
        days.append({"date": current.isoformat(), "day_type": kind, "available_minutes": profile.minutes,
                     "exam_minutes": exam, "questions": questions, "error_cards": errors, "general_cards": general,
                     "planned_minutes": round((available-remaining)/60, 6), "remaining_minutes": round(max(0, remaining)/60, 6),
                     "nominal_capacity": nominal, "time_capacity": time_capacity,
                     "minutes_after_reserves": reserved_remaining/60,
                     "unfilled_goals": {"questions": profile.questions-questions, "error_cards": profile.error_cards-errors, "general_cards": profile.general_cards-general},
                     "warning": warning})
    return days


def simulate_capacity(config, load_count=None, load_horizon=None):
    cfg = config.validate()
    if load_count is not None:
        _number(load_count, "Revisões informadas", integer=True)
        if type(load_horizon) is not int or load_horizon != cfg.days:
            raise ValueError("Horizonte da medição difere do cenário. Não extrapolar automaticamente.")
    days = plan_days(cfg)
    nominal, timed = sum(d["nominal_capacity"] for d in days), sum(d["time_capacity"] for d in days)
    return {"config": cfg.to_dict(), "load_count": load_count, "load_horizon": load_horizon,
            "ceiling_all_days": cfg.days*cfg.daily_limit, "nominal_capacity": nominal, "time_capacity": timed,
            "excess_at_limit": max(0, load_count-nominal) if load_count is not None else None,
            "excess_with_time": max(0, load_count-timed) if load_count is not None else None,
            "days": days, "sensitivity": [{"seconds_per_card": seconds,
                "capacity": sum(min(d["nominal_capacity"], math.floor((d["minutes_after_reserves"]*60+1e-8)/seconds)) for d in days)}
                for seconds in sorted({max(1, cfg.seconds_per_general*0.75), cfg.seconds_per_general, cfg.seconds_per_general*1.5})],
            "warnings": ["Cenário estático: agendamento individual, novas revisões e reagendamentos não estão disponíveis.",
                         "Capacidade não prova que a carga real caberá diariamente. Concentração em picos não foi simulada.",
                         "Cartões selecionados/suspensos não foram convertidos em revisões eliminadas.",
                         "Tempos e metas são hipóteses ajustáveis, sem obrigação de compensar dias anteriores."]}
