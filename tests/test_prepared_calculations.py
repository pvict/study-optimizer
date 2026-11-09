"""Reutilização de cálculo puro não pode mudar dados ou contornar validação."""
from dataclasses import replace
import pytest


def test_repeated_path_normalizes_unicode_once_but_returns_independent_lists(monkeypatch):
    from osler import models
    original=models.unicodedata.normalize
    calls=[]
    part='  Cárdio auditoria 20261101  —  AÇÃO '
    def normalize(form,text):
        if text==part:calls.append(text)
        return original(form,text)
    monkeypatch.setattr(models.unicodedata,'normalize',normalize)
    first=models.normalize_path([part])
    first.append('alteração local')
    assert models.normalize_path([part])==['cardio auditoria 20261101 — acao']
    assert calls==[part]


def test_equal_parameter_values_are_validated_once_without_stale_mutable_input(monkeypatch):
    from osler.algorithm_parameters import AlgorithmParameters
    from osler.study_models import AdaptiveProfile
    original=AlgorithmParameters.validate
    calls=[]
    def validate(self):
        if self.version==99101:calls.append(self.first_interval)
        return original(self)
    monkeypatch.setattr(AlgorithmParameters,'validate',validate)
    values={'version':99101,'first_interval':9}
    profile=AdaptiveProfile(parameter_values=values)
    assert profile.parameters.first_interval==9
    assert replace(profile,target_accuracy=95).parameters.first_interval==9
    assert calls==[9]
    values['first_interval']=12
    assert profile.parameters.first_interval==12
    assert calls==[9,12]
    values['first_interval']=True
    with pytest.raises(ValueError):profile.parameters


def test_parameter_cache_never_confuses_boolean_with_valid_integer():
    from osler.study_models import AdaptiveProfile
    good=AdaptiveProfile(parameter_values={'version':99102,'first_interval':1})
    assert good.parameters.first_interval==1
    with pytest.raises(ValueError):
        AdaptiveProfile(parameter_values={'version':99102,'first_interval':True}).parameters


def test_projection_uses_valid_spaced_anchor_instead_of_last_early_contact():
    from osler.evolution_spacing import advance_projected_spacing
    from osler.study_models import AdaptiveProfile
    state={'spacing':{'streak':1,'base_interval':7,'ease':2.5,
                      'last_evidence_day':'2026-10-07','last_spaced_evidence_day':'2026-10-01'},
           'review_interval_days':7}
    advance_projected_spacing(state,AdaptiveProfile(review_strategy='balanced_v2'),'2026-10-08',20)
    assert state['review_interval_days']==14
    assert state['projected_spacing']['streak']==2


def test_topic_filter_counts_use_same_individual_base_as_the_table(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from test_daily_swaps import service_fixture
    service,_=service_fixture(tmp_path,monkeypatch)
    original=service.overview
    def overview(*args,**kwargs):
        view=original(*args,**kwargs)
        view['planning_states']=view['planning_states'][:1]
        return view
    monkeypatch.setattr(service,'overview',overview)
    app=AppTest.from_string('''
import streamlit as st
from osler.study_tables_ui import render_topic_table
render_topic_table(st.session_state.service,lambda *args:None)
''',default_timeout=60)
    app.session_state['service']=service
    app.run()
    assert not app.exception
    assert app.button(key='focus_unseen').label=='Não vistos · 4'
    frame=next(d.value for d in app.dataframe if 'Estado' in d.value)
    assert len(frame)==5
    app.button(key='focus_unseen').click().run()
    frame=next(d.value for d in app.dataframe if 'Estado' in d.value)
    assert len(frame)==4


def test_capacity_sorts_only_admissible_candidates_but_counts_future_committed_load(monkeypatch):
    from osler import study_capacity
    from osler.adaptive_planning import topic_states
    from osler.study_models import AdaptiveProfile
    from test_initial_review_policy import imported
    profile=AdaptiveProfile(workload_mode='adaptive',minimum_new_share=0,max_questions=40)
    states=topic_states([imported('future'),imported('active',n=0,contact=None),imported('outside',n=0,contact=None)],[],[],{},'2026-10-15',profile)
    old=next(t for t in states if t['topic_id']=='future')
    old.update(review_committed=True,next_review='2026-10-22',theme_review_due='2026-10-22',theme_recommended_questions=40)
    original=study_capacity.review_order;ordered=[]
    def order(t,day):
        ordered.append(t['topic_id'])
        return original(t,day)
    monkeypatch.setattr(study_capacity,'review_order',order)
    kept,_,meta=study_capacity.capacity_policy(states,profile,'2026-10-15',40,40,eligible_ids={'active'})
    assert ordered==['active']
    assert 'future' in {t['topic_id'] for t in kept}
    assert 'outside' not in {t['topic_id'] for t in kept}
    assert 'active' not in {t['topic_id'] for t in kept}


def test_calendar_and_backlog_reuse_current_view_but_reject_a_stale_one(tmp_path,monkeypatch):
    from copy import deepcopy
    from test_daily_swaps import service_fixture
    service,_=service_fixture(tmp_path,monkeypatch)
    view=service.overview('2026-10-15');before=deepcopy(view)
    def unexpected(*args,**kwargs):
        raise AssertionError('O snapshot atual não deve ser calculado novamente.')
    monkeypatch.setattr(service,'overview',unexpected)
    days=service.calendar(2,view=view)
    assert days[0]['date']=='2026-10-15' and days[0]['questions']==20
    context=service.replanning(view=view)
    assert context['view']==view and view==before
    service.configure_day('2026-10-15',40,'normal',view['day']['revision'])
    with pytest.raises(ValueError,match='Atualize'):service.calendar(2,view=view)
    with pytest.raises(ValueError,match='Atualize'):service.replanning(view=view)
