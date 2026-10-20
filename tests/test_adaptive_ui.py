from streamlit.testing.v1 import AppTest

from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService
from osler.study_models import AdaptiveProfile


def test_daily_plan_has_integer_questions_and_result_shortcut(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    assert not app.exception
    assert app.radio(key='main_view').value=='Plano de questões'
    assert any('questões' in x.value.lower() for x in app.subheader)
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    assert not app.exception
    assert app.radio(key='adaptive_view').value=='Registrar resultados'
    app.number_input(key='study_n').set_value(10)
    app.number_input(key='study_correct').set_value(7)
    next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run()
    assert not app.exception
    assert len(AdaptiveService(repo).store.active('2026-10-15'))==1


def test_alerts_and_unseen_are_available_without_per_topic_configuration(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    app.radio(key='adaptive_view').set_value('Temas e estatísticas').run()
    assert not app.exception
    assert len(app.dataframe)>=1
    app.selectbox(key='statistics_focus').set_value('Sem estudo registrado').run()
    assert not app.exception


def test_csv_import_and_history_are_optional_not_blocking_the_day(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    assert not app.exception
    assert len(app.text_area)==0
    app.radio(key='adaptive_view').set_value('Registrar resultados').run()
    assert not app.exception
    assert any('Importar' in e.label for e in app.expander)


def test_profile_form_preserves_displayed_revision_on_concurrent_change(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    app.radio(key='adaptive_view').set_value('Ajustes').run()
    store=AdaptiveService(repo).store
    store.save_profile(AdaptiveProfile(target_accuracy=85,max_questions=100),0)
    next(x for x in app.number_input if x.label=='Meta de acerto nos temas (%)').set_value(80.)
    next(b for b in app.button if b.label=='Salvar planejamento').click().run()
    assert not app.exception
    assert any('atualizado' in e.value for e in app.error)
    assert store.profile()['id']==1
    assert store.profile()['profile']['target_accuracy']==85
