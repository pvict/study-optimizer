from dataclasses import replace
from io import StringIO
import csv
import json

import pytest

from osler.extraction import extract_pdf
from osler.matching import ManualMatch, build_matching
from osler.matching_exports import matching_csv, matching_json, unified_records
from osler.models import Finding, stable_topic_id


def renamed(row, path):
    return replace(row, path=path, topic_id=stable_topic_id(path), level=len(path)-1)


def pair(sample_pdf):
    return extract_pdf(sample_pdf(), "q.pdf"), extract_pdf(sample_pdf(kind="flashcards"), "f.pdf")


def test_exact_full_hierarchy_matches_and_preserves_values(sample_pdf):
    q, f = pair(sample_pdf)
    result = build_matching(q, f)
    assert result.stats["pares_exatos"] == 4
    rows = unified_records(result)
    row = next(r for r in rows if "Feridas" in r["hierarquia_qbank"])
    assert row["questoes_respondidas"] == 44
    assert row["cartoes_estudados"] == 146
    assert row["acerto_pdf"] == 95
    assert row["acerto_primeira_tentativa"] is None
    assert row["cartoes_pendentes"] is None


def test_exact_matching_normalizes_accents_case_and_spaces(sample_pdf):
    q, f = pair(sample_pdf)
    f.records[-2] = renamed(f.records[-2], [" CLINICA  CIRURGICA ", "cirurgia plastica", "cicatrizacao e avaliacao de feridas"])
    assert build_matching(q, f).stats["pares_exatos"] == 4


def test_same_name_in_other_area_is_never_joined(sample_pdf):
    q, f = pair(sample_pdf)
    f.records = [renamed(r, ["Pediatria", *r.path[1:]]) for r in f.records]
    result = build_matching(q, f, threshold=0.5)
    assert result.stats["pares_total"] == 0
    assert not result.suggestions
    assert len(result.rows) == 8


def test_duplicate_hierarchy_preserves_rows_and_blocks_automatic_match(sample_pdf):
    q, f = pair(sample_pdf)
    q.records.append(replace(q.records[-2], studied=43))
    result = build_matching(q, f)
    assert result.stats["pares_total"] == 3
    assert result.stats["bloqueados_qbank"] == 2
    assert result.stats["bloqueados_flashcards"] == 1
    assert len(result.rows) == 6
    assert len({row.row_id for row in result.rows}) == 6


def test_granularity_difference_is_visible_and_not_counted_as_terminal_pair(sample_pdf):
    q, f = pair(sample_pdf)
    q.records[-2].is_leaf = False
    result = build_matching(q, f)
    row = next(r for r in result.rows if r.qbank and "Feridas" in r.qbank.name)
    assert row.row_type == "granularidade_diferente"
    assert result.stats["granularidades_diferentes"] == 1
    assert result.stats["pares_terminais"] == 1


def test_close_name_is_only_suggestion_never_automatic(sample_pdf):
    q, f = pair(sample_pdf)
    f.records[-2] = renamed(f.records[-2], [*f.records[-2].path[:-1], "Cicatrização e Avaliação das Feridas"])
    result = build_matching(q, f)
    assert result.stats["pares_total"] == 3
    assert [(s.qbank_index, s.flashcards_index) for s in result.suggestions] == [(2, 2)]
    assert result.stats["sem_flashcards"] == 1
    assert result.stats["sem_qbank"] == 1


def test_similar_name_in_other_parent_not_suggested(sample_pdf):
    q, f = pair(sample_pdf)
    f.records[-2] = renamed(f.records[-2], ["Clínica Cirúrgica", "Cirurgia Vascular", "Cicatrização e Avaliação das Feridas"])
    assert not build_matching(q, f).suggestions


def test_manual_match_requires_note_and_is_one_to_one(sample_pdf):
    q, f = pair(sample_pdf)
    f.records[-2] = renamed(f.records[-2], [*f.records[-2].path[:-1], "Cicatrização e Avaliação das Feridas"])
    result = build_matching(q, f, [ManualMatch(2, 2, "Conferidos os dois caminhos")])
    assert result.stats["pares_manuais"] == 1
    assert result.stats["pares_total"] == 4
    assert not result.suggestions
    with pytest.raises(ValueError):
        build_matching(q, f, [ManualMatch(2, 2, "")])
    with pytest.raises(ValueError):
        build_matching(q, f, [ManualMatch(2, 2, "ok"), ManualMatch(2, 2, "duplicado")])


