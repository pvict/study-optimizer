from ui_actions import confirm_action
from conftest import open_view
from streamlit.testing.v1 import AppTest

from osler.guide_service import GuideService
from test_assessments import setup_assessment


def open_legacy(app,view):
    open_view(app,main='Ferramentas')
    app.selectbox(key='advanced_view').set_value(view).run()


def test_today_is_simple_and_works_without_manual_metrics(tmp_path, monkeypatch, project_root, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(project_root/"app.py"), default_timeout=30).run()
    open_legacy(app,'Roteiro simples')
    assert not app.exception
    assert app.session_state['main_view'] == "Ferramentas"
    assert len(app.tabs) == 0
    assert len(app.number_input) == 0
    assert len(app.text_input) == 0
    assert not any("peso" in s.label.lower() for s in app.selectbox)
    assert any(b.label == "Terminei por hoje" for b in app.button)
    confirm_action(next(b for b in app.button if b.label == "Terminei por hoje").click().run())
    assert not app.exception
    assert GuideService(repo).days()[0]["status"] == "feito"
    assert "questoes_feitas" not in GuideService(repo).days()[0]


def test_personal_plan_only_needs_global_choices(tmp_path, monkeypatch, project_root, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(project_root/"app.py"), default_timeout=30).run()
    open_legacy(app,'Preferências do roteiro')
    assert not app.exception
    app.text_area(key="guide_institutions").set_value("Instituição A\nInstituição B")
    confirm_action(next(b for b in app.button if b.label == "Salvar meu plano").click().run())
    assert not app.exception
    assert GuideService(repo).settings()["settings"]["institutions"] == ["Instituição A", "Instituição B"]


def test_rest_day_does_not_require_a_compensation_plan(tmp_path, monkeypatch, project_root, sample_pdf):
    setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(project_root/"app.py"), default_timeout=30).run()
    open_legacy(app,'Roteiro simples')
    app.radio(key="guide_kind").set_value("descanso").run()
    assert not app.exception
    assert any("descanso" in i.value.lower() for i in app.info)
    assert not any(b.label == "Terminei por hoje" for b in app.button)


def test_path_shortcut_opens_reduction_without_changing_an_instantiated_widget(tmp_path, monkeypatch, project_root, sample_pdf):
    setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(project_root/"app.py"), default_timeout=30).run()
    open_legacy(app,'Meu caminho')
    next(b for b in app.button if b.label == "Ver meus temas para redução").click().run()
    assert not app.exception
    assert app.session_state['main_view'] == "Ferramentas"
    assert app.selectbox(key="advanced_view").value == "Planejador de Suspensões"


def test_unidentified_table_is_not_silently_used_for_named_targets(tmp_path, monkeypatch, project_root, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    guide = GuideService(repo)
    guide.import_incidence("Tema;Questões\nOutro;10", "questoes", ["Instituições selecionadas na Osler"], "2026-10-15")
    monkeypatch.setenv("OSLER_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(project_root/"app.py"), default_timeout=30).run()
    open_legacy(app,'Preferências do roteiro')
    app.text_area(key="guide_institutions").set_value("USP\nUnicamp")
    confirm_action(next(b for b in app.button if b.label == "Salvar meu plano").click().run())
    assert not app.exception
    assert any("não está sendo usada" in w.value for w in app.warning)
    assert not any("já está carregada" in s.value for s in app.success)
