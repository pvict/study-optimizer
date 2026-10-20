"""Associação conservadora de um par de relatórios, sem alterar as fontes."""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
import hashlib
import json
import math

from .models import Finding, Report, TopicRecord, normalize_path


@dataclass(frozen=True)
class ManualMatch:
    qbank_index: int
    flashcards_index: int
    note: str
    decision_id: int | None = None


@dataclass(frozen=True)
class Suggestion:
    qbank_index: int
    flashcards_index: int
    similarity: float
    ambiguous: bool


@dataclass
class UnifiedRow:
    row_id: str
    qbank_index: int | None
    flashcards_index: int | None
    qbank: TopicRecord | None
    flashcards: TopicRecord | None
    association: str
    row_type: str
    quality: str
    note: str = ""


@dataclass
class MatchingResult:
    qbank_report_id: str
    flashcards_report_id: str
    qbank_date: str | None
    flashcards_date: str | None
    qbank_scope: str
    flashcards_scope: str
    rows: list[UnifiedRow]
    suggestions: list[Suggestion]
    stats: dict
    findings: list[Finding]
    manual: list[ManualMatch]
    threshold: float
    algorithm_version: str = "1.1"

    def to_dict(self):
        return asdict(self)


def _path(row):
    return tuple(normalize_path(row.path))


def _blocked(records, counterpart_counts):
    counts = Counter(_path(r) for r in records)
    result = {}
    for index, row in enumerate(records):
        key = _path(row)
        if counts[key] > 1 or counterpart_counts[key] > 1:
            result[index] = "Hierarquia duplicada: exige revisão da fonte; registros preservados."
        elif len(row.path) != row.level + 1 or not key or any(not part for part in key):
            result[index] = "Hierarquia incompleta: associação bloqueada."
    return result


def _row(q_report, f_report, qi, fi, association, note="", blocked_note=""):
    q = q_report.records[qi] if qi is not None else None
    f = f_report.records[fi] if fi is not None else None
    signature = json.dumps([q_report.file_sha256, f_report.file_sha256, qi, fi])
    row_id = hashlib.sha256(signature.encode()).hexdigest()[:24]
    if q and f:
        row_type = "granularidade_diferente" if q.is_leaf != f.is_leaf else "terminal_comparavel" if q.is_leaf else "agregado"
    else:
        row_type = "terminal_uma_fonte" if (q or f).is_leaf else "agregado"
    quality = blocked_note or ("Granularidade diferente: não somar ou comparar como terminal." if row_type == "granularidade_diferente"
                              else "Sem associação: indicador da outra fonte ausente." if not (q and f)
                              else "Associação manual documentada." if association == "manual"
                              else "Hierarquia completa exata após normalização.")
    return UnifiedRow(row_id, qi, fi, q, f, association, row_type, quality, note)