def test_manual_match_cannot_override_exact_or_cross_area(sample_pdf):
    q, f = pair(sample_pdf)
    with pytest.raises(ValueError):
        build_matching(q, f, [ManualMatch(2, 2, "já era exata")])
    f.records[-2] = renamed(f.records[-2], ["Pediatria", *f.records[-2].path[1:]])
    with pytest.raises(ValueError):
        build_matching(q, f, [ManualMatch(2, 2, "área errada")])


def test_different_dates_are_exposed_with_warning(sample_pdf):
    q, f = pair(sample_pdf)
    f.report_date = "2026-10-15"
    result = build_matching(q, f)
    assert "datas_diferentes" in {f.code for f in result.findings}
    row = unified_records(result)[0]
    assert row["data_qbank"] == "2026-10-14"
    assert row["data_flashcards"] == "2026-10-15"


def test_wrong_report_role_and_incomplete_extraction_are_rejected(sample_pdf):
    q, f = pair(sample_pdf)
    with pytest.raises(ValueError):
        build_matching(f, q)
    q.findings.append(Finding("hierarquia_incompleta", "erro", "parcial"))
    with pytest.raises(ValueError):
        build_matching(q, f)


def test_unmatched_source_stays_absent_and_csv_keeps_operators(sample_pdf):
    q, f = pair(sample_pdf)
    f.records.pop()
    result = build_matching(q, f)
    rows = list(csv.DictReader(StringIO(matching_csv(result).decode("utf-8-sig")), delimiter=";"))
    orphan = next(r for r in rows if r["associacao"] == "somente_qbank")
    assert orphan["cartoes_estudados"] == ""
    assert orphan["percentual_visto_qbank_operador"] == "<"
    assert rows[0]["percentual_visto_qbank_operador"] == "="
    payload = json.loads(matching_json(result))
    assert payload["qbank_report_id"] == q.file_sha256
    assert payload["stats"]["pares_total"] == 3


def test_terminal_directly_below_area_can_receive_suggestion(sample_pdf):
    q, f = pair(sample_pdf)
    q.records = [replace(renamed(q.records[-1], ["Área", "Tema próximo"]), is_leaf=True)]
    f.records = [replace(renamed(f.records[-1], ["Área", "Tema próxmo"]), is_leaf=True)]
    assert len(build_matching(q, f).suggestions) == 1


def test_missing_summary_includes_total_responses(sample_pdf):
    q, f = pair(sample_pdf)
    assert "respostas_totais" in unified_records(build_matching(q, f))[0]["dados_ausentes"]


@pytest.mark.real
def test_matching_real_complete_reports(project_root):
    q_path = project_root / "acervo_qbank_2026-10-14 (1).pdf"
    f_path = project_root / "acervo_flashcards_2026-10-14 (1).pdf"
    if not q_path.exists() or not f_path.exists():
        pytest.skip("Par completo real não disponível.")
    q, f = extract_pdf(q_path.read_bytes(), q_path.name), extract_pdf(f_path.read_bytes(), f_path.name)
    result = build_matching(q, f)
    assert result.stats["pares_exatos"] == 738
    assert result.stats["pares_terminais"] == 555
    assert result.stats["granularidades_diferentes"] == 20
    assert result.stats["sem_flashcards"] == 949
    assert result.stats["sem_qbank"] == 823
    assert len(result.rows) == 2510
    row = next(r for r in unified_records(result) if (r["hierarquia_qbank"] or "").endswith("Cicatrização e Avaliação de Feridas"))
    assert row["questoes_respondidas"] == 44
    assert row["cartoes_estudados"] == 146
    assert row["acerto_pdf"] == 95
    assert row["percentual_revisado"] == 82
    assert row["acerto_primeira_tentativa"] is None
