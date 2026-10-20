import pytest

from osler.extraction import extract_pdf


@pytest.fixture(scope="module")
def real_reports():
    from pathlib import Path
    paths = sorted(Path(__file__).resolve().parents[1].glob("*.pdf"))
    if len(paths) < 5:
        pytest.skip("Os cinco PDFs reais não acompanham esta cópia do projeto.")
    return {p.name: extract_pdf(p.read_bytes(), p.name) for p in paths}


@pytest.mark.real
def test_all_five_reports_detected_from_content(real_reports):
    assert sorted((r.kind, r.scope, r.page_count) for r in real_reports.values()) == [
        ("flashcards", "iniciados", 28), ("flashcards", "todos", 49),
        ("qbank", "iniciados", 25), ("qbank", "todos", 53), ("qbank", "todos", 53)]
    assert {r.report_date for r in real_reports.values()} == {"2026-10-14"}
    assert all(r.table_pages == r.page_count - 1 for r in real_reports.values())


@pytest.mark.real
def test_real_cover_totals_and_feridas(real_reports):
    for r in real_reports.values():
        assert r.summary["estudados"] == (9249 if r.kind == "qbank" else 35548)
        assert r.summary["total"] == (111347 if r.kind == "qbank" else 91583)
        found = [row for row in r.records if row.path == ["Clínica Cirúrgica", "Cirurgia Plástica", "Cicatrização e Avaliação de Feridas"]]
        assert len(found) == 1
        assert found[0].studied == (44 if r.kind == "qbank" else 146)
        assert found[0].acerto_primeira_tentativa is None
        assert found[0].acerto_ultima_tentativa is None
        assert found[0].cartoes_pendentes is None


@pytest.mark.real
def test_complete_qbank_exports_are_semantically_equivalent(real_reports):
    a = real_reports["acervo_qbank_2026-10-14 (1).pdf"]
    b = real_reports["acervo_qbank_2026-10-14.pdf"]
    assert a.file_sha256 != b.file_sha256
    assert a.content_sha256 == b.content_sha256


@pytest.mark.real
def test_real_wrapped_name_is_not_lost(real_reports):
    report = real_reports["acervo_flashcards_2026-10-14 (1).pdf"]
    rows = [r for r in report.records if r.name == "Artérias & Veias & Sistema de Condução do Coração"]
    assert len(rows) == 1
    assert rows[0].total == 70


@pytest.mark.real
def test_declared_decks_and_themes_count_terminal_rows(real_reports):
    for report in real_reports.values():
        assert report.summary["nos_declarados"] == sum(r.is_leaf for r in report.records)
        assert "numero_nos_divergente" not in {f.code for f in report.findings}


@pytest.mark.real
def test_real_feridas_keeps_review_and_accuracy_separate(real_reports):
    for report in real_reports.values():
        row = next(r for r in report.records if r.name == "Cicatrização e Avaliação de Feridas")
        assert row.acerto_pdf.raw == ("95%" if report.kind == "qbank" else "-")
        assert row.percentual_revisado.raw == ("82%" if report.kind == "flashcards" else "-")


@pytest.mark.real
def test_all_pages_have_no_unrecognized_rows(real_reports):
    assert not [f for r in real_reports.values() for f in r.findings if f.severity == "erro"]
    assert {len(r.records) for r in real_reports.values()} == {1561, 852, 1687, 761}
