import json

import pytest

from osler.classification import ClassifierConfig
from osler.planner_service import PlannerService
from osler.planner_exports import checklist_csv, checklist_markdown, checklist_records
from test_assessments import setup_assessment
from test_classification import known


def setup_plan(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(), 0)
    planner = PlannerService(repo)
    batch_id = planner.create_batch(matching, [row.row_id], "Lote 01 — avaliar feridas", "Rascunho para conferência manual", "2026-10-14")
    return repo, assessment, matching, row, planner, batch_id


def move(planner, item, status, **kwargs):
    return planner.transition(item["id"], status, "Conferência informada pelo usuário", item["revision"], "2026-10-14", **kwargs)


def test_batch_preserves_evidence_and_never_applies_candidate(tmp_path, sample_pdf):
    repo, assessment, matching, row, planner, batch_id = setup_plan(tmp_path, sample_pdf)
    batch = planner.get_batch(batch_id)
    item = batch["items"][0]
    assert item["status"] == "sugerido"
    assert item["applied_date"] is None
    assert item["snapshot"]["classification"]["category"] == "B"
    assert item["snapshot"]["observation"]["acerto_primeira_tentativa"] == 82
    assert item["snapshot"]["classification"]["cards_involved"] == 146
    assert batch["qbank_report_id"] == matching.qbank_report_id
    assert len(planner.events()) == 1
    assert repo.get_report(matching.qbank_report_id).records[2].acerto_pdf.value == 95


def test_batch_rejects_non_candidates_and_is_atomic(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(), 0)
    planner = PlannerService(repo)
    other = next(r for r in matching.rows if r.row_id != row.row_id)
    with pytest.raises(ValueError):
        planner.create_batch(matching, [row.row_id, other.row_id], "Inválido", "teste", "2026-10-14")
    assert planner.list_batches() == []
    assert planner.events() == []
    with pytest.raises(ValueError):
        planner.create_batch(matching, [row.row_id, row.row_id], "Duplicado", "teste", "2026-10-14")


def test_same_topic_cannot_be_in_two_active_batches(tmp_path, sample_pdf):
    repo, assessment, matching, row, planner, batch_id = setup_plan(tmp_path, sample_pdf)
    with pytest.raises(ValueError, match="ativo"):
        planner.create_batch(matching, [row.row_id], "Outro lote", "não duplicar", "2026-10-14")
    from osler.service import import_bytes
    from osler.matching_service import load_matching
    f2 = import_bytes(repo, sample_pdf(kind="flashcards", date="15/10/2026"), "f2.pdf").report
    other_matching = load_matching(repo, matching.qbank_report_id, f2.file_sha256)
    other_row = next(r for r in other_matching.rows if r.flashcards and "Feridas" in r.flashcards.name)
    assessment.save_observation(other_matching, other_row.row_id, known(data_observacao="2026-10-15"), 0)
    with pytest.raises(ValueError, match="ativo"):
        planner.create_batch(other_matching, [other_row.row_id], "Novo recorte", "não duplicar", "2026-10-15")
    assert len(planner.list_batches()) == 1


def test_manual_state_machine_and_audit(tmp_path, sample_pdf):
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    item = planner.get_batch(bid)["items"][0]
    with pytest.raises(ValueError):
        move(planner, item, "aplicado_manualmente", confirmed=True)
    move(planner, item, "aguardando_validacao")
    item = planner.get_batch(bid)["items"][0]
    with pytest.raises(ValueError, match="confirma"):
        move(planner, item, "aprovado_usuario")
    move(planner, item, "aprovado_usuario", confirmed=True)
    item = planner.get_batch(bid)["items"][0]
    with pytest.raises(ValueError, match="confirma"):
        move(planner, item, "aplicado_manualmente")
    move(planner, item, "aplicado_manualmente", confirmed=True, reevaluation_date="2026-11-14")
    item = planner.get_batch(bid)["items"][0]
    assert item["applied_date"] == "2026-10-14"
    assert item["reevaluation_date"] == "2026-11-14"
    assert planner.due_items("2026-11-14")[0]["id"] == item["id"]
    move(planner, item, "reativado", confirmed=True)
    item = planner.get_batch(bid)["items"][0]
    assert item["reactivated_date"] == "2026-10-14"
    assert planner.due_items("2026-11-14") == []
    assert len(planner.events()) == 5


def test_revision_conflict_and_invalid_dates_leave_no_partial_event(tmp_path, sample_pdf):
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    item = planner.get_batch(bid)["items"][0]
    move(planner, item, "aguardando_validacao")
    with pytest.raises(ValueError, match="[Rr]evis"):
        move(planner, item, "cancelado")
    item = planner.get_batch(bid)["items"][0]
    with pytest.raises(ValueError, match="[Dd]ata"):
        planner.transition(item["id"], "aprovado_usuario", "não deve salvar", item["revision"], "2099-01-01", confirmed=True)
    with pytest.raises(ValueError):
        planner.update_item(item["id"], "nota", "2026-02-30", item["revision"])
    assert len(planner.events()) == 2


def test_approval_revalidates_new_or_revoked_observation(tmp_path, sample_pdf):
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    move(planner, planner.get_batch(bid)["items"][0], "aguardando_validacao")
    assessment.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=60), 1)
    with pytest.raises(ValueError, match="[Ee]vid|[Ii]ndicador"):
        move(planner, planner.get_batch(bid)["items"][0], "aprovado_usuario", confirmed=True)
    assert planner.get_batch(bid)["items"][0]["status"] == "aguardando_validacao"
    assert planner.get_batch(bid)["items"][0]["snapshot"]["observation"]["acerto_primeira_tentativa"] == 82


