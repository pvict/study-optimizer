"""Comparações documentais de cortes distintos; não demonstra efeito causal."""
from collections import Counter

from .models import normalize_path
from .planner_service import PlannerService


def compare_reports(repo, older_id, newer_id):
    old, new = repo.get_report(older_id), repo.get_report(newer_id)
    complete = {r["file_sha256"]: r["complete"] for r in repo.list_reports()}
    if not complete.get(older_id) or not complete.get(newer_id):
        raise ValueError("Compare somente relatórios completos e sem erros bloqueantes.")
    if old.kind != new.kind or old.scope != new.scope or old.scope == "desconhecido":
        raise ValueError("A comparação exige o mesmo tipo e escopo de relatório.")
    if not old.report_date or not new.report_date or old.report_date >= new.report_date:
        raise ValueError("Selecione duas datas distintas, com a fonte antiga antes da recente.")
    def leaves(report):
        keys = Counter(tuple(normalize_path(r.path)) for r in report.records)
        return {tuple(normalize_path(r.path)): r for r in report.records if r.is_leaf and len(r.path) == r.level+1 and keys[tuple(normalize_path(r.path))] == 1}
    left, right = leaves(old), leaves(new)
    common = []
    for key in sorted(left.keys() & right.keys()):
        a, b = left[key], right[key]
        metric_a = a.acerto_pdf if old.kind == "qbank" else a.percentual_revisado
        metric_b = b.acerto_pdf if old.kind == "qbank" else b.percentual_revisado
        delta = metric_b.value-metric_a.value if metric_a.value is not None and metric_b.value is not None and metric_a.operator == metric_b.operator == "=" else None
        common.append({"hierarchy": " → ".join(b.path), "old_studied": a.studied, "new_studied": b.studied,
                       "studied_delta": b.studied-a.studied, "old_total": a.total, "new_total": b.total,
                       "old_pdf_metric": metric_a.raw, "new_pdf_metric": metric_b.raw, "pdf_metric_delta_pp": delta})
    a, b = old.summary.get("estudados"), new.summary.get("estudados")
    return {"older_id": older_id, "newer_id": newer_id, "kind": old.kind, "scope": old.scope,
            "older_date": old.report_date, "newer_date": new.report_date,
            "metric_label": "Acerto PDF: tentativa não identificada" if old.kind == "qbank" else "Cobertura de revisão, não acerto",
            "cover": {"old_studied": a, "new_studied": b, "studied_delta": b-a if a is not None and b is not None else None,
                      "old_total": old.summary.get("total"), "new_total": new.summary.get("total")}, "common": common,
            "added": [" → ".join(right[k].path) for k in sorted(right.keys()-left.keys())],
            "removed": [" → ".join(left[k].path) for k in sorted(left.keys()-right.keys())],
            "excluded_old": sum(r.is_leaf for r in old.records)-len(left), "excluded_new": sum(r.is_leaf for r in new.records)-len(right),
            "warnings": ["Comparação documental, sem atribuição causal às decisões de suspensão.",
                         "Acervo, denominadores e seleção podem ter mudado. Diferença aritmética não comprova melhora individual.",
                         "Somente terminais com hierarquia completa exata e única são comparados; pais e filhos não foram somados."]}


def decision_timeline(repo):
    events = sorted(PlannerService(repo).events(), key=lambda e: (e["action_date"], e["id"]))
    states, applied, reactivated, timeline = {}, 0, 0, {}
    for event in events:
        states[event["item_id"]] = event["new_status"]
        applied += event["action"] == "estado" and event["new_status"] == "aplicado_manualmente"
        reactivated += event["action"] == "estado" and event["new_status"] == "reativado"
        counts = Counter(states.values())
        timeline[event["action_date"]] = {"date": event["action_date"], **{s: counts[s] for s in ("sugerido", "aguardando_validacao", "aprovado_usuario", "aplicado_manualmente", "reativado", "cancelado")},
                                           "total_aplicacoes_declaradas": applied, "total_reativacoes_declaradas": reactivated}
    return list(timeline.values())
