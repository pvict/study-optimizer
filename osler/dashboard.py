"""Resumo documental sem misturar níveis, recortes ou tentativas."""
from collections import Counter

from .assessment_service import AssessmentService, eligible
from .matching_service import load_matching
from .models import normalize_path
from .planner_service import PlannerService
from .planning_service import PlanningService


def build_dashboard(repo, qbank_id, flashcards_id, as_of):
    q, f = repo.get_report(qbank_id), repo.get_report(flashcards_id)
    matching = load_matching(repo, qbank_id, flashcards_id)
    analyzed = AssessmentService(repo).analyze(matching, as_of)
    areas = {}
    for kind, report in [("qbank", q), ("flashcards", f)]:
        for row in report.records:
            if row.level != 0:
                continue
            key = normalize_path(row.path)[0]
            entry = areas.setdefault(key, {"area": row.path[0]})
            # Duplicação no nível de área torna o agregado ambíguo; não somar.
            if f"{kind}_studied" in entry:
                entry[f"{kind}_studied"] = None
                entry[f"{kind}_total"] = None
                entry[f"{kind}_metric"] = "ambíguo"
            else:
                entry.update({f"{kind}_studied": row.studied, f"{kind}_total": row.total,
                              f"{kind}_metric": row.acerto_pdf.raw if kind == "qbank" else row.percentual_revisado.raw})
    planner = PlannerService(repo)
    counts = Counter(i["status"] for i in planner.store.all_items())
    dates = {r["report_date"] for r in repo.list_reports(False) if r["report_date"]}
    def cover(report):
        return {"studied": report.summary.get("estudados"), "total": report.summary.get("total"),
                "report_date": report.report_date, "scope": report.scope, "report_id": report.file_sha256}
    practice_gaps = []
    for row in matching.rows:
        if eligible(row) and row.flashcards and row.flashcards.studied >= 100 and (row.qbank is None or row.qbank.studied < 30):
            practice_gaps.append({"hierarquia": " → ".join(row.flashcards.path), "cartoes_estudados_pdf": row.flashcards.studied,
                                  "respondidas_pdf": row.qbank.studied if row.qbank else None})
    measurements = {}
    for measurement in sorted(PlanningService(repo).measurements(), key=lambda m: (m["observed_date"], m["id"])):
        if measurement["observed_date"] <= as_of:
            measurements[measurement["kind"]] = {k: v for k, v in measurement.items() if k not in {"payload", "digest"}}
    return {"qbank": cover(q), "flashcards": cover(f), "areas": list(areas.values()),
            "classification": analyzed["stats"], "planner": {state: counts[state] for state in ("sugerido", "aguardando_validacao", "aprovado_usuario", "aplicado_manualmente", "reativado", "cancelado")},
            "pending_reviews": None, "future_reviews": None, "longitudinal_available": len(dates) > 1,
            "manual_measurements": measurements, "reevaluation_due": len(planner.due_items(as_of)), "practice_gaps": sorted(practice_gaps, key=lambda r: -r["cartoes_estudados_pdf"])}
