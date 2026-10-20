from osler.dashboard import build_dashboard
from test_assessments import setup_assessment


def test_dashboard_uses_cover_totals_and_separate_area_rows(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    result = build_dashboard(repo, matching.qbank_report_id, matching.flashcards_report_id, "2026-10-14")
    assert result["qbank"]["studied"] == 44
    assert result["flashcards"]["studied"] == 146
    assert len(result["areas"]) == 1
    assert result["areas"][0]["qbank_studied"] == 44
    assert result["areas"][0]["flashcards_studied"] == 146
    assert result["pending_reviews"] is None
    assert result["future_reviews"] is None
    assert result["longitudinal_available"] is False
    assert result["planner"]["aplicado_manualmente"] == 0
    assert result["classification"]["B"] == 0


def test_manual_agenda_metrics_keep_separate_denominators_and_sources(tmp_path, sample_pdf):
    from osler.planning import Measurement
    from osler.planning_service import PlanningService
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    planning = PlanningService(repo)
    planning.save_measurement(Measurement("cartoes_pendentes", 2002, "2026-10-14", "Outra tela", approximate=True))
    planning.save_measurement(Measurement("revisoes_periodo", 31149, "2026-10-14", "Equilíbrio 90 dias", 90))
    result = build_dashboard(repo, matching.qbank_report_id, matching.flashcards_report_id, "2026-10-14")
    assert result["manual_measurements"]["cartoes_pendentes"]["count"] == 2002
    assert result["manual_measurements"]["revisoes_periodo"]["count"] == 31149
    assert result["pending_reviews"] is None
