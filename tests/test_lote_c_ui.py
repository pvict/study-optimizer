from ui_actions import confirm_action
from conftest import open_view
from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from test_assessments import setup_assessment


def test_new_topic_sections_keep_navigation_and_show_capacity_and_uncertainty(tmp_path,sample_pdf,project_root,monkeypatch):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(repo.root))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Temas e estatísticas')
    assert not app.exception
    assert {'Plano de corte','Minha meta'}<={tab.label for tab in app.tabs}
    assert any('Demanda condicional' in e.value for e in app.markdown)
    assert any('Não é uma previsão de aprovação.' in e.value for e in app.info)
    open_view(app,adaptive='Ajustes')
    assert not app.exception
    assert app.selectbox(key='parameter_version').value==1
    assert not AdaptiveService(repo).store.events()


def test_weekly_form_saves_once_and_keeps_daily_profile_unchanged(tmp_path,monkeypatch):
    monkeypatch.setenv('WEEKLY_TEST_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.weekly_review_ui import render_weekly_review
render_weekly_review(AdaptiveService(Repository(os.environ['WEEKLY_TEST_ROOT'])))
''').run()
    app.text_input(key='weekly_blocked_2026-10-12').set_value('Plantão')
    confirm_action(next(b for b in app.button if b.label=='Salvar revisão da semana').click().run())
    from osler.weekly_review import WeeklyReviewStore
    assert not app.exception
    assert len(WeeklyReviewStore(Repository(tmp_path)).events())==1
    app.run()
    assert len(WeeklyReviewStore(Repository(tmp_path)).events())==1
    assert AdaptiveService(Repository(tmp_path)).store.profile()['id']==0


def test_registration_remembers_last_saved_modality_after_new_session(tmp_path,sample_pdf,project_root,monkeypatch):
    from osler.study_models import StudyEntry
    repo,*_,topic=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.save_entry(StudyEntry(topic.qbank.path,'2026-10-14',20,correct=20,confident_correct=20,mode='repetidas'),'last')
    monkeypatch.setenv('OSLER_DATA_DIR',str(repo.root))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Registrar resultados')
    assert not app.exception
    assert app.selectbox(key='study_mode').value=='repetidas'
