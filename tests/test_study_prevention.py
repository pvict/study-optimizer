from copy import deepcopy
from osler.adaptive_planning import topic_states
from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile
from test_adaptive_planning import topic,session
from dataclasses import replace
import pytest
from osler.study_models import StudyEntry
from osler.adaptive_service import AdaptiveService
from test_assessments import setup_assessment


def test_orange_indicator_has_exact_specific_topic_details_and_no_fake_results():
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    states=topic_states([topic('A'),topic('B')],[],[],{},'2026-10-15',p)
    for t in states: t.update(next_review='2026-10-16',status='revisao',is_new_for_day=False,review_committed=True)
    before=deepcopy(states)
    days=forecast_calendar(states,p,'2026-10-15',4,[],{})
    assert any(d['topic_backlog'] for d in days)
    assert all(d['topic_backlog']==len(d['backlog_items']) for d in days)
    pending=next(d['backlog_items'][0] for d in days if d['backlog_items'])
    assert pending['path'][-1] in ['A','B'] and pending['due_date']=='2026-10-16'
    assert states==before


def test_preventive_lead_is_bounded_and_does_not_hold_first_contact_or_advance_queue():
    from osler.study_prevention import preventive_state
    p=AdaptiveProfile()
    state=topic_states([topic()],[],[],{},'2026-10-15',p)[0]
    policy=[{'start':'2026-10-15','end':'2026-10-30','topics':[state['topic_id']]}]
    fresh=preventive_state(state,'2026-10-15',policy)
    assert fresh.get('allocation_due') is None
    state.update(next_review='2026-10-22',review_interval_days=7,status='revisao')
    before=deepcopy(state)
    assert preventive_state(state,'2026-10-21',policy)['allocation_due']=='2026-10-21'
    assert preventive_state(state,'2026-10-20',policy)['allocation_due']=='2026-10-21'
    queued=preventive_state(state,'2026-10-21',policy,pending_due_dates=['2026-10-22'])
    assert queued['allocation_due']=='2026-10-22'
    state.update(next_review='2026-10-18',review_interval_days=3)
    assert preventive_state(state,'2026-10-17',policy)['allocation_due']=='2026-10-18'
    assert before['next_review']=='2026-10-22'


def test_temporary_prevention_reduces_projected_risk_without_mutating_study():
    from osler.study_prevention import summarize_risk
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    states=topic_states([topic('A'),topic('B')],[],[],{},'2026-10-15',p)
    for t in states: t.update(next_review='2026-10-17',review_interval_days=7,status='revisao',is_new_for_day=False,review_committed=True)
    before=forecast_calendar(states,p,'2026-10-15',4,[],{})
    agenda={'rows':[],'overrides':{'2026-10-17':{'mode':'extra','extra_questions':20}},
            'policies':[{'start':'2026-10-15','end':'2026-10-18','topics':['A','B']}]}
    after=forecast_calendar(states,p,'2026-10-15',4,[],{},agenda=agenda)
    assert summarize_risk(after,'2026-10-15','2026-10-18')['late_topic_days']<summarize_risk(before,'2026-10-15','2026-10-18')['late_topic_days']
    assert all(s['recorded_attempts']==0 for s in states)


def prevention_service(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.store.save_profile(AdaptiveProfile(max_questions=20,max_topics=1,new_share=0),0)
    t=max(service.catalog('2026-10-15')[0],key=lambda t:t['total'])
    service.save_entry(StudyEntry(t['path'],'2026-10-14',20,20,confident_correct=20),'actual')
    service.configure_day('2026-10-21',20,'descanso',0)
    return service,t


def test_service_prevents_a_future_rest_conflict_without_inventing_a_contact(tmp_path,sample_pdf):
    service,t=prevention_service(tmp_path,sample_pdf)
    assert not service.replanning()['backlog']
    context=service.prevention_context('2026-10-15',14)
    assert t['topic_id'] in [r['topic_id'] for r in context['candidates']]
    preview=service.preview_prevention('2026-10-15',14,'balanced')
    assert preview['after']['late_topic_days']<preview['before']['late_topic_days']
    event=service.apply_prevention(preview)
    assert len(service.store.active('2026-10-15'))==1
    state=next(row for row in service.overview('2026-10-15')['states'] if row['topic_id']==t['topic_id'])
    assert state['last_contact']=='2026-10-14' and state['next_review']=='2026-10-21'
    advanced=service.overview('2026-10-20')['plan']['items'][0]
    assert advanced['anticipated_days']==1
    service.cancel_replan(event)
    assert not service.replanning()['policies']
    assert len(service.store.active('2026-10-15'))==1


def test_preventive_preview_expires_and_cannot_overwrite_real_reservations(tmp_path,sample_pdf):
    service,t=prevention_service(tmp_path,sample_pdf)
    preview=service.preview_prevention('2026-10-15',14,'reviews')
    service.configure_day('2026-10-20',20,'descanso',0)
    with pytest.raises(ValueError,match='mud|atualiz'): service.apply_prevention(preview)
    # A política não utiliza selected de reservas: suas filas de recuperação ficam íntegras.
    row={'topic_id':t['topic_id'],'path':t['path'],'date':'2026-10-22','original_due':'2026-10-21','questions':20,'new_topic':False}
    service.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-15','cutoff':1,'selected':[t['topic_id']],
                          'rows':[row],'overrides':{},'mode':'balanced','start':'2026-10-22','days':1},service.agenda.token())
    fresh=service.preview_prevention('2026-10-15',14,'extra',extra_questions=20)
    original=service.replanning()['rows']
    service.apply_prevention(fresh)
    assert service.replanning()['rows']==original


