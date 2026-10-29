from copy import deepcopy
import pytest
from osler.study_models import AdaptiveProfile
from test_confidence import event


def test_observed_history_keeps_new_confidence_and_volume_denominators_separate():
    from osler.evolution_history_ui import observed_history
    sessions=[event('a','2026-10-26',20,18,15),event('b','2026-10-27',10,8,None),
              event('repeat','2026-10-27',100,0,0)]
    sessions[-1]['entry']['mode']='repetidas'
    sessions += [event('future','2026-10-30',200,200,200)]
    before=deepcopy(sessions)
    model=observed_history(sessions,'2026-10-28',AdaptiveProfile(),{}, {},weeks=4)
    week=model['weeks'][-1]
    assert week['new_n']==30 and week['correct']==26
    assert week['conviction_n']==20 and week['conviction']==75
    assert week['accuracy']==pytest.approx(100*26/30)
    assert week['volume']==130 and model['study_days']==2
    area=model['areas'][0]
    assert area['n']==30 and area['rate']==pytest.approx(100*26/30)
    assert 70<area['lower']<71 and 94<area['upper']<95
    assert sessions==before


def test_empty_accuracy_stays_missing_and_zero_correct_stays_zero():
    from osler.evolution_history_ui import observed_history
    repeated=event('r','2026-10-26',10,10,10);repeated['entry']['mode']='repetidas'
    model=observed_history([repeated],'2026-10-28',AdaptiveProfile(),{}, {},weeks=4)
    assert model['weeks'][-1]['accuracy'] is None
    assert model['weeks'][-1]['conviction'] is None
    assert not model['areas'] and model['volume']==10
    zero=observed_history([event('zero','2026-10-26',10,0,0)],'2026-10-28',AdaptiveProfile(),{}, {},weeks=4)
    assert zero['weeks'][-1]['accuracy']==0 and zero['weeks'][-1]['conviction']==0
    assert zero['areas'][0]['lower']==0 and zero['areas'][0]['upper']>0


def test_weekly_reference_respects_start_rest_mock_and_elapsed_days_only():
    from osler.evolution_history_ui import observed_history
    p=AdaptiveProfile(max_questions=20,start_date='2026-10-26')
    settings={'2026-10-27':{'questions':60,'kind':'normal','extra_topics':[]},
              '2026-10-30':{'questions':1000,'kind':'normal','extra_topics':[]}}
    model=observed_history([],'2026-10-28',p,settings,{'2026-10-28':{'mode':'mock_reserved'}},weeks=4)
    assert model['weeks'][-1]['target']==80
    assert all(w['target'] is None for w in model['weeks'][:-1])
    assert model['study_days']==0 and model['new_n']==0


def test_history_renders_without_running_forecast_or_writing_study(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from test_daily_swaps import service_fixture
    s,_=service_fixture(tmp_path,monkeypatch);before=s.agenda.token()
    def no_forecast(*args,**kwargs):raise AssertionError('Histórico não precisa simular o futuro.')
    monkeypatch.setattr(s,'evolution_context',no_forecast)
    app=AppTest.from_string('''
import streamlit as st
from osler.study_evolution_ui import render_evolution
render_evolution(st.session_state.service)
''',default_timeout=60)
    app.session_state['service']=s;app.run()
    assert not app.exception
    assert any('Registrar' in i.value or 'Registre' in i.value for i in app.info)
    assert s.agenda.token()==before and not s.store.active('2026-10-15')
