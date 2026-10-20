"""Indicadores declarados pelo usuário, independentes das extrações dos PDFs."""
from dataclasses import asdict, dataclass, fields
from datetime import date
import math
import re

from .models import normalize_path

COUNTS = {"questoes_distintas", "respostas_totais", "cartoes_estudados", "cartoes_ativos", "cartoes_pendentes", "cartoes_futuros", "cartoes_selecionaveis"}
PERCENTAGES = {"acerto_primeira_tentativa", "acerto_ultima_tentativa", "acerto_recente"}
FLAGS = {"erros_criticos", "erros_recorrentes", "cobertura_suficiente"}
ENUMS = {"relevancia_residencia": {"baixa", "media", "alta"}, "incidencia_provas": {"baixa", "media", "alta"},
         "dificuldade": {"baixa", "media", "alta"}, "risco_perda": {"baixo", "moderado", "alto"}}
RELIABILITY = {"informado_usuario", "conferido_usuario", "estimado"}


@dataclass(frozen=True)
class Observation:
    data_observacao: str
    origem_da_informacao: str
    nivel_de_confiabilidade: str
    questoes_distintas: int | None = None
    respostas_totais: int | None = None
    acerto_primeira_tentativa: float | None = None
    acerto_ultima_tentativa: float | None = None
    acerto_recente: float | None = None
    cartoes_estudados: int | None = None
    cartoes_ativos: int | None = None
    cartoes_pendentes: int | None = None
    cartoes_futuros: int | None = None
    cartoes_selecionaveis: int | None = None
    erros_criticos: bool | None = None
    erros_recorrentes: bool | None = None
    cobertura_suficiente: bool | None = None
    relevancia_residencia: str | None = None
    incidencia_provas: str | None = None
    fonte_incidencia: str = ""
    dificuldade: str | None = None
    risco_perda: str | None = None
    confianca_flashcards: int | None = None
    nota: str = ""

    def validate(self):
        try:
            if date.fromisoformat(self.data_observacao).isoformat() != self.data_observacao:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError("Data da observação deve ser uma data ISO válida (AAAA-MM-DD).") from None
        if not isinstance(self.origem_da_informacao, str) or not self.origem_da_informacao.strip():
            raise ValueError("Informe a origem dos indicadores.")
        if self.nivel_de_confiabilidade not in RELIABILITY:
            raise ValueError("Confiabilidade inválida: use informado_usuario, conferido_usuario ou estimado.")
        for name in COUNTS:
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name}: use inteiro não negativo ou deixe vazio.")
        for name in PERCENTAGES:
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100):
                raise ValueError(f"{name}: percentual deve estar entre 0 e 100.")
        for name in FLAGS:
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise ValueError(f"{name}: use sim, não ou não informado.")
        for name, allowed in ENUMS.items():
            if getattr(self, name) is not None and getattr(self, name) not in allowed:
                raise ValueError(f"{name}: opção inválida.")
        if self.questoes_distintas is not None and self.respostas_totais is not None and self.respostas_totais < self.questoes_distintas:
            raise ValueError("Respostas totais não podem ser menores que questões distintas.")
        if self.cartoes_ativos is not None:
            scheduled = sum(v or 0 for v in [self.cartoes_pendentes, self.cartoes_futuros])
            if scheduled > self.cartoes_ativos:
                raise ValueError("Pendentes e futuros informados excedem os cartões ativos desta observação.")
        if self.incidencia_provas is not None and not self.fonte_incidencia.strip():
            raise ValueError("Incidência em provas exige fonte explícita.")
        if self.confianca_flashcards is not None and (type(self.confianca_flashcards) is not int or not 1 <= self.confianca_flashcards <= 5):
            raise ValueError("Confiança subjetiva deve estar entre 1 e 5 ou ausente.")
        if not isinstance(self.nota, str) or not isinstance(self.fonte_incidencia, str):
            raise ValueError("Nota e fonte devem ser texto.")
        return self

    def to_dict(self):
        return asdict(self)


OBSERVATION_FIELDS = [f.name for f in fields(Observation)]


def parse_observation(values: dict) -> Observation:
    if set(values) - set(OBSERVATION_FIELDS):
        raise ValueError("Campos de observação desconhecidos: " + ", ".join(sorted(set(values) - set(OBSERVATION_FIELDS))))
    output = {}
    for name, value in values.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            output[name] = "" if name in {"nota", "fonte_incidencia", "origem_da_informacao"} else None
            continue
        if isinstance(value, str):
            value = value.strip()
        if name in COUNTS or name == "confianca_flashcards":
            if isinstance(value, str):
                if not re.fullmatch(r"\d+|\d{1,3}(?:\.\d{3})+", value):
                    raise ValueError(f"{name}: contagem inválida.")
                value = int(value.replace(".", ""))
        elif name in PERCENTAGES and isinstance(value, str):
            if not re.fullmatch(r"\d+(?:[.,]\d+)?%?", value):
                raise ValueError(f"{name}: percentual inválido; use 0 a 100, sem limites aproximados.")
            value = float(value.rstrip("%").replace(",", "."))
        elif name in FLAGS and isinstance(value, str):
            normalized = normalize_path([value])[0]
            if normalized not in {"sim", "nao", "true", "false"}:
                raise ValueError(f"{name}: use sim ou não; vazio significa não informado.")
            value = normalized in {"sim", "true"}
        elif name in ENUMS and isinstance(value, str):
            value = normalize_path([value])[0]
        output[name] = value
    try:
        return Observation(**output).validate()
    except TypeError as exc:
        raise ValueError("Data, origem e confiabilidade precisam ser informadas.") from exc
