from dataclasses import replace
import hashlib
import json

import pandas as pd
import pytest

from osler.extraction import extract_pdf
from osler.exports import records_csv, report_json
from osler.service import import_bytes
from osler.storage import Repository


def test_import_preserves_exact_original_and_roundtrips(tmp_path, sample_pdf):
    repo = Repository(tmp_path)
    data = sample_pdf()
    result = import_bytes(repo, data, "../misleading.pdf")
    assert result.state == "importado"
    assert repo.original_path(result.report.file_sha256).read_bytes() == data
    assert repo.get_report(result.report.file_sha256).to_dict() == result.report.to_dict()
    assert repo.list_reports()[0]["filename"] == "misleading.pdf"
    assert len(repo.list_reports()) == 1
    assert repo.audit_events()[0]["event"] == "importado"
    assert result.csv_path.is_file()
    assert result.json_path.is_file()


def test_same_file_is_idempotent(tmp_path, sample_pdf):
    repo = Repository(tmp_path)
    data = sample_pdf()
    first = import_bytes(repo, data, "one.pdf")
    before = repo.original_path(first.report.file_sha256).stat().st_mtime_ns
    second = import_bytes(repo, data, "two.pdf")
    assert second.state == "ja_importado"
    assert len(repo.list_reports()) == 1
    assert repo.original_path(first.report.file_sha256).stat().st_mtime_ns == before
    assert second.report.file_sha256 == first.report.file_sha256


def test_semantic_duplicate_keeps_both_originals(tmp_path, sample_pdf):
    import pymupdf
    repo = Repository(tmp_path)
    data = sample_pdf()
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        doc.set_metadata({"title": "Same tables, different metadata"})
        second_data = doc.tobytes()
    a = import_bytes(repo, data, "first.pdf")
    b = import_bytes(repo, second_data, "second.pdf")
    assert b.state == "equivalente"
    assert b.duplicate_of == a.report.file_sha256
    assert len(repo.list_reports()) == 2
    assert len(repo.list_reports(include_duplicates=False)) == 1
    assert repo.original_path(b.report.file_sha256).read_bytes() == second_data


def test_existing_original_cannot_be_silently_overwritten(tmp_path, sample_pdf):
    repo = Repository(tmp_path)
    data = sample_pdf()
    digest = hashlib.sha256(data).hexdigest()
    repo.original_path(digest).write_bytes(b"different original")
    with pytest.raises(ValueError, match="integridade"):
        import_bytes(repo, data, "sample.pdf")
    assert not repo.list_reports()
    assert repo.original_path(digest).read_bytes() == b"different original"


def test_exports_keep_missing_values_and_percentual_operator(sample_pdf):
    from io import BytesIO
    report = extract_pdf(sample_pdf(), "sample.pdf")
    data = records_csv(report)
    assert data.startswith(b"\xef\xbb\xbf")
    frame = pd.read_csv(BytesIO(data), sep=";")
    assert frame["acerto_primeira_tentativa"].isna().all()
    assert frame.iloc[-1]["percentual_visto_operador"] == "<"
    assert frame.iloc[-1]["percentual_visto_texto"] == "<1%"
    assert frame.iloc[-2]["questoes_respondidas"] == 44
    assert frame["cartoes_estudados"].isna().all()
    assert json.loads(report_json(report))["records"][-2]["studied"] == 44


def test_export_escapes_spreadsheet_formula_names(sample_pdf):
    report = extract_pdf(sample_pdf(), "sample.pdf")
    report.records[-1] = replace(report.records[-1], path=["=dangerous formula"])
    from io import BytesIO
    frame = pd.read_csv(BytesIO(records_csv(report)), sep=";")
    assert frame.iloc[-1]["area"].startswith("'")
    assert report.records[-1].path == ["=dangerous formula"]


def test_invalid_pdf_does_not_create_report(tmp_path):
    repo = Repository(tmp_path)
    with pytest.raises(ValueError):
        import_bytes(repo, b"bad file", "fake.pdf")
    assert not repo.list_reports()


def test_csv_preserves_structured_percentage_operators(sample_pdf):
    import csv
    from io import StringIO
    from osler.models import parse_percentage
    report = extract_pdf(sample_pdf(), "sample.pdf")
    report.records[-1].percentual_revisado = parse_percentage(">90%")
    rows = list(csv.DictReader(StringIO(records_csv(report).decode("utf-8-sig")), delimiter=";"))
    assert rows[-2]["percentual_visto_operador"] == "="
    assert rows[-2]["acerto_pdf_operador"] == "="
    assert rows[-1]["percentual_visto_operador"] == "<"
    assert rows[-1]["percentual_revisado_operador"] == ">"


@pytest.mark.parametrize("failure_prefix", [b"%PDF-", b"\xef\xbb\xbf"])
def test_partial_write_can_be_retried_without_truncated_destination(tmp_path, sample_pdf, monkeypatch, failure_prefix):
    from pathlib import Path
    repo = Repository(tmp_path)
    data = sample_pdf()
    real_open = Path.open

    class FaultyStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def write(self, payload):
            if payload.startswith(failure_prefix):
                self.stream.write(payload[:4])
                raise OSError("simulated disk failure")
            return self.stream.write(payload)

    def failing_open(path, mode="r", *args, **kwargs):
        stream = real_open(path, mode, *args, **kwargs)
        return FaultyStream(stream) if mode in {"xb", "wb"} else stream

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", failing_open)
        with pytest.raises(OSError, match="simulated"):
            import_bytes(repo, data, "sample.pdf")
    result = import_bytes(repo, data, "sample.pdf")
    assert repo.original_path(result.report.file_sha256).read_bytes() == data
    assert result.csv_path.read_bytes() == records_csv(result.report)
    assert len(repo.list_reports()) == 1
    assert not list(tmp_path.rglob(".partial-*"))
