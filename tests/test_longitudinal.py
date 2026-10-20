import pytest

from osler.longitudinal import compare_reports, decision_timeline
from osler.service import import_bytes
from osler.storage import Repository


def test_comparison_keeps_cover_totals_and_pdf_attempt_unknown(tmp_path, sample_pdf):
    repo = Repository(tmp_path)
    old = import_bytes(repo, sample_pdf(), "old.pdf").report
    new = import_bytes(repo, sample_pdf(date="15/10/2026"), "new.pdf").report
    result = compare_reports(repo, old.file_sha256, new.file_sha256)
    assert result["cover"]["studied_delta"] == 0
    assert len(result["common"]) == 2
    assert result["common"][0]["pdf_metric_delta_pp"] == 0
    assert "tentativa" in result["metric_label"]
    assert "causal" in " ".join(result["warnings"])
    assert decision_timeline(repo) == []


@pytest.mark.parametrize("new_kind,new_scope,new_date", [("flashcards", "Todos", "15/10/2026"), ("qbank", "Iniciados", "15/10/2026"),
                                                       ("qbank", "Todos", "14/10/2026"), ("qbank", "Todos", "13/10/2026")])
def test_incompatible_sources_are_not_presented_as_evolution(tmp_path, sample_pdf, new_kind, new_scope, new_date):
    repo = Repository(tmp_path)
    old = import_bytes(repo, sample_pdf(), "old.pdf").report
    new = import_bytes(repo, sample_pdf(kind=new_kind, scope=new_scope, date=new_date), "new.pdf").report
    with pytest.raises(ValueError):
        compare_reports(repo, old.file_sha256, new.file_sha256)


def test_changed_hierarchy_and_percentage_limits_remain_explicit(tmp_path, sample_pdf, monkeypatch):
    from osler.models import parse_percentage
    repo = Repository(tmp_path)
    old = import_bytes(repo, sample_pdf(), "old.pdf").report
    new = import_bytes(repo, sample_pdf(date="15/10/2026"), "new.pdf").report
    old.records[2].acerto_pdf = parse_percentage("<1%")
    new.records[3].path[-1] = "Tema novo"
    original = repo.get_report
    monkeypatch.setattr(repo, "get_report", lambda key: old if key == old.file_sha256 else new)
    result = compare_reports(repo, old.file_sha256, new.file_sha256)
    assert result["common"][0]["pdf_metric_delta_pp"] is None
    assert len(result["added"]) == len(result["removed"]) == 1
    assert "<1%" == result["common"][0]["old_pdf_metric"]
