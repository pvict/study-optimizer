from ui_actions import confirm_action
from datetime import date, datetime

import pytest
from streamlit.testing.v1 import AppTest

import osler.planner_service as clock
from osler.study_models import StudyEntry
from test_daily_swaps import service_fixture


def freeze_time(monkeypatch, instant):
    moment=datetime.fromisoformat(instant)
    class FrozenClock(datetime):
        @classmethod
        def now(cls,tz=None):
            return moment.astimezone(tz) if tz else moment
    monkeypatch.setattr(clock,'datetime',FrozenClock)


@pytest.mark.parametrize('instant,expected',[
    ('2026-10-22T23:59:59-03:00','2026-10-22'),
    ('2026-10-23T00:00:00-03:00','2026-10-22'),
    ('2026-10-23T03:59:59.999999-03:00','2026-10-22'),
    ('2026-10-23T04:00:00-03:00','2026-10-23'),
    ('2026-11-01T02:00:00-03:00','2026-10-31'),
    ('2027-01-01T02:00:00-03:00','2026-12-31'),
    ('2026-10-23T06:59:59+00:00','2026-10-22'),
    ('2026-10-23T07:00:00+00:00','2026-10-23'),
])
def test_study_day_changes_at_four_in_brasilia(monkeypatch,instant,expected):
    freeze_time(monkeypatch,instant)
    assert clock.today_local().isoformat()==expected


def test_after_midnight_registration_and_plan_still_belong_to_previous_day(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    service.save_entry(StudyEntry(topics[0]['path'],'2026-10-15',5,4),'evening')
    freeze_time(monkeypatch,'2026-10-16T02:00:00-03:00')
    app=AppTest.from_string('''
import streamlit as st
from osler.study_day_ui import render_study_day
from osler.adaptive_ui import _register
render_study_day(st.session_state.service,lambda *args:None,lambda *args:None)
_register(st.session_state.service)
''',default_timeout=60)
    app.session_state['service']=service
    app.run()
    assert not app.exception
    assert app.date_input(key='study_date').value==date(2026,10,15)
    assert service.overview(clock.today_local().isoformat())['plan']['done_questions']==5
    app.number_input(key='study_n').set_value(5)
    app.number_input(key='study_correct').set_value(4)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception
    assert service.overview('2026-10-15')['plan']['done_questions']==10
    freeze_time(monkeypatch,'2026-10-16T04:00:00-03:00')
    assert service.overview(clock.today_local().isoformat())['plan']['done_questions']==0
    assert {s['entry']['day'] for s in service.store.active('2026-10-16')}=={'2026-10-15'}


def test_today_swap_is_valid_after_midnight_until_four(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    freeze_time(monkeypatch,'2026-10-16T03:59:00-03:00')
    options=service.swap_options('2026-10-15','A')
    slot=service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    assert service.overview('2026-10-15')['plan']['items'][0]['topic_id']=='B'
    assert any(r['date']=='2026-10-16' for r in service.overview('2026-10-15')['agenda']['rows'])
    freeze_time(monkeypatch,'2026-10-16T04:00:00-03:00')
    with pytest.raises(ValueError):
        service.undo_swap('2026-10-15',slot,service.agenda.token())
