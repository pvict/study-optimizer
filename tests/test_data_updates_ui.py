from streamlit.testing.v1 import AppTest
from ui_actions import confirm_action
from test_planner_import import configured, table, html_row
from test_error_cards import node


APP='''
import streamlit as st
from osler.data_updates_ui import render_updates
from osler.action_feedback import bind_actions
repo=st.session_state.repo
bind_actions(repo)
render_updates(repo)
'''


def test_planner_preview_requires_confirmation_and_persists_no_attempts(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf)
    app=AppTest.from_string(APP,default_timeout=60)
    app.session_state['repo']=service.repo
    app.run()
    app.text_area(key='updates_planner_paste').set_value(table(html_row(paths[0])).decode()).run()
    app.button(key='updates_planner_preview').click().run()
    assert not app.exception and service.guide.datasets()==[]
    assert any('Questões antes' in d.value for d in app.dataframe)
    app.button(key='updates_planner_apply').click().run()
    assert service.guide.datasets()==[]
    confirm_action(app)
    assert not app.exception and len(service.guide.datasets())==1
    with service.repo._connection() as db:assert db.execute('select count(*) from study_events').fetchone()[0]==0


def test_changed_input_invalidates_the_old_preview(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf)
    app=AppTest.from_string(APP,default_timeout=60)
    app.session_state['repo']=service.repo;app.run()
    app.text_area(key='updates_planner_paste').set_value(table(html_row(paths[0])).decode()).run()
    app.button(key='updates_planner_preview').click().run()
    app.text_area(key='updates_planner_paste').set_value(table(html_row(paths[0],n=40)).decode()).run()
    assert not any(b.key=='updates_planner_apply' for b in app.button)
    assert service.guide.datasets()==[]


def test_cards_can_be_updated_from_the_same_screen_without_question_data(tmp_path,sample_pdf):
    from osler.error_cards_service import ErrorCardsService
    service,_=configured(tmp_path,sample_pdf)
    app=AppTest.from_string(APP,default_timeout=60)
    app.session_state['repo']=service.repo;app.run()
    app.session_state['updates_tab']='Flashcards de erros';app.run()
    html='<div>'+node('Área',20,branch='down')+node('A',20,20)+'</div>'
    app.text_area(key='updates_cards_paste').set_value(html)
    app.radio(key='updates_cards_scope').set_value('pending').run()
    app.button(key='updates_cards_preview').click().run()
    assert not app.exception
    confirm_action(app.button(key='updates_cards_apply').click().run())
    assert not app.exception and ErrorCardsService(service.repo).latest_snapshot()['tree']['total']==20


def test_tab_switch_preserves_capture_date_and_pasted_html(tmp_path,sample_pdf):
    from datetime import date
    service,paths=configured(tmp_path,sample_pdf)
    app=AppTest.from_string(APP,default_timeout=60)
    app.session_state['repo']=service.repo;app.run()
    html=table(html_row(paths[0])).decode()
    app.text_area(key='updates_planner_paste').set_value(html)
    app.date_input(key='updates_planner_day').set_value(date(2026,10,14)).run()
    app.button(key='updates_planner_preview').click().run()
    app.session_state['updates_tab']='Flashcards de erros';app.run()
    app.session_state['updates_tab']='Planner de questões';app.run()
    assert not app.exception and app.text_area(key='updates_planner_paste').value==html
    assert app.date_input(key='updates_planner_day').value==date(2026,10,14)
    assert app.button(key='updates_planner_apply')


def test_clearing_capture_date_does_not_crash_or_offer_apply(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf)
    app=AppTest.from_string(APP,default_timeout=60)
    app.session_state['repo']=service.repo;app.run()
    app.text_area(key='updates_planner_paste').set_value(table(html_row(paths[0])).decode())
    app.date_input(key='updates_planner_day').set_value(None).run()
    assert not app.exception and app.button(key='updates_planner_preview').disabled
