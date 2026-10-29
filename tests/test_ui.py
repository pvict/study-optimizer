from ui_actions import confirm_action
from conftest import open_view
from streamlit.testing.v1 import AppTest
import pytest

from osler.service import import_bytes
from osler.storage import Repository


def advanced(app):
    if app.exception:
        return app
    open_view(app,main='Ferramentas')
    app.selectbox(key="advanced_view").set_value("Dados e classificação").run()
    return app


def test_empty_app_explains_import_step(tmp_path, monkeypatch, project_root):
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run())
    assert not app.exception
    assert any("Importar" in tab.label for tab in app.tabs)
    assert any("relatório" in element.value.lower() for element in app.info)


def test_app_displays_imported_report_and_search_filters(tmp_path, monkeypatch, project_root, sample_pdf):
    repo = Repository(tmp_path)
    import_bytes(repo, sample_pdf(), "sample.pdf")
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run())
    assert not app.exception
    app.text_input(key="topic_search").set_value("Feridas").run()
    assert not app.exception
    table = app.tabs[2].dataframe[0].value
    assert len(table) == 1
    assert table.iloc[0]["Respondidas"] == 44
    assert "Cicatrização" in table.iloc[0]["Hierarquia"]


def test_app_explains_absent_attempts(tmp_path, monkeypatch, project_root, sample_pdf):
    import_bytes(Repository(tmp_path), sample_pdf(), "sample.pdf")
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run())
    assert not app.exception
    assert any("tentativa" in e.value.lower() for e in app.info)


def test_crossing_requires_both_report_types(tmp_path, monkeypatch, project_root, sample_pdf):
    import_bytes(Repository(tmp_path), sample_pdf(), "q.pdf")
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run())
    assert not app.exception
    assert any(t.label == "Cruzamento" for t in app.tabs)
    assert any("Qbank e de Flashcards" in i.value for i in app.info)


def test_crossing_table_preserves_both_sources(tmp_path, monkeypatch, project_root, sample_pdf):
    repo = Repository(tmp_path)
    import_bytes(repo, sample_pdf(), "q.pdf")
    import_bytes(repo, sample_pdf(kind="flashcards"), "f.pdf")
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run())
    assert not app.exception
    app.text_input(key="cross_search").set_value("Feridas").run()
    assert not app.exception
    frame = app.tabs[4].dataframe[0].value
    assert len(frame) == 1
    assert frame.iloc[0]["Respondidas"] == 44
    assert frame.iloc[0]["Cartões estudados"] == 146
    assert frame.iloc[0]["Associação"] == "exata"


def test_manual_review_can_approve_and_remove(tmp_path, monkeypatch, project_root, sample_pdf):
    from test_matching_storage import stored_pair
    repo, q, f = stored_pair(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run())
    assert not app.exception
    next(s for s in app.selectbox if s.label == "Tema do Qbank").select(2).run()
    next(s for s in app.selectbox if s.label == "Tema dos flashcards").select(2).run()
    next(t for t in app.text_area if t.label == "Justificativa da associação").set_value("Conferi que os dois caminhos representam o mesmo assunto").run()
    confirm_action(next(b for b in app.button if b.label == "Aprovar associação").click().run())
    assert not app.exception
    assert len(repo.active_matches(q.file_sha256, f.file_sha256)) == 1
    confirm_action(next(b for b in app.button if b.label == "Remover associação selecionada").click().run())
    assert not app.exception
    assert not repo.active_matches(q.file_sha256, f.file_sha256)
    assert [e["action"] for e in repo.matching_events()] == ["aprovar", "remover"]


def test_crossing_search_handles_missing_source_without_inventing_values(tmp_path, monkeypatch, project_root, sample_pdf):
    import pandas as pd
    from test_matching_storage import stored_pair
    stored_pair(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=20).run())
    assert not app.exception
    app.text_input(key="cross_search").set_value("das feridas").run()
    assert not app.exception
    frame = app.tabs[4].dataframe[0].value
    assert len(frame) == 1
    assert frame.iloc[0]["Associação"] == "somente_flashcards"
    assert pd.isna(frame.iloc[0]["Respondidas"])
    assert frame.iloc[0]["Cartões estudados"] == 146


def test_classification_tab_requires_sources(tmp_path, monkeypatch, project_root):
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=30).run())
    assert not app.exception
    assert any(t.label == "Classificação" for t in app.tabs)


