from copy import deepcopy
from datetime import date
import sqlite3

import pytest

from osler.guide import GuideSettings, daily_blocks, roadmap, rank_topics
from osler.incidence import parse_html_table, parse_incidence, incidence_for_topic
from osler.guide_service import GuideService
from test_assessments import setup_assessment


@pytest.mark.parametrize("minutes", [15, 30, 45, 60, 90, 120, 180, 240, 360])
def test_daily_guide_fits_without_carry_over(minutes):
    blocks = daily_blocks(minutes, "normal")
    assert sum(b["minutes"] for b in blocks) <= minutes
    assert blocks[0]["kind"] == "questoes"
    assert next((b["minutes"] for b in blocks if b["kind"] == "gerais"), 0) <= 15
    assert daily_blocks(minutes, "descanso") == []
    assert daily_blocks(minutes, "plantao") == daily_blocks(min(minutes, 45), "normal")


def test_roadmap_has_three_connected_phases_and_known_target():
    phases = roadmap("2026-10-15", "2027-11-30")
    assert len(phases) == 3
    assert phases[0]["start"] == "2026-10-15"
    assert phases[-1]["end"] == "2027-11-30"
    assert "oficial" not in phases[0]["title"].lower()
    with pytest.raises(ValueError):
        roadmap("2027-12-01", "2027-11-30")


