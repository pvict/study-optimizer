from dataclasses import replace
import pytest
from osler.study_models import AdaptiveProfile
from osler.adaptive_planning import topic_states,allocate_day
from osler.study_capacity import capacity_policy
from osler.study_feedback import result_feedback
from osler.study_calendar import forecast_calendar
from test_adaptive_planning import topic
from test_balanced_reviews import block


def profile(**kw):return AdaptiveProfile(review_strategy='balanced_v2',target_accuracy=90,**kw)


def state(events,day='2026-10-27',p=None,name='Tema'):
    events=[{**e,'entry':{**e['entry'],'path':['Área',name]}} for e in events]
    return topic_states([topic(name)],events,[],{},day,p or profile())[0],events


@pytest.mark.parametrize('name',['Tema','Outro tema','Queimaduras'])
def test_next_encounter_is_earliest_real_lot_for_every_topic(name):
    t,events=state([block('2026-10-23',22,15,7),block('2026-10-27',23,17,11)],name=name)
    v={'states':[t],'sessions':events,'date':'2026-10-27','profile':profile().to_dict(),
       'review_queue':t['pending_reviews']}
    f=result_feedback(v,events[-1]['session_id'])
    assert f['next_contact']=='2026-10-30' and f['next_questions']==15
    assert f['next_review_kind']=='lot_only'
    assert f['theme_questions']<22 and f['theme_contact']=='2026-11-03'
    assert t['performance']['exact_n']==45 and t['performance']['exact_correct']==32
    assert t['learning_state']!='dominado'


def test_lots_and_theme_share_the_same_budget_in_plan_feedback_and_capacity():
    p=profile(workload_mode='adaptive',max_questions=120,new_share=0)
    t,events=state([block('2026-10-20',30,27,2)],p=p)
    due=sum(q['questions'] for q in t['pending_reviews'])
    expected=max(due,t['theme_recommended_questions'])
    assert t['recommended_questions']==expected
    _,_,meta=capacity_policy([t],p,'2026-10-27',120,120)
    assert meta['due_questions']==expected
    plan=allocate_day([t],p,None,'normal',events,'2026-10-27',question_target=120)
    assert plan['items'][0]['questions']==expected


def test_recovered_old_low_score_does_not_keep_interval_at_three_days():
    events=[block('2026-10-01',100,50,30),block('2026-10-08',20,19,10),block('2026-10-15',20,19,10)]
    t,_=state(events,day='2026-10-16')
    assert t['review_interval_days']>7
    assert t['performance']['exact_correct']==88 and t['performance']['exact_n']==140


def test_moderate_deficit_is_not_catastrophic_failure_but_real_failure_stays_short():
    moderate,_=state([block('2026-10-23',30,20,10)])
    failed,_=state([block('2026-10-23',30,12,10)])
    assert moderate['review_interval_days']==7
    assert failed['review_interval_days']<=3


def test_small_random_fluctuation_does_not_raise_dose_with_more_evidence():
    first,_=state([block('2026-10-08',20,18,10)],day='2026-10-08')
    second,_=state([block('2026-10-08',20,18,10),block('2026-10-15',20,17,10)],day='2026-10-15')
    assert second['theme_recommended_questions']<=first['theme_recommended_questions']


def test_large_successful_linked_return_avoids_an_immediate_extra_theme_block():
    p=profile(new_share=0)
    root=block('2026-10-08',30,27,2)
    linked=block('2026-10-15',28,27,27,mode='repetidas',review_of=root['session_id'])
    t,events=state([root,linked],day='2026-10-16',p=p)
    assert t['theme_review_due']>='2026-10-22'
    assert t['spacing']['last_evidence_day']=='2026-10-08'
    assert t['performance']['exact_n']==30
    assert not allocate_day([t],p,None,'normal',events,'2026-10-16',question_target=120)['items']


def test_projection_waits_for_result_after_lot_covers_review_budget():
    p=profile(new_share=0)
    t,events=state([block('2026-10-08',30,27,2)],day='2026-10-15',p=p)
    days=forecast_calendar([t],p,'2026-10-15',2,events,{},next_contact_only=True)
    assert days[0]['items'][0]['questions']==28
    assert not days[1]['items']


def test_operational_contact_keeps_failed_returns_and_exam_deadline_protected():
    p=profile(exam_date='2026-10-18')
    root=block('2026-10-08',30,27,2)
    bad=block('2026-10-15',28,0,0,mode='repetidas',review_of=root['session_id'])
    failed,_=state([root,bad],day='2026-10-16',p=p)
    assert failed['theme_review_due']<='2026-10-16'
    good=block('2026-10-15',28,28,28,mode='repetidas',review_of=root['session_id'])
    from osler.balanced_reviews import operational_contact_due
    due=operational_contact_due({'theme_review_due':'2026-10-15','recommended_questions':10},p,[good['entry']],'2026-10-16')
    assert due<=p.exam_date


def test_later_failed_linked_return_is_not_hidden_by_an_earlier_success():
    from osler.balanced_reviews import operational_contact_due
    root=block('2026-10-08',30,27,2)
    good=block('2026-10-14',28,28,28,mode='repetidas',review_of=root['session_id'])
    bad=block('2026-10-16',28,0,0,mode='repetidas',review_of=good['session_id'])
    due=operational_contact_due({'theme_review_due':'2026-10-15','recommended_questions':10},profile(),[good['entry'],bad['entry']],'2026-10-16')
    assert due=='2026-10-15'


@pytest.mark.parametrize('complement_day',['2026-10-15','2026-10-16'])
def test_completed_joint_budget_does_not_repeat_small_complement_next_day(complement_day):
    p=profile(new_share=0)
    root=block('2026-10-08',30,27,20)
    linked=block('2026-10-15',10,9,9,mode='repetidas',review_of=root['session_id'])
    complement=block(complement_day,3,3,3)
    t,events=state([root,linked,complement],day='2026-10-17',p=p)
    assert t['theme_review_due']>'2026-10-17'
    assert t['spacing']['last_evidence_day']=='2026-10-08'
    assert t['performance']['exact_n']==33
    assert not allocate_day([t],p,None,'normal',events,'2026-10-17',question_target=120)['items']