def test_cancel_releases_topic_but_keeps_history(tmp_path, sample_pdf):
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    move(planner, planner.get_batch(bid)["items"][0], "cancelado")
    new_id = planner.create_batch(matching, [row.row_id], "Nova avaliação", "Retomar após conferência", "2026-10-14")
    assert new_id != bid
    assert planner.get_batch(bid)["items"][0]["status"] == "cancelado"
    assert len(planner.events()) == 3


def test_checklist_does_not_confuse_suggestion_with_application(tmp_path, sample_pdf):
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    batch = planner.get_batch(bid)
    record = checklist_records(batch)[0]
    assert record["estado"] == "sugerido"
    assert record["data_aplicacao"] is None
    assert record["confirmacao_manual"] == ""
    assert record["cartoes_avaliaveis"] == 146
    assert record["cartoes_ativos"] is None
    assert record["acerto_primeira_tentativa"] == 82
    assert "Feridas" in record["hierarquia"]
    assert "CONFIRMAÇÃO MANUAL" in checklist_markdown(batch)
    assert "146" in checklist_csv(batch).decode("utf-8-sig")
    exported = planner.export(bid)
    original = exported.json_path.read_bytes()
    planner.update_item(batch["items"][0]["id"], "Conferir erros críticos", "2026-11-14", 1)
    newer = planner.export(bid)
    assert newer.folder != exported.folder
    assert exported.json_path.read_bytes() == original
    assert json.loads(newer.json_path.read_bytes())["items"][0]["note"] == "Conferir erros críticos"


def test_schema_is_not_downgraded_by_older_modules(tmp_path, sample_pdf):
    import sqlite3
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    from osler.assessment_service import AssessmentService
    from osler.storage import Repository
    AssessmentService(Repository(tmp_path))
    with sqlite3.connect(repo.db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_approval_detects_evidence_change_during_validation(tmp_path, sample_pdf, monkeypatch):
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    move(planner, planner.get_batch(bid)["items"][0], "aguardando_validacao")
    original = planner._current_evidence
    def concurrent_change(item, action_date):
        result = original(item, action_date)
        assessment.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=60), 1)
        return result
    monkeypatch.setattr(planner, "_current_evidence", concurrent_change)
    with pytest.raises(ValueError, match="[Ee]vid|[Ii]ndicador"):
        move(planner, planner.get_batch(bid)["items"][0], "aprovado_usuario", confirmed=True)
    assert planner.get_batch(bid)["items"][0]["status"] == "aguardando_validacao"


@pytest.mark.parametrize("q_only", [False, True])
def test_newer_evidence_in_another_pair_blocks_old_approval(tmp_path, sample_pdf, monkeypatch, q_only):
    from datetime import date
    from osler.service import import_bytes
    from osler.matching_service import load_matching
    import osler.planner_service
    monkeypatch.setattr(osler.planner_service, "today_local", lambda: date(2026, 10, 15))
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    move(planner, planner.get_batch(bid)["items"][0], "aguardando_validacao")
    q = import_bytes(repo, sample_pdf(date="15/10/2026"), "q-new.pdf").report
    raw_f = sample_pdf(kind="flashcards", date="15/10/2026")
    if q_only:
        import pymupdf
        with pymupdf.open(stream=raw_f, filetype="pdf") as doc:
            page = doc[2]
            page.add_redact_annot(page.search_for("de Feridas")[0])
            page.apply_redactions()
            page.insert_text((69, 177), "das Feridas", fontsize=9)
            raw_f = doc.tobytes()
    f = import_bytes(repo, raw_f, "f-new.pdf").report
    newer = load_matching(repo, q.file_sha256, f.file_sha256)
    topic = next(r for r in newer.rows if r.qbank and "Feridas" in r.qbank.name)
    assessment.save_observation(newer, topic.row_id, known(data_observacao="2026-10-15", acerto_primeira_tentativa=60, erros_criticos=True), 0)
    item = planner.get_batch(bid)["items"][0]
    with pytest.raises(ValueError, match="[Ee]vid|[Ii]ndicador"):
        planner.transition(item["id"], "aprovado_usuario", "Conferência", item["revision"], "2026-10-15", confirmed=True)
    assert planner.get_batch(bid)["items"][0]["status"] == "aguardando_validacao"


def test_parent_and_child_cannot_be_in_active_batches_across_reports(tmp_path, sample_pdf):
    import pymupdf
    from osler.service import import_bytes
    from osler.matching_service import load_matching
    repo, assessment, matching, row, planner, bid = setup_plan(tmp_path, sample_pdf)
    def subdivided(kind):
        doc = pymupdf.open(stream=sample_pdf(kind=kind, date="15/10/2026"), filetype="pdf")
        page = doc[-1]
        page.insert_text((79.5, 188), "Tratamento local", fontsize=8)
        for x, value in zip([330, 402, 472, 530], ["99", "44", "44%", "95%"] if kind == "qbank" else ["146", "146", "100%", "95%"]):
            page.insert_text((x, 188), value, fontsize=8)
        data = doc.tobytes()
        doc.close()
        return data
    q = import_bytes(repo, subdivided("qbank"), "q-child.pdf").report
    f = import_bytes(repo, subdivided("flashcards"), "f-child.pdf").report
    newer = load_matching(repo, q.file_sha256, f.file_sha256)
    child = next(r for r in newer.rows if r.flashcards and r.flashcards.name == "Tratamento local")
    assessment.save_observation(newer, child.row_id, known(data_observacao="2026-10-15"), 0)
    with pytest.raises(ValueError, match="ativo|sobrepo"):
        planner.create_batch(newer, [child.row_id], "Subtema sobreposto", "Não duplicar cartões", "2026-10-15")
    assert len(planner.list_batches()) == 1
