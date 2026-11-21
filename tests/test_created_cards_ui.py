from ui_actions import confirm_action
from streamlit.testing.v1 import AppTest

from osler.adaptive_service import AdaptiveService
from osler.error_cards_service import ErrorCardsService
from test_assessments import setup_assessment


def test_question_form_adds_cards_and_edit_replaces_count_without_extra_session(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    cards=ErrorCardsService(repo);cards.configure(0,{},cards.token())
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    app.number_input(key='study_n').set_value(10)
    app.number_input(key='study_correct').set_value(8)
    app.number_input(key='study_cards_created').set_value(3)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception
    assert any('3 flashcards criados' in i.value for i in app.success)
    view=cards.overview('2026-10-15',question_view={'plan':{},'states':[]})
    assert view['remaining']==3 and view['budget']==0 and view['done_today']==0
    app.button(key='study_back_to_plan').click().run()
    event=AdaptiveService(repo).store.active('2026-10-15')[0]
    app.session_state['today_blocks_tab']='Feito hoje (10)';app.run()
    app.button(key='activity_edit_'+event['session_id']).click().run()
    assert app.number_input(key='study_cards_created').value==3
    app.number_input(key='study_cards_created').set_value(5)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception
    assert cards.overview('2026-10-15',question_view={'plan':{},'states':[]})['remaining']==5
    assert len(AdaptiveService(repo).store.active('2026-10-15'))==1


def test_cards_ui_works_without_html_and_can_record_a_newly_created_deck(tmp_path,monkeypatch):
    from osler.storage import Repository
    from osler.study_storage import StudyStore
    from osler.study_models import StudyEntry
    from osler.planner_service import today_local
    repo=Repository(tmp_path);store=StudyStore(repo);day=today_local().isoformat()
    store.save_batch([('q',StudyEntry(['Área','Tema'],day,10,8,cards_created=3),0)])
    monkeypatch.setenv('ERROR_CARDS_TEST_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.error_cards_ui import render_error_cards
render_error_cards(Repository(os.environ['ERROR_CARDS_TEST_ROOT']))
''',default_timeout=60).run()
    assert not app.exception
    next(b for b in app.button if b.label=='Registrar cards deste tema').click().run()
    confirm_action(next(b for b in app.button if b.label=='Salvar bloco de cards').click().run())
    assert not app.exception
    view=ErrorCardsService(repo).overview(day,question_view={'states':[],'plan':{}})
    assert view['remaining']==0 and view['done_today']==3


def test_removed_creation_preserves_studied_history_and_closes_stale_form(tmp_path,monkeypatch):
    from osler.storage import Repository
    from osler.study_storage import StudyStore
    from osler.study_models import StudyEntry
    from osler.planner_service import today_local
    from osler.models import stable_topic_id
    repo=Repository(tmp_path);store=StudyStore(repo);day=today_local().isoformat()
    store.save_batch([('q',StudyEntry(['Área','Tema'],day,10,8,cards_created=5),0)])
    cards=ErrorCardsService(repo)
    cards.record(stable_topic_id(['Área','Tema']),day,5,0,None,'done',cards.token())
    monkeypatch.setenv('ERROR_CARDS_TEST_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.error_cards_ui import render_error_cards
render_error_cards(Repository(os.environ['ERROR_CARDS_TEST_ROOT']))
''',default_timeout=60).run()
    app.session_state['ec_tabs']='Temas';app.run()
    app.button(key='ec_manual_'+stable_topic_id(['Área','Tema'])).click().run()
    store.void('q',1)
    app.run()
    assert not app.exception
    assert any('A fila mudou' in w.value for w in app.warning)
    assert any('5 cards já estudados' in w.value for w in app.warning)
    app.session_state['ec_tabs']='Hoje';app.run()
    assert any(b.label=='Desfazer este registro' for b in app.button)
    next(b for b in app.button if b.label=='Fechar registro desatualizado').click().run()
    assert not app.exception