def test_practice_guide_works_without_per_topic_indicators(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    report = repo.get_report(matching.qbank_report_id)
    queue = rank_topics(report, {}, [], [], "2026-10-15")
    assert queue
    assert all(i["action"] == "praticar" for i in queue)
    assert all(i["suspend"] is False for i in queue)
    assert len(queue) == 2  # somente folhas, sem pais


def test_html_reads_only_table_and_preserves_breadcrumb():
    html = '''<html><script>fetch('https://never.example')</script><table><thead><tr><th>Tema</th><th>Questões</th><th>Incidência</th></tr></thead><tbody><tr><td><span class="PrimaryText-abc">Saúde do Trabalhador</span><span class="SecondaryText-def">Preventiva &amp; Social &gt;&gt; Medicina Legal</span></td><td>203</td><td>7,1%</td></tr></tbody></table></html>'''
    table = parse_html_table(html)
    assert table["headers"] == ["Tema", "Questões", "Incidência"]
    assert table["rows"][0][0] == "Preventiva & Social → Medicina Legal → Saúde do Trabalhador"
    assert len(table["rows"]) == 1
    assert "fetch" not in str(table)


def test_html_preserves_incidence_labels_in_accessible_icons():
    html = '<table><tr><th>Tema</th><th>Questões</th><th>Incidência</th></tr><tr><td>Outro</td><td>3</td><td><div role="img" aria-label="Incidência alta" title="Incidência alta"><svg aria-hidden="true"></svg></div></td></tr></table>'
    assert parse_html_table(html)["rows"][0][2] == "Incidência alta"


def test_incidence_maps_exact_unique_names_and_keeps_ambiguity(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    report = repo.get_report(matching.qbank_report_id)
    copied = "Tema\tQuestões\nCicatrização e Avaliação de Feridas\t203\nOutro\t20\nNão existe\t10\n"
    parsed = parse_incidence(copied, report, "questoes")
    assert parsed[0]["path"] == report.records[2].path
    assert parsed[2]["path"] is None
    duplicated = deepcopy(report)
    duplicated.records.append(deepcopy(report.records[2]))
    duplicated.records[-1].path[0] = "Pediatria"
    result = parse_incidence("Tema;Questões\nCicatrização e Avaliação de Feridas;203", duplicated, "questoes")
    assert result[0]["path"] is None


def test_incidence_parent_is_context_and_different_institutions_are_not_summed():
    path = ["Clínica", "Cardiologia", "Arritmias"]
    datasets = [{"id": 1, "institutions": ["A"], "observed_date": "2026-10-14", "unit": "questoes", "rows": [
        {"path": ["Clínica", "Cardiologia"], "value": 100, "band": "alta"}, {"path": path, "value": 12, "band": "media"}]},
        {"id": 2, "institutions": ["B"], "observed_date": "2026-10-14", "unit": "questoes", "rows": [{"path": path, "value": 30, "band": "alta"}]}]
    result = incidence_for_topic(path, datasets, ["A"], "2026-10-15")
    assert len(result) == 1 and result[0]["value"] == 12
    assert result[0]["exact"] is True
    assert incidence_for_topic(path, datasets, ["C"], "2026-10-15") == []
    pooled = [{**datasets[0], "institutions": ["A", "B"]}]
    assert incidence_for_topic(path, pooled, ["A"], "2026-10-15") == []


def test_parts_of_same_consultation_merge_without_adding_duplicate_counts():
    one, two = ["Área", "Tema 1"], ["Área", "Tema 2"]
    datasets = [{"id": 1, "institutions": ["A"], "observed_date": "2026-10-15", "unit": "questoes", "rows": [{"path": one, "value": 12, "band": "alta"}]},
                {"id": 2, "institutions": ["A"], "observed_date": "2026-10-15", "unit": "questoes", "rows": [{"path": two, "value": 10, "band": "alta"}, {"path": one, "value": 12, "band": "alta"}]}]
    assert incidence_for_topic(one, datasets, ["A"], "2026-10-15")[0]["value"] == 12
    assert incidence_for_topic(two, datasets, ["A"], "2026-10-15")[0]["value"] == 10
    datasets[1]["rows"] = [{"path": two, "value": 10, "band": "alta"}]
    assert incidence_for_topic(one, datasets, ["A"], "2026-10-15")[0]["value"] == 12
    datasets[1]["observed_date"] = "2026-10-16"
    assert incidence_for_topic(one, datasets, ["A"], "2026-10-16") == []


def test_parent_incidence_suggests_the_parent_topic_without_multiplying_children(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    report = repo.get_report(matching.qbank_report_id)
    parent = report.records[1].path
    data = [{"id": 1, "institutions": ["A"], "observed_date": "2026-10-15", "unit": "questoes", "rows": [{"path": parent, "topic": "Cirurgia Plástica", "value": 36, "band": "alta"}]}]
    queue = rank_topics(report, {}, data, ["A"], "2026-10-15")
    assert len(queue) == 1
    assert queue[0]["path"] == parent
    assert queue[0]["incidence"][0]["value"] == 36


def test_feedback_on_suggested_parent_prioritizes_that_same_topic(tmp_path, sample_pdf):
    repo, _, matching, _ = setup_assessment(tmp_path, sample_pdf)
    report = repo.get_report(matching.qbank_report_id)
    parent = report.records[1].path
    data = [{"id": 1, "institutions": ["A"], "observed_date": "2026-10-15", "unit": "questoes", "rows": [{"path": parent, "value": 36, "band": "alta"}]}]
    from osler.models import normalize_path
    queue = rank_topics(report, {}, data, ["A"], "2026-10-15", [tuple(normalize_path(parent))])
    assert queue[0]["path"] == parent
    assert queue[0]["tier"] == 0
    assert "dificuldade" in queue[0]["reason"]


def test_day_corrections_keep_history_and_last_choice_wins(tmp_path, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    guide = GuideService(repo)
    first = guide.save_day("2026-10-15", "feito", [])
    assert guide.save_day("2026-10-15", "feito", []) == first
    second = guide.save_day("2026-10-15", "parcial", [])
    third = guide.save_day("2026-10-15", "feito", [])
    assert first < second < third
    assert guide.days()[0]["status"] == "feito"
    with repo._connection() as db:
        assert db.execute("SELECT COUNT(*) FROM guide_days").fetchone()[0] == 3


def test_settings_days_and_incidence_are_local_versions(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    guide = GuideService(repo)
    initial = guide.settings()
    new = GuideSettings(institutions=["A"], normal_minutes=120, shift_minutes=30)
    sid = guide.save_settings(new, initial["id"])
    assert guide.settings()["id"] == sid
    with pytest.raises(ValueError):
        guide.save_settings(new, initial["id"])
    with pytest.raises(ValueError):
        guide.import_incidence("Tema;Questões\nOutro;10\nFeridas;NaN", "questoes", ["A"], "2026-10-15")
    assert guide.datasets() == []
    guide.import_incidence("Tema;Questões\nCicatrização e Avaliação de Feridas;203\nOutro;10", "questoes", ["A"], "2026-10-15")
    result = guide.guide("2026-10-15", 120, "normal")
    assert result["topics"]
    assert result["topics"][0]["incidence"]
    guide.save_day("2026-10-15", "parcial", result["topics"][0]["path"], "dificil")
    assert "questoes_feitas" not in guide.days()[0]
    assert guide.days()[0]["status"] == "parcial"
    assert all(i["suspend"] is False for i in result["topics"])
    from osler.planning_service import PlanningService
    PlanningService(repo)
    with sqlite3.connect(repo.db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 6
    from osler.backups import create_backup, inspect_backup
    assert inspect_backup(create_backup(repo).read_bytes())["schema_version"] == 6


@pytest.mark.parametrize("text,unit", [("Tema;Questões\nOutro;-1", "questoes"), ("Tema;Questões\nOutro;1.5", "questoes"), ("Tema;Valor\nOutro;101%", "percentual")])
def test_bad_incidence_does_not_become_priority(tmp_path, sample_pdf, text, unit):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    with pytest.raises(ValueError):
        parse_incidence(text, repo.get_report(matching.qbank_report_id), unit)