def test_preview_matches_execution_and_does_not_change_today_for_a_future_policy(tmp_path,sample_pdf):
    service,first=prevention_service(tmp_path,sample_pdf)
    second={**first,'topic_id':'other-big','path':first['path'][:-1]+['Outro tema específico']}
    service.catalog=lambda as_of,include_parents=False:([first,second],{})
    service.store.void('actual',1)
    service.save_entry(StudyEntry(first['path'],'2026-10-12',20,0,confident_correct=0),'weak')
    service.save_entry(StudyEntry(second['path'],'2026-10-07',20,20,confident_correct=20),'strong')
    service.configure_day('2026-10-22',20,'descanso',0)
    service.configure_day('2026-10-23',20,'descanso',0)
    actual_today=service.overview('2026-10-15')['plan']['items'][0]['topic_id']
    preview=service.preview_prevention('2026-10-16',14,'balanced')
    service.apply_prevention(preview)
    assert service.overview('2026-10-15')['plan']['items'][0]['topic_id']==actual_today
    actual_forecast=service.prevention_context('2026-10-16',14)['summary']
    assert actual_forecast==preview['after']


def test_comparison_exposes_worsening_of_a_topic_already_at_risk():
    from osler.study_prevention import summarize_risk,worsened_risks
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    states=topic_states([topic('A'),topic('B'),topic('C')],[],[],{},'2026-10-15',p)
    for t in states:
        t.update(next_review='2026-10-17' if t['topic_id']=='A' else '2026-10-16',review_interval_days=7,status='revisao',is_new_for_day=False,review_committed=True)
    before=summarize_risk(forecast_calendar(states,p,'2026-10-15',14,[],{}),'2026-10-15','2026-10-28')
    agenda={'rows':[],'overrides':{},'policies':[{'start':'2026-10-15','end':'2026-10-28','topics':['A']}]}
    after=summarize_risk(forecast_calendar(states,p,'2026-10-15',14,[],{},agenda=agenda),'2026-10-15','2026-10-28')
    assert any(r['topic_id']=='C' for r in worsened_risks(before,after))


def test_forecast_preserves_real_difficulty_before_and_after_projected_contact():
    from osler.study_prevention import preventive_state
    from osler.adaptive_planning import allocate_day
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    topics=[topic('Weak'),topic('Strong')]
    entries=[session('Weak',day='2026-10-13',n=20,correct=0),
             session('Strong',day='2026-10-09',n=20,correct=20)]
    states=topic_states(topics,entries,[],{},'2026-10-15',p)
    agenda={'rows':[],'overrides':{},'policies':[{'start':'2026-10-16','end':'2026-10-25','topics':['Strong']}]}
    calendar=forecast_calendar(states,p,'2026-10-15',11,entries,{'2026-10-15':{'kind':'descanso','questions':20}},agenda=agenda)
    actual=[preventive_state(t,'2026-10-16',agenda['policies']) for t in topic_states(topics,entries,[],{},'2026-10-16',p)]
    plan=allocate_day(actual,p,None,'normal',entries,'2026-10-16',question_target=20)
    assert calendar[1]['items'][0]['topic_id']==plan['items'][0]['topic_id']=='Weak'
    weak=[i for d in calendar for i in d['items'] if i['topic_id']=='Weak']
    assert len(weak)>=2 and all(i['priority']=='urgente' for i in weak)


def test_forecast_keeps_post_reduction_priority_until_projected_contact():
    from osler.adaptive_planning import allocate_day
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    topics=[{**topic('Reduced',answered=20),'cards_reduced_day':'2026-09-01'},topic('Other',answered=20)]
    states=topic_states(topics,[],[],{},'2026-10-15',p)
    days=forecast_calendar(states,p,'2026-10-15',4,[],{'2026-10-15':{'kind':'descanso','questions':20}})
    real=allocate_day(topic_states(topics,[],[],{},'2026-10-16',p),p,None,'normal',[],'2026-10-16',question_target=20)
    assert days[1]['items'][0]['topic_id']==real['items'][0]['topic_id']=='Reduced'
    assert days[1]['items'][0]['priority']=='alta'
    assert days[2]['items'][0]['topic_id']=='Other'
