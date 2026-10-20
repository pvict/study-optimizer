import pytest

from osler.extraction import ImportFailure, extract_pdf
from osler.models import normalize_path, parse_percentage


def test_identifies_content_despite_misleading_filename(sample_pdf):
    report = extract_pdf(sample_pdf(), "flashcards_1999.pdf")
    assert (report.kind, report.scope, report.report_date) == ("qbank", "todos", "2026-10-14")
    assert report.summary["estudados"] == 44
    assert report.summary["total"] == 100


def test_hierarchy_survives_continuation_and_wrapped_name(sample_pdf):
    report = extract_pdf(sample_pdf(), "sample.pdf")
    row = next(r for r in report.records if "Feridas" in r.name)
    assert row.path == ["Clínica Cirúrgica", "Cirurgia Plástica", "Cicatrização e Avaliação de Feridas"]
    assert row.studied == 44
    assert row.page == 3
    assert row.is_leaf
    assert [r.is_leaf for r in report.records] == [False, False, True, True]


def test_pdf_accuracy_never_becomes_attempt_accuracy(sample_pdf):
    r = extract_pdf(sample_pdf(), "sample.pdf").records[-2]
    assert r.acerto_pdf.value == 95
    assert r.acerto_primeira_tentativa is None
    assert r.acerto_ultima_tentativa is None
    assert r.questoes_distintas is None
    assert r.respostas_totais is None


def test_flashcard_review_is_coverage_and_missing_stays_missing(sample_pdf):
    r = extract_pdf(sample_pdf(kind="flashcards"), "qbank.pdf").records[-2]
    assert r.percentual_revisado.value == 95
    assert r.acerto_pdf.value is None
    assert r.studied == 146
    assert r.cartoes_pendentes is None
    assert r.cartoes_futuros is None


@pytest.mark.parametrize("text,value,operator", [("-", None, None), ("<1%", 1, "<"), ("82%", 82, "="), ("82,5%", 82.5, "=")])
def test_percentages_preserve_limits(text, value, operator):
    pct = parse_percentage(text)
    assert (pct.value, pct.operator, pct.raw) == (value, operator, text)


def test_normalization_preserves_ancestry():
    assert normalize_path([" Clínica  Médica ", "Cardiologia"]) == ["clinica medica", "cardiologia"]
    assert normalize_path(["Pediatria", "Cardiologia"]) != normalize_path(["Clínica Médica", "Cardiologia"])


def test_missing_date_is_flagged_not_taken_from_filename(sample_pdf):
    report = extract_pdf(sample_pdf(date=""), "2026-10-14.pdf")
    assert report.report_date is None
    assert "data_ausente" in {f.code for f in report.findings}


def test_inconsistent_counts_are_preserved_and_flagged(sample_pdf):
    report = extract_pdf(sample_pdf(bad_counts=True), "bad.pdf")
    assert report.records[-2].studied == 110
    assert "estudados_maior_total" in {f.code for f in report.findings}
    assert report.status == "revisar"


@pytest.mark.parametrize("data", [b"", b"not a pdf", b"%PDF-damaged"])
def test_invalid_files_have_clear_failure(data):
    with pytest.raises(ImportFailure):
        extract_pdf(data, "anything.pdf")


def test_image_only_pdf_is_rejected():
    import pymupdf
    doc = pymupdf.open()
    doc.new_page()
    with pytest.raises(ImportFailure, match="textual"):
        extract_pdf(doc.tobytes(), "scan.pdf")
    doc.close()


def test_password_protection_is_rejected(sample_pdf):
    import pymupdf
    with pymupdf.open(stream=sample_pdf(), filetype="pdf") as doc:
        data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="test", owner_pw="owner")
    with pytest.raises(ImportFailure, match="senha"):
        extract_pdf(data, "protected.pdf")


def test_unrelated_pdf_is_rejected():
    import pymupdf
    with pymupdf.open() as doc:
        doc.new_page().insert_text((48, 80), "Relatório de outra fonte")
        data = doc.tobytes()
    with pytest.raises(ImportFailure, match="Conteúdo"):
        extract_pdf(data, "osler_qbank.pdf")


def test_unknown_table_page_is_not_silently_skipped(sample_pdf):
    import pymupdf
    with pymupdf.open(stream=sample_pdf(), filetype="pdf") as doc:
        doc.new_page().insert_text((48, 80), "Tabela com outro formato")
        data = doc.tobytes()
    report = extract_pdf(data, "partial.pdf")
    assert report.status == "revisar"
    assert "pagina_sem_tabela" in {f.code for f in report.findings}
    assert report.table_pages == 2
