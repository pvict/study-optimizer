from ui_actions import confirm_action
from streamlit.testing.v1 import AppTest
from test_daily_swaps import service_fixture


def app_for(service):
    app=AppTest.from_string('''
import streamlit as st
from osler.study_day_ui import render_study_day
render_study_day(st.session_state.service,lambda *args:None,lambda *args:None)
''',default_timeout=60)
    app.session_state['service']=service
    return app.run()


def test_suggested_swap_and_undo_are_available_on_the_day(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    app=app_for(service)
    next(b for b in app.button if b.label=='Trocar tema').click().run()
    assert not app.exception
    assert any('16/10/2026' in i.value for i in app.info)
    confirm_action(next(b for b in app.button if b.label=='Usar esta sugestão').click().run())
    assert not app.exception
    assert service.overview('2026-10-15')['plan']['items'][0]['topic_id']=='B'
    assert any('reservado para 16/10/2026' in c.value for c in app.caption)
    confirm_action(next(b for b in app.button if b.label=='Desfazer troca').click().run())
    assert not app.exception
    assert service.overview('2026-10-15')['plan']['items'][0]['topic_id']=='A'
    assert not service.store.active('2026-10-15')


def test_manual_search_can_select_review_instead_of_new_topic(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    app=app_for(service)
    next(b for b in app.button if b.label=='Trocar tema').click().run()
    search=next(t for t in app.text_input if t.label=='Digite o tema ou navegue pelas áreas')
    search.set_value('Review').run()
    assert not app.exception
    confirm_action(next(b for b in app.button if b.label=='Trocar por este tema').click().run())
    assert not app.exception
    view=service.overview('2026-10-15')
    assert view['plan']['items'][0]['topic_id']=='Review'
    assert view['plan']['target_questions']==20
