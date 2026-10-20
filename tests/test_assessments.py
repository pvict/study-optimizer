import csv
from io import StringIO
import json
import sqlite3

import pytest

from osler.assessment_service import AssessmentService
from osler.classification import ClassifierConfig
from osler.matching_service import load_matching
from osler.service import import_bytes
from osler.storage import Repository
from test_classification import known


def setup_assessment(tmp_path, sample_pdf):
    repo = Repository(tmp_path)
    q = import_bytes(repo, sample_pdf(), "q.pdf").report
    f = import_bytes(repo, sample_pdf(kind="flashcards"), "f.pdf").report
    matching = load_matching(repo, q.file_sha256, f.file_sha256)
    row = next(r for r in matching.rows if r.qbank and "Feridas" in r.qbank.name)
    return repo, AssessmentService(repo), matching, row


def test_observations_append_preserve_sources_and_detect_conflict(tmp_path, sample_pdf):
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    before = repo.get_report(matching.qbank_report_id).to_dict()
    first = service.save_observation(matching, row.row_id, known(), expected_revision=0)
    with pytest.raises(ValueError, match="[Rr]evis"):
        service.save_observation(matching, row.row_id, known(nota="edição concorrente"), expected_revision=0)
    service.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=83), expected_revision=1)
    history = service.store.history(row.row_id)
    assert len(history) == 2
    assert history[0]["id"] == first
    assert history[0]["observation"]["acerto_primeira_tentativa"] == 82
    assert repo.get_report(matching.qbank_report_id).to_dict() == before
    result = service.analyze(matching, "2026-10-14")
    item = next(i for i in result["items"] if i["row_id"] == row.row_id)
    assert item["classification"]["category"] == "B"
    assert item["observation"]["acerto_primeira_tentativa"] == 83


def test_analysis_uses_date_cutoff_and_revoke_keeps_history(tmp_path, sample_pdf):
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    first = service.save_observation(matching, row.row_id, known(), 0)
    second = service.save_observation(matching, row.row_id, known(data_observacao="2026-10-15", acerto_primeira_tentativa=60), 1)
    def category(day):
        return next(i for i in service.analyze(matching, day)["items"] if i["row_id"] == row.row_id)["classification"]["category"]
    assert category("2026-10-13") == "D"
    assert category("2026-10-14") == "B"
    assert category("2026-10-15") == "C"
    service.revoke(second, expected_revision=2)
    assert category("2026-10-15") == "B"
    assert len(service.store.history(row.row_id)) == 2
    assert len(service.store.events()) == 3


def test_csv_import_is_atomic_and_blank_rows_are_skipped(tmp_path, sample_pdf):
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    template = service.csv_template(matching, "2026-10-14")
    rows = list(csv.DictReader(StringIO(template.decode("utf-8-sig")), delimiter=";"))
    target = next(r for r in rows if r["registro_id"] == row.row_id)
    target.update({k: "" if v is None else str(v) for k, v in known().to_dict().items()})
    def encoded(items):
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=list(items[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(items)
        return output.getvalue().encode("utf-8-sig")
    broken = [dict(r) for r in rows]
    other = next(r for r in broken if r["registro_id"] != row.row_id)
    other.update(data_observacao="2026-10-14", origem_da_informacao="manual", nivel_de_confiabilidade="informado_usuario", questoes_distintas="-1")
    with pytest.raises(ValueError):
        service.import_csv(matching, encoded(broken))
    assert not service.store.history(row.row_id)
    assert service.import_csv(matching, encoded(rows)) == 1
    assert len(service.store.history(row.row_id)) == 1


def test_csv_unknown_header_or_wrong_context_is_rejected(tmp_path, sample_pdf):
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    with pytest.raises(ValueError):
        service.import_csv(matching, b"registro_id;inventado\nmissing;1\n")
    with pytest.raises(ValueError):
        service.save_observation(matching, "outro_contexto", known(), 0)
    assert service.store.events() == []


def test_policy_versions_and_result_exports_are_immutable(tmp_path, sample_pdf):
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    policy_id = service.store.save_policy("Inicial", ClassifierConfig())
    assert service.store.policies()[0]["id"] == policy_id
    old = service.export(service.analyze(matching, "2026-10-14"))
    previous = old.json_path.read_bytes()
    service.save_observation(matching, row.row_id, known(), 0)
    new = service.export(service.analyze(matching, "2026-10-14"))
    assert old.folder != new.folder
    assert old.json_path.read_bytes() == previous
    assert json.loads(new.json_path.read_bytes())["stats"]["B"] == 1
    assert new.csv_path.is_file()
    with sqlite3.connect(repo.db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def test_real_snapshot_context_is_not_transferred(tmp_path, sample_pdf):
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    service.save_observation(matching, row.row_id, known(), 0)
    changed = import_bytes(repo, sample_pdf(kind="flashcards", date="15/10/2026"), "f2.pdf").report
    other = load_matching(repo, matching.qbank_report_id, changed.file_sha256)
    result = service.analyze(other, "2026-10-15")
    assert result["stats"]["B"] == 0


def test_old_observation_does_not_remain_candidate_forever(tmp_path, sample_pdf):
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    service.save_observation(matching, row.row_id, known(), 0)
    result = service.analyze(matching, "2027-02-01")
    item = next(i for i in result["items"] if i["row_id"] == row.row_id)
    assert item["classification"]["category"] == "D"
    assert "antiga" in " ".join(item["classification"]["reasons"]).lower()


def test_pdf_percentage_limits_remain_explicit_in_classification(tmp_path, sample_pdf):
    from osler.models import parse_percentage
    from osler.assessment_service import result_records
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    row.qbank.acerto_pdf = parse_percentage("<1%")
    item = next(i for i in result_records(service.analyze(matching, "2026-10-14")) if i["registro_id"] == row.row_id)
    assert item["acerto_pdf_operador"] == "<"
    assert item["acerto_pdf_texto"] == "<1%"
