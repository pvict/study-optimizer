from ui_actions import confirm_action
from conftest import open_view
"""Contratos de tarefa do redesign: filtros e registro, sem dados reais."""
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService


def start(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    return repo,AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()


def test_clear_filters_restores_topics_without_recording_study(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    open_view(app,adaptive='Temas e estatísticas')
    original=len(app.dataframe[0].value)
    app.text_input(key='statistics_search').set_value('não existe este tema').run()
    assert len(app.dataframe[0].value)==0
    app.button(key='statistics_clear').click().run()
    assert not app.exception
    assert app.text_input(key='statistics_search').value==''
    assert app.selectbox(key='statistics_focus').value=='Todos os temas'
    assert len(app.dataframe[0].value)==original
    assert not AdaptiveService(repo).store.active('2026-10-15')


def test_invalid_contextual_result_keeps_values_and_does_not_save(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    selected=app.session_state['adaptive_topic']
    count=app.number_input(key='study_n').value
    assert app.number_input(key='study_confident').value is None
    app.number_input(key='study_correct').set_value(count+1)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception and app.error
    assert app.session_state['adaptive_topic']==selected
    assert app.number_input(key='study_n').value==count
    assert app.number_input(key='study_correct').value==count+1
    assert not AdaptiveService(repo).store.active('2026-10-15')


def test_success_offers_return_and_does_not_resubmit_on_rerun(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    app.number_input(key='study_n').set_value(10)
    app.number_input(key='study_correct').set_value(8)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception
    assert any(b.label=='Voltar ao plano' for b in app.button)
    assert not any(b.label=='Salvar resultado e atualizar meu plano' for b in app.button)
    app.run()
    assert len(AdaptiveService(repo).store.active('2026-10-15'))==1
    app.button(key='study_back_to_plan').click().run()
    assert app.session_state['adaptive_view']=='Meu dia'