def test_classification_ui_saves_manual_first_attempt_without_overwriting_pdf(tmp_path, monkeypatch, project_root, sample_pdf):
    from test_assessments import setup_assessment
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=30).run())
    assert not app.exception
    app.selectbox(key="assessment_row").select(row.row_id).run()
    next(t for t in app.text_input if t.label == "Questões distintas").set_value("44")
    next(t for t in app.text_input if t.label == "Acerto na primeira tentativa (%)").set_value("82")
    next(t for t in app.text_input if t.label == "Acerto na última tentativa (%)").set_value("95")
    next(t for t in app.text_input if t.label == "Origem dos indicadores").set_value("Conferido manualmente pelo usuário")
    confirm_action(next(b for b in app.button if b.label == "Salvar nova observação").click().run())
    assert not app.exception
    history = service.store.history(row.row_id)
    assert len(history) == 1
    assert history[0]["observation"]["acerto_primeira_tentativa"] == 82
    assert repo.get_report(matching.qbank_report_id).records[2].acerto_pdf.value == 95
    table = app.tabs[5].dataframe[0].value
    assert "B" in table["Categoria"].tolist()


def test_planner_ui_creates_only_suggested_batch(tmp_path, monkeypatch, project_root, sample_pdf):
    from test_assessments import setup_assessment
    from test_classification import known
    from osler.planner_service import PlannerService
    repo, service, matching, row = setup_assessment(tmp_path, sample_pdf)
    service.save_observation(matching, row.row_id, known(), 0)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=30).run())
    app.selectbox(key="advanced_view").set_value("Planejador de Suspensões").run()
    assert not app.exception
    app.text_input(key="planner_search").set_value("feridas").run()
    assert not app.exception
    app.multiselect(key="planner_selection").select(row.row_id).run()
    next(t for t in app.text_input if t.label == "Nome do lote").set_value("Avaliar feridas")
    next(t for t in app.text_area if t.label == "Finalidade do lote").set_value("Conferência manual dos conceitos frágeis")
    confirm_action(next(b for b in app.button if b.label == "Criar lote sugerido").click().run())
    assert not app.exception
    planner = PlannerService(repo)
    batches = planner.list_batches()
    assert len(batches) == 1
    assert planner.get_batch(batches[0]["id"])["items"][0]["status"] == "sugerido"
    assert planner.get_batch(batches[0]["id"])["items"][0]["applied_date"] is None


def test_advanced_dashboard_keeps_missing_agenda_explicit(tmp_path, monkeypatch, project_root, sample_pdf):
    from test_assessments import setup_assessment
    setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=30).run())
    assert not app.exception
    app.selectbox(key="advanced_view").set_value("Painel").run()
    assert any("agenda" in e.value.lower() for e in app.info)


def test_planning_ui_shows_capacity_and_no_carry_over(tmp_path, monkeypatch, project_root, sample_pdf):
    from test_assessments import setup_assessment
    from osler.planning import Measurement
    from osler.planning_service import PlanningService
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    PlanningService(repo).save_measurement(Measurement("revisoes_periodo", 31149, "2026-10-14", "Referência fornecida", 90))
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=30).run())
    app.selectbox(key="advanced_view").set_value("Simulação e rotina").run()
    assert not app.exception
    assert any(m.label == "Capacidade pelo teto" and m.value == "13.500" for m in app.metric)
    assert any("dívida" in e.value for e in app.info)
    assert any(b.label == "Baixar rotina CSV" for b in app.get("download_button"))


def test_evolution_ui_does_not_invent_second_date(tmp_path, monkeypatch, project_root, sample_pdf):
    from test_assessments import setup_assessment
    setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=30).run())
    app.selectbox(key="advanced_view").set_value("Evolução").run()
    assert not app.exception
    assert any("duas datas" in e.value.lower() for e in app.info)


def test_backups_ui_does_not_restore_without_selected_file(tmp_path, monkeypatch, project_root):
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = advanced(AppTest.from_file(str(project_root / "app.py"), default_timeout=30).run())
    app.selectbox(key="advanced_view").set_value("Backup e restauração").run()
    assert not app.exception
    assert next(b for b in app.button if b.label == "Restaurar em nova pasta e abrir").disabled


@pytest.mark.parametrize('has_original',[False,True])
def test_bad_active_database_offers_recovery_only_when_available(tmp_path, monkeypatch, project_root,has_original):
    import sqlite3
    import osler.ui
    # O projeto de teste é isolado: não depender do banco pessoal do checkout.
    isolated_project=tmp_path/'project'
    monkeypatch.setattr(osler.ui,'__file__',str(isolated_project/'osler'/'ui.py'))
    if has_original: Repository(isolated_project/'data')
    with sqlite3.connect(tmp_path/"osler.sqlite3") as db:
        db.execute("CREATE TABLE reports(file_sha256 TEXT)")
        db.execute("PRAGMA user_version=5")
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(project_root/"app.py"), default_timeout=30).run()
    assert not app.exception
    assert any("abrir" in e.value.lower() for e in app.error)
    assert any(b.label == "Abrir pasta original preservada" for b in app.button)==has_original
