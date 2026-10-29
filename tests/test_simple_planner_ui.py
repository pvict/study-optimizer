from ui_actions import confirm_action
from conftest import open_view
from streamlit.testing.v1 import AppTest
from test_planner import setup_plan


def test_manual_choice_needs_no_written_justification_or_duplicate_checkbox(tmp_path, sample_pdf, monkeypatch, project_root):
    repo, assessment, matching, row, planner, batch = setup_plan(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(project_root/"app.py"), default_timeout=30).run()
    open_view(app,main="Ferramentas")
    app.selectbox(key="advanced_view").set_value("Planejador de Suspensões").run()
    assert not app.exception
    assert not any("Confirmo" in c.label for c in app.checkbox)
    confirm_action(next(b for b in app.button if b.label == "Quero avaliar este tema").click().run())
    assert not app.exception
    assert planner.get_batch(batch)["items"][0]["status"] == "aguardando_validacao"
    confirm_action(next(b for b in app.button if b.label == "Quero fazer essa redução").click().run())
    assert not app.exception
    assert planner.get_batch(batch)["items"][0]["status"] == "aprovado_usuario"
    assert planner.get_batch(batch)["items"][0]["applied_date"] is None
