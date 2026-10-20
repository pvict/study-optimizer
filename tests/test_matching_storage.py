import json
import sqlite3

import pymupdf
import pytest

from osler.matching_service import approve_match, export_matching, load_matching, revoke_match
from osler.service import import_bytes
from osler.storage import Repository


def stored_pair(tmp_path, sample_pdf):
    repo = Repository(tmp_path)
    q = import_bytes(repo, sample_pdf(), "q.pdf").report
    raw = sample_pdf(kind="flashcards")
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        page = doc[2]
        rectangle = page.search_for("de Feridas")[0]
        page.add_redact_annot(rectangle)
        page.apply_redactions()
        page.insert_text((69, 177), "das Feridas", fontsize=9)
        raw = doc.tobytes()
    f = import_bytes(repo, raw, "f.pdf").report
    return repo, q, f


def test_manual_approval_persists_and_can_be_revoked(tmp_path, sample_pdf):
    repo, q, f = stored_pair(tmp_path, sample_pdf)
    before = repo.get_report(q.file_sha256).to_dict()
    assert load_matching(repo, q.file_sha256, f.file_sha256).stats["pares_total"] == 3
    decision_id = approve_match(repo, q.file_sha256, f.file_sha256, 2, 2, "Conferido manualmente")
    reopened = Repository(tmp_path)
    result = load_matching(reopened, q.file_sha256, f.file_sha256)
    assert result.stats["pares_manuais"] == 1
    assert result.stats["pares_total"] == 4
    assert result.manual[0].decision_id == decision_id
    assert reopened.get_report(q.file_sha256).to_dict() == before
    revoke_match(reopened, decision_id)
    assert load_matching(repo, q.file_sha256, f.file_sha256).stats["pares_total"] == 3
    assert [e["action"] for e in repo.matching_events()] == ["aprovar", "remover"]
    with pytest.raises(ValueError):
        revoke_match(repo, decision_id)


def test_conflicting_decision_does_not_replace_existing(tmp_path, sample_pdf):
    repo, q, f = stored_pair(tmp_path, sample_pdf)
    approve_match(repo, q.file_sha256, f.file_sha256, 2, 2, "Primeira decisão")
    with pytest.raises(ValueError):
        approve_match(repo, q.file_sha256, f.file_sha256, 2, 2, "Outra decisão")
    assert len(repo.active_matches(q.file_sha256, f.file_sha256)) == 1
    assert len(repo.matching_events()) == 1


def test_decision_does_not_transfer_to_another_report(tmp_path, sample_pdf):
    repo, q, f = stored_pair(tmp_path, sample_pdf)
    approve_match(repo, q.file_sha256, f.file_sha256, 2, 2, "Conferido")
    with pymupdf.open(stream=repo.original_path(f.file_sha256).read_bytes(), filetype="pdf") as doc:
        doc.set_metadata({"title": "Outra exportação"})
        new = import_bytes(repo, doc.tobytes(), "new.pdf").report
    result = load_matching(repo, q.file_sha256, new.file_sha256)
    assert result.stats["pares_manuais"] == 0
    assert result.stats["pares_total"] == 3


def test_snapshot_exports_are_immutable_and_keep_old_decisions(tmp_path, sample_pdf):
    repo, q, f = stored_pair(tmp_path, sample_pdf)
    first = export_matching(repo, load_matching(repo, q.file_sha256, f.file_sha256))
    previous = first.json_path.read_bytes()
    approve_match(repo, q.file_sha256, f.file_sha256, 2, 2, "Revisado")
    second = export_matching(repo, load_matching(repo, q.file_sha256, f.file_sha256))
    assert first.folder != second.folder
    assert first.json_path.read_bytes() == previous
    assert json.loads(previous)["stats"]["pares_total"] == 3
    assert json.loads(second.json_path.read_bytes())["stats"]["pares_total"] == 4
    repeat = export_matching(repo, load_matching(repo, q.file_sha256, f.file_sha256))
    assert repeat.folder == second.folder


def test_additive_migration_preserves_report_and_original(tmp_path, sample_pdf):
    repo, q, f = stored_pair(tmp_path, sample_pdf)
    before = repo.get_report(q.file_sha256).to_dict()
    with sqlite3.connect(repo.db_path) as db:
        db.execute("DROP TABLE IF EXISTS matching_events")
        db.execute("DROP TABLE IF EXISTS topic_matches")
        db.execute("PRAGMA user_version=1")
    reopened = Repository(tmp_path)
    assert reopened.get_report(q.file_sha256).to_dict() == before
    assert reopened.original_path(q.file_sha256).read_bytes() == repo.original_path(q.file_sha256).read_bytes()
    assert reopened.active_matches(q.file_sha256, f.file_sha256) == []
    with sqlite3.connect(repo.db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_invalid_manual_indices_or_empty_note_leave_history_unchanged(tmp_path, sample_pdf):
    repo, q, f = stored_pair(tmp_path, sample_pdf)
    for qi, fi, note in [(-1, 2, "errado"), (2, 100, "errado"), (2, 2, "  ")]:
        with pytest.raises(ValueError):
            approve_match(repo, q.file_sha256, f.file_sha256, qi, fi, note)
    assert repo.matching_events() == []
