from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
import unicodedata
from functools import lru_cache


@lru_cache(maxsize=8192)
def _normalized_part(part: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", part)
                            if not unicodedata.combining(c)).casefold().split())


def normalize_path(path: list[str]) -> list[str]:
    # Strings são imutáveis; a lista de cada chamador continua independente.
    return [_normalized_part(part) for part in path]


def stable_topic_id(path: list[str]) -> str:
    return hashlib.sha256(json.dumps(normalize_path(path), ensure_ascii=False).encode()).hexdigest()[:24]


@dataclass
class Percentage:
    value: float | None = None
    operator: str | None = None
    raw: str = "-"


def parse_percentage(text: str) -> Percentage:
    raw = text.strip()
    if raw in {"", "-", "—", "–"}:
        return Percentage(raw=raw)
    match = re.fullmatch(r"([<>]?)\s*(\d+(?:[.,]\d+)?)\s*%", raw)
    if not match:
        raise ValueError(f"Percentual não reconhecido: {raw}")
    return Percentage(float(match[2].replace(",", ".")), match[1] or "=", raw)


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    page: int | None = None
    topic_id: str | None = None


@dataclass
class TopicRecord:
    topic_id: str
    path: list[str]
    level: int
    total: int
    studied: int
    percentual_visto: Percentage
    page: int
    raw_row: str
    source_x: float
    source_y: float
    is_leaf: bool = True
    acerto_pdf: Percentage = field(default_factory=Percentage)
    percentual_revisado: Percentage = field(default_factory=Percentage)
    acerto_primeira_tentativa: float | None = None
    acerto_ultima_tentativa: float | None = None
    questoes_distintas: int | None = None
    respostas_totais: int | None = None
    cartoes_ativos: int | None = None
    cartoes_pendentes: int | None = None
    cartoes_futuros: int | None = None
    origem_da_informacao: str = "PDF exportado manualmente"
    nivel_de_confiabilidade: str = "extração documental; tentativa do acerto não identificada"

    @property
    def name(self) -> str:
        return self.path[-1]


@dataclass
class Report:
    filename: str
    file_sha256: str
    kind: str
    scope: str
    report_date: str | None
    page_count: int
    metadata: dict
    summary: dict
    records: list[TopicRecord] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    table_pages: int = 0
    content_sha256: str = ""
    parser_version: str = "1.0"

    @property
    def status(self) -> str:
        return "revisar" if any(f.severity in {"aviso", "erro"} for f in self.findings) else "validado"

    def to_dict(self) -> dict:
        return {**asdict(self), "status": self.status}

    @classmethod
    def from_dict(cls, data: dict) -> "Report":
        data = dict(data)
        data.pop("status", None)
        rows = []
        for item in data.pop("records"):
            item = dict(item)
            for key in ["percentual_visto", "acerto_pdf", "percentual_revisado"]:
                item[key] = Percentage(**item[key])
            rows.append(TopicRecord(**item))
        return cls(**{**data, "records": rows, "findings": [Finding(**f) for f in data["findings"]]})
