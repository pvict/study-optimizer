from copy import deepcopy

from streamlit.testing.v1 import AppTest

from osler.adaptive_planning import topic_states
from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile,StudyEntry
from test_adaptive_planning import topic
from test_confidence import event
from test_daily_swaps import service_fixture


def weak_theme():
    profile=AdaptiveProfile(max_questions=60,max_topics=2,new_share=0,workload_mode='adaptive')
    sessions=[event('initial','2026-10-15',30,20,5)]
    states=topic_states([topic()],sessions,[],{},'2026-10-16',profile)
    return states,sessions,profile


def test_service_calendar_keeps_next_theme_contact_and_known_return_not_a_fixed_chain(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    service.store.save_profile(AdaptiveProfile(max_questions=60,max_topics=2,new_share=.5),1)
    service.save_entry(StudyEntry(topics[0]['path'],'2026-10-15',30,20,confident_correct=5),'initial')
    before=deepcopy(service.store.active('2026-10-15'))
    days=service.calendar(32)
    contacts=[(d['date'],i) for d in days for i in d['items'] if i['topic_id']=='A']
    # Sem incidência no fixture: próximo tema em18/10 e o lote conhecido em22/10.
    assert [d for d,i in contacts]==['2026-10-18','2026-10-22']
    assert contacts[0][1]['forecast_basis']=='next_contact'
    assert contacts[1][1]['forecast_basis']=='known_return'
    assert service.store.active('2026-10-15')==before


def test_forecast_keeps_pending_questions_at_seven_days_and_does_not_infer_recovery():
    states,sessions,p=weak_theme(); before=deepcopy(states)
    days=forecast_calendar(states,p,'2026-10-16',22,sessions,{},next_contact_only=True)
    theme=[d['date'] for d in days for i in d['items'] if i['review_kind']!='lot_only']
    lots=[(d['date'],d['pending_planned']) for d in days if d['pending_planned']]
    assert theme==['2026-10-18']
    assert lots==[('2026-10-22',25)]
    assert days[-1]['awaiting_results']==1
    assert not days[-1]['topic_backlog']
    assert states==before


def test_small_capacity_keeps_unfinished_known_lot_until_it_fits():
    states,sessions,p=weak_theme()
    settings={'2026-10-22':{'questions':10,'kind':'normal','extra_topics':[]}}
    days=forecast_calendar(states,p,'2026-10-16',10,sessions,settings,next_contact_only=True)
    lots=[(d['date'],d['pending_planned']) for d in days if d['pending_planned']]
    assert lots==[('2026-10-22',10),('2026-10-23',15)]
    assert days[6]['pending_backlog']==15
    assert not days[7]['pending_backlog']


def test_return_before_first_theme_contact_does_not_replace_whole_theme():
    states,sessions,p=weak_theme()
    states[0].update(theme_review_due='2026-10-25',next_review='2026-10-22')
    days=forecast_calendar(states,p,'2026-10-22',10,sessions,{},next_contact_only=True)
    assert [(d['date'],i['review_kind']) for d in days for i in d['items']]==[
        ('2026-10-22','lot_only'),('2026-10-25','theme')]


def test_calendar_marks_further_reviews_as_awaiting_results(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    service.save_entry(StudyEntry(topics[0]['path'],'2026-10-15',30,20,confident_correct=5),'initial')
    app=AppTest.from_string('''
import streamlit as st
from osler.study_calendar_ui import render_calendar
render_calendar(st.session_state.service,lambda *args:None)
''',default_timeout=60)
    app.session_state['service']=service
    app.session_state['calendar_selected']='2026-10-18'
    app.run()
    assert not app.exception
    assert any('resultado' in c.value.lower() and 'próxim' in c.value.lower() for c in app.caption)
    assert any('recalculad' in c.value.lower() for c in app.caption)


def test_lot_and_theme_due_together_share_one_block_without_doubled_questions():
    states,sessions,p=weak_theme()
    states[0].update(theme_review_due='2026-10-22',next_review='2026-10-22')
    days=forecast_calendar(states,p,'2026-10-22',6,sessions,{},next_contact_only=True)
    assert len(days[0]['items'])==1
    assert days[0]['items'][0]['review_kind']=='theme'
    assert days[0]['pending_planned']==25
    assert days[0]['questions']==25
    assert not any(d['items'] for d in days[1:])


def test_rest_keeps_due_lot_visible_until_the_next_available_day():
    states,sessions,p=weak_theme()
    settings={'2026-10-22':{'questions':60,'kind':'descanso','extra_topics':[]}}
    days=forecast_calendar(states,p,'2026-10-16',10,sessions,settings,next_contact_only=True)
    assert not days[6]['items'] and days[6]['pending_backlog']==25
    assert days[7]['pending_planned']==25


def test_explicit_future_reservation_and_extra_survive_the_next_contact_limit():
    states,sessions,p=weak_theme()
    agenda={'rows':[{'topic_id':'Tema','path':['Área','Tema'],'date':'2026-10-20',
                     'original_due':'2026-10-18','questions':12,'remaining':12}], 'overrides':{}}
    settings={'2026-10-21':{'questions':60,'kind':'normal','extra_topics':[
        {'topic_id':'Tema','extra_id':'extra','questions':10,'after_event_id':0}]}}
    days=forecast_calendar(states,p,'2026-10-16',10,sessions,settings,agenda=agenda,next_contact_only=True)
    reserved=next(d for d in days if d['date']=='2026-10-20')
    extra=next(d for d in days if d['date']=='2026-10-21')
    assert reserved['items'][0]['rescheduled'] and reserved['items'][0]['questions']==12
    assert extra['items'][0]['added_by_user'] and extra['items'][0]['questions']==10
