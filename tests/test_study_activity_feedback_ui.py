from ui_actions import confirm_action
from conftest import open_view
from streamlit.testing.v1 import AppTest

from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from test_assessments import setup_assessment


def start(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    return repo,AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()


def test_save_shows_feedback_then_today_lists_result_and_allows_correction(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    app.number_input(key='study_n').set_value(30)
    app.number_input(key='study_correct').set_value(24)
    app.number_input(key='study_confident').set_value(20)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception
    assert next(m for m in app.metric if m.label=='Acertos no bloco').value=='80,0%'
    assert next(m for m in app.metric if m.label=='Acertos com convicção').value=='66,7%'
    assert any('22/10/2026' in i.value for i in app.info)
    assert any('Próximo bloco de referência' in m.value for m in app.markdown)
    app.button(key='study_back_to_plan').click().run()
    assert not app.exception
    assert any(t.label=='Feito hoje (30)' for t in app.tabs)
    event=AdaptiveService(repo).store.active('2026-10-15')[0]
    app.session_state['today_blocks_tab']='Feito hoje (30)';app.run()
    app.button(key='activity_edit_'+event['session_id']).click().run()
    assert app.session_state['adaptive_view']=='Registrar resultados'
    assert app.number_input(key='study_n').value==30
    app.number_input(key='study_n').set_value(25)
    app.number_input(key='study_correct').set_value(20)
    app.number_input(key='study_confident').set_value(18)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    app.button(key='study_back_to_plan').click().run()
    assert not app.exception
    assert any(t.label=='Feito hoje (25)' for t in app.tabs)
    assert len(AdaptiveService(repo).store.active('2026-10-15'))==1


def test_today_shows_empty_state_and_feedback_keeps_missing_conviction_unknown(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    app.session_state['today_blocks_tab']='Feito hoje (0)';app.run()
    assert any('Nenhum bloco registrado hoje' in i.value for i in app.info)
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    app.number_input(key='study_n').set_value(20)
    app.number_input(key='study_correct').set_value(18)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception
    assert next(m for m in app.metric if m.label=='Acertos com convicção').value=='Não informada'
    assert any('Convicção não informada' in i.value for i in app.info)
    app.run()
    assert len(AdaptiveService(repo).store.active('2026-10-15'))==1