def build_matching(qbank: Report, flashcards: Report, manual=(), threshold: float = 0.86) -> MatchingResult:
    if qbank.kind != "qbank" or flashcards.kind != "flashcards":
        raise ValueError("Selecione primeiro Qbank e depois Flashcards.")
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Limite de semelhança deve estar entre 0 e 1.")
    for report in [qbank, flashcards]:
        if not report.records or report.table_pages != report.page_count - 1 or any(f.severity == "erro" for f in report.findings):
            raise ValueError("Relatório com extração incompleta ou erros. Revise a fonte antes do cruzamento.")
    q_counts = Counter(_path(r) for r in qbank.records)
    f_counts = Counter(_path(r) for r in flashcards.records)
    qb = _blocked(qbank.records, f_counts)
    fb = _blocked(flashcards.records, q_counts)
    q_lookup = {_path(r): i for i, r in enumerate(qbank.records) if i not in qb}
    f_lookup = {_path(r): i for i, r in enumerate(flashcards.records) if i not in fb}
    rows, used_q, used_f = [], set(), set()
    for key in sorted(q_lookup.keys() & f_lookup.keys()):
        qi, fi = q_lookup[key], f_lookup[key]
        rows.append(_row(qbank, flashcards, qi, fi, "exata"))
        used_q.add(qi)
        used_f.add(fi)
    decisions = list(manual)
    for decision in decisions:
        qi, fi = decision.qbank_index, decision.flashcards_index
        if not isinstance(qi, int) or not isinstance(fi, int) or not 0 <= qi < len(qbank.records) or not 0 <= fi < len(flashcards.records):
            raise ValueError("Índice de registro inválido para a associação.")
        if not isinstance(decision.note, str) or not decision.note.strip():
            raise ValueError("Registre uma justificativa para a associação manual.")
        if qi in qb or fi in fb:
            raise ValueError("Hierarquia duplicada ou incompleta: reveja a fonte antes de associar.")
        if qi in used_q or fi in used_f:
            raise ValueError("Um dos registros já está associado. Nenhuma correspondência foi substituída.")
        q, f = qbank.records[qi], flashcards.records[fi]
        if not q.is_leaf or not f.is_leaf:
            raise ValueError("Associação manual disponível somente entre terminais.")
        if _path(q)[0] != _path(f)[0]:
            raise ValueError("Grandes áreas diferentes: associação recusada.")
        rows.append(_row(qbank, flashcards, qi, fi, "manual", decision.note.strip()))
        used_q.add(qi)
        used_f.add(fi)
    for qi in range(len(qbank.records)):
        if qi not in used_q:
            rows.append(_row(qbank, flashcards, qi, None, "bloqueada_qbank" if qi in qb else "somente_qbank", blocked_note=qb.get(qi, "")))
    for fi in range(len(flashcards.records)):
        if fi not in used_f:
            rows.append(_row(qbank, flashcards, None, fi, "bloqueada_flashcards" if fi in fb else "somente_flashcards", blocked_note=fb.get(fi, "")))
    rows.sort(key=lambda r: (_path(r.qbank or r.flashcards), r.row_id))
    candidates = defaultdict(list)
    for fi, f in enumerate(flashcards.records):
        if fi not in used_f and fi not in fb and f.is_leaf and len(f.path) >= 2:
            candidates[_path(f)[:-1]].append((fi, f))
    proposals = []
    for qi, q in enumerate(qbank.records):
        if qi in used_q or qi in qb or not q.is_leaf or len(q.path) < 2:
            continue
        options = []
        for fi, f in candidates[_path(q)[:-1]]:
            similarity = SequenceMatcher(None, _path(q)[-1], _path(f)[-1], autojunk=False).ratio()
            if similarity >= threshold:
                options.append((similarity, fi))
        proposals.extend((qi, fi, score) for score, fi in sorted(options, key=lambda x: (-x[0], x[1]))[:3])
    q_proposals = Counter(qi for qi, fi, score in proposals)
    f_proposals = Counter(fi for qi, fi, score in proposals)
    suggestions = [Suggestion(qi, fi, score, q_proposals[qi] > 1 or f_proposals[fi] > 1) for qi, fi, score in proposals]
    terminal_pairs = sum(r.row_type == "terminal_comparavel" for r in rows)
    pairs = len(used_q)
    q_leaves = sum(r.is_leaf for r in qbank.records)
    f_leaves = sum(r.is_leaf for r in flashcards.records)
    stats = {"registros_qbank": len(qbank.records), "registros_flashcards": len(flashcards.records),
             "pares_exatos": pairs - len(decisions), "pares_manuais": len(decisions), "pares_total": pairs,
             "pares_terminais": terminal_pairs, "terminais_qbank": q_leaves, "terminais_flashcards": f_leaves,
             "granularidades_diferentes": sum(r.row_type == "granularidade_diferente" for r in rows),
             "sem_flashcards": len(qbank.records) - pairs, "sem_qbank": len(flashcards.records) - pairs,
             "bloqueados_qbank": len(qb), "bloqueados_flashcards": len(fb),
             "taxa_qbank": 100 * pairs / len(qbank.records), "taxa_flashcards": 100 * pairs / len(flashcards.records),
             "taxa_terminais_qbank": 100 * terminal_pairs / q_leaves if q_leaves else None,
             "taxa_terminais_flashcards": 100 * terminal_pairs / f_leaves if f_leaves else None,
             "sugestoes": len(suggestions)}
    findings = []
    if not qbank.report_date or not flashcards.report_date:
        findings.append(Finding("data_ausente", "aviso", "Data ausente em uma fonte; não pressupor corte comum."))
    elif qbank.report_date != flashcards.report_date:
        findings.append(Finding("datas_diferentes", "aviso", "Relatórios de datas diferentes: os indicadores preservam suas datas de origem."))
    if qbank.scope != flashcards.scope:
        findings.append(Finding("escopos_diferentes", "aviso", "Escopos diferentes: ausência de correspondência pode resultar do filtro de exportação."))
    if qb or fb:
        findings.append(Finding("hierarquias_bloqueadas", "aviso", "Há hierarquias duplicadas ou incompletas. Registros preservados sem associação automática."))
    for label, report in [("qbank", qbank), ("flashcards", flashcards)]:
        for finding in report.findings:
            if finding.severity == "aviso":
                findings.append(Finding(f"fonte_{label}", "aviso", f"{label}: {finding.message}", finding.page, finding.topic_id))
    return MatchingResult(qbank.file_sha256, flashcards.file_sha256, qbank.report_date, flashcards.report_date,
                          qbank.scope, flashcards.scope, rows, suggestions, stats, findings, decisions, threshold)
