from pathlib import Path
from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from test_day_goal import configured,DAY
from ui_actions import confirm_action


def test_goal_editor_starts_at_effective_limit_and_previews_before_save(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch,area=20)
    catalog=service.catalog(DAY)
    monkeypatch.setattr(AdaptiveService,'catalog',lambda *a,**kw:catalog)
    monkeypatch.setenv('DAY_GOAL_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.day_goal_ui import render_day_goal
import streamlit as st
s=AdaptiveService(Repository(os.environ['DAY_GOAL_ROOT']))
if st.radio('Tela',['Hoje','Outra tela'],key='test_view')=='Hoje':
    render_day_goal(s,s.overview('2026-10-15'),'2026-10-15')
''',default_timeout=30).run()
    assert not app.exception
    assert app.number_input(key='day_questions').value==80
    before=service.agenda.token()
    app.number_input(key='day_questions').set_value(100)
    app.button(key='today_goal_preview').click().run()
    assert not app.exception and service.agenda.token()==before
    assert app.dataframe[0].value['Depois'].tolist()==[100,30,20,50]
    confirm_action(app.button(key='today_goal_apply').click().run())
    assert not app.exception
    assert service.overview(DAY)['plan']['base_questions']==50
    assert app.number_input(key='day_questions').value==100
    app.radio(key='test_view').set_value('Outra tela').run()
    app.radio(key='test_view').set_value('Hoje').run()
    assert app.number_input(key='day_questions').value==100


def test_stale_preview_blocks_apply_instead_of_overwriting_another_screen(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    catalog=service.catalog(DAY)
    monkeypatch.setattr(AdaptiveService,'catalog',lambda *a,**kw:catalog)
    monkeypatch.setenv('DAY_GOAL_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.day_goal_ui import render_day_goal
s=AdaptiveService(Repository(os.environ['DAY_GOAL_ROOT']))
render_day_goal(s,s.overview('2026-10-15'),'2026-10-15')
''',default_timeout=30).run()
    app.number_input(key='day_questions').set_value(100)
    app.button(key='today_goal_preview').click().run()
    service.configure_day('2026-10-16',60,'normal',0)
    app.run()
    assert app.button(key='today_goal_apply').disabled
    assert any('mudaram' in w.value for w in app.warning)
