from copy import deepcopy
from dataclasses import replace
import pytest
from osler.adaptive_planning import topic_states,allocate_day
from osler.study_models import AdaptiveProfile
from osler.study_calendar import forecast_calendar
from test_initial_review_policy import imported


def profile(**kwargs): return AdaptiveProfile(workload_mode='adaptive',**kwargs)


def test_due_reviews_reduce_new_quota_without_raising_daily_load():
    p=profile(max_questions=60,max_topics=4,new_share=.5)
    states=topic_states([imported(str(i)) for i in range(3)]+[imported('new',n=0,contact=None)],[],[],{},'2026-10-15',p)
    for t in states:
        if t['topic_id']!='new': t.update(review_committed=True,next_review='2026-10-15',theme_review_due='2026-10-15',recommended_questions=20,theme_recommended_questions=20)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=60)
    assert plan['distribution']['planned_new']==0
    assert plan['questions']==60
    assert plan['capacity']['effective_share']==0


def test_admissions_fit_future_review_capacity_and_preserve_inputs():
    p=profile(max_questions=60,max_topics=3,new_share=.4)
    states=topic_states([imported(str(i),n=0,contact=None) for i in range(100)],[],[],{},'2026-10-15',p)
    before=deepcopy(states)
    days=forecast_calendar(states,p,'2026-10-15',30,[],{})
    assert max(d['topic_backlog'] for d in days)==0
    assert all(d['questions']<=60 and len(d['items'])<=3 for d in days)
    assert any(d['capacity']['deferred_admissions'] for d in days)
    assert states==before


def test_maintenance_dose_is_not_inflated_to_fill_quota():
    p=profile(max_questions=120,max_topics=5,new_share=0)
    states=topic_states([imported()],[],[],{},'2026-10-15',p)
    t=states[0]; t.update(review_committed=True,next_review='2026-10-15',recommended_questions=10)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=120)
    assert plan['questions']==10
    assert plan['capacity']['unused_questions']==110
    fixed=allocate_day(states,replace(p,workload_mode='fixed'),None,'normal',[],'2026-10-15',question_target=120)
    assert fixed['questions']>10


def test_mode_validation_and_legacy_profile():
    assert AdaptiveProfile().workload_mode=='fixed'
    with pytest.raises(ValueError): AdaptiveProfile(workload_mode='unknown').validate()


def test_real_overload_and_rest_still_visible():
    p=profile(max_questions=20,max_topics=1,new_share=.4)
    states=topic_states([imported('A'),imported('B')],[],[],{},'2026-10-15',p)
    for t in states: t.update(review_committed=True,next_review='2026-10-15',recommended_questions=20)
    day=forecast_calendar(states,p,'2026-10-15',1,[],{})[0]
    assert day['topic_backlog']==1
    assert allocate_day(states,p,None,'descanso',[],'2026-10-15',question_target=20)['questions']==0


def lot_history():
    from test_confidence import event
    return [event('first','2026-10-01',20,18,10),event('good1','2026-10-08',20,20,20),
            event('good2','2026-10-18',20,20,20),event('lot','2026-10-22',10,0,0,'first')]


def test_linked_lot_does_not_reset_whole_theme_spacing_but_updates_contact():
    from test_adaptive_planning import topic
    p=profile(max_questions=60,new_share=0)
    events=lot_history()
    control=topic_states([topic()],events[:-1],[],{},'2026-10-22',p)[0]
    state=topic_states([topic()],events,[],{},'2026-10-22',p)[0]
    assert state['review_interval_days']==control['review_interval_days']==14
    assert state['last_contact']=='2026-10-22'
    assert state['theme_review_due']=='2026-11-01'
    assert state['next_review']=='2026-10-29'


def test_lot_only_dose_and_forecast_preserve_whole_theme_due_date():
    from test_adaptive_planning import topic
    p=profile(max_questions=60,new_share=0)
    states=topic_states([topic()],lot_history(),[],{},'2026-10-29',p)
    days=forecast_calendar(states,p,'2026-10-29',5,lot_history(),{})
    assert days[0]['items'][0]['review_kind']=='lot_only'
    assert days[0]['questions']==10
    assert not days[1]['items']
    assert days[3]['items'][0]['review_kind']=='theme'


def test_admission_accounts_for_future_rest_and_smaller_daily_target():
    p=profile(max_questions=60,max_topics=3,new_share=.4)
    states=topic_states([imported(str(i),n=0,contact=None) for i in range(20)],[],[],{},'2026-10-15',p)
    settings={'2026-10-22':{'questions':60,'kind':'descanso','extra_topics':[]}}
    days=forecast_calendar(states,p,'2026-10-15',8,[],settings)
    assert not days[0]['items']
    assert days[-1]['questions']==0 and days[-1]['topic_backlog']==0


def test_small_linked_lot_cannot_postpone_due_whole_theme():
    from test_confidence import event
    from test_adaptive_planning import topic
    events=[event('first','2026-10-01',5,0,0)]
    before=topic_states([topic()],events,[],{},'2026-10-08',profile())[0]
    after=topic_states([topic()],events+[event('lot','2026-10-08',5,5,5,'first')],[],{},'2026-10-08',profile())[0]
    assert after['last_contact']=='2026-10-08'
    assert after['theme_review_due']==before['theme_review_due']=='2026-10-04'


def test_multiple_lots_on_same_day_consume_their_combined_capacity():
    from osler.study_capacity import capacity_policy
    p=profile(max_questions=40,max_topics=3,new_share=.5)
    states=topic_states([imported('old'),imported('new',n=0,contact=None)],[],[],{},'2026-10-15',p)
    old=next(t for t in states if t['topic_id']=='old')
    old.update(review_committed=True,next_review='2026-10-22',theme_review_due='2026-11-10',pending_reviews=[
        {'questions':20,'due_date':'2026-10-22'},{'questions':20,'due_date':'2026-10-22'}])
    kept,_,_=capacity_policy(states,p,'2026-10-15',40,40)
    assert 'new' not in {t['topic_id'] for t in kept}


def test_adaptive_reservation_can_use_needed_review_budget():
    p=profile(max_questions=100,max_topics=3,new_share=.4)
    states=topic_states([imported('A')],[],[],{},'2026-10-15',p)
    states[0].update(review_committed=True,next_review='2026-10-15',theme_review_due='2026-10-15',recommended_questions=80,theme_recommended_questions=80)
    reservations=[{'topic_id':'A','date':'2026-10-15','remaining':80,'original_due':'2026-10-14'}]
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=100,reservations=reservations)
    assert plan['questions']==80
    assert plan['items'][0]['rescheduled']
    assert plan['capacity']['unused_questions']==20
