from dataclasses import replace
import pytest
from osler.study_models import AdaptiveProfile,StudyEntry
from osler.adaptive_planning import topic_states
from test_adaptive_planning import topic


def strong():
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    events=[{'id':i,'session_id':str(i),'entry':StudyEntry(['Área','A'],d,100,100,confident_correct=100).to_dict()} for i,d in enumerate(['2026-10-01','2026-10-08'],1)]
    t=topic_states([topic('A',1000,100)],events,[],{},'2026-10-15',p)[0]
    t.update(importance=.01,incidence_strength=.01,incidence_known=True)
    return t


@pytest.mark.parametrize('field,value',[('registered_error',True),('manual_adverse',True),('open_error_count',1),('low_accuracy',True),('incidence_known',False)])
def test_triage_never_reduces_protected_themes(field,value):
    from osler.study_triage_policy import propose_triage
    state=strong(); state[field]=value
    report=propose_triage([state],[{'date':'2026-10-15','target_questions':1,'items':[]}],'2026-10-15','2026-12-15')
    assert report['rows'][0]['action']=='manter'
    assert report['demand_questions']>report['capacity_questions']


def test_triage_proposes_longer_interval_only_with_sufficient_confidence():
    from osler.study_triage_policy import propose_triage,apply_triage
    state=strong(); original=dict(state)
    report=propose_triage([state],[{'date':'2026-10-15','target_questions':1,'items':[]}],'2026-10-15','2026-12-15')
    row=report['rows'][0]
    assert row['action']=='reduzir frequência' and row['new_interval']>row['old_interval']
    changed=apply_triage([state],[{'start':'2026-10-15','end':'2026-12-15','rows':[row]}],'2026-10-15')[0]
    assert changed['review_interval_days']>state['review_interval_days']
    assert state==original


def test_service_triage_preview_apply_undo_does_not_modify_study(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    from test_assessments import setup_assessment
    repo,*_=setup_assessment(tmp_path,sample_pdf); service=AdaptiveService(repo)
    p=service.preview_triage(14)
    before=service.store.events()
    assert not service.agenda.active(service.store.active('2026-10-15'),'2026-10-15').get('triage_policies')
    assert p['before']['deficit_questions']>=0
    with pytest.raises(ValueError): service.apply_triage({**p,'token':'old'})
    assert service.store.events()==before


def test_service_safe_cut_applies_and_undo_restores_interval_and_history(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    from test_assessments import setup_assessment
    repo,*_=setup_assessment(tmp_path,sample_pdf); service=AdaptiveService(repo)
    service.store.save_profile(AdaptiveProfile(max_questions=1,max_topics=1,new_share=0),0)
    t=max(service.catalog('2026-10-15')[0],key=lambda t:t['total'])
    service.guide.store.save_dataset({'institutions':['X'],'observed_date':'2026-10-15','unit':'questoes',
                                      'rows':[{'path':t['path'],'value':100,'band':'alta'}]})
    for i,day in enumerate(['2026-10-01','2026-10-08']):
        service.save_entry(StudyEntry(t['path'],day,100,100,confident_correct=100),'healthy'+str(i))
    original=next(s for s in service.overview('2026-10-15')['planning_states'] if s['topic_id']==t['topic_id'])
    preview=service.preview_triage(90)
    assert any(r['topic_id']==t['topic_id'] for r in preview['policy']['rows'])
    before=service.store.events(); pid=service.apply_triage(preview)
    after=next(s for s in service.overview('2026-10-15')['planning_states'] if s['topic_id']==t['topic_id'])
    assert after['review_interval_days']>original['review_interval_days']
    assert after['spacing']==original['spacing']
    service.cancel_replan(pid)
    restored=next(s for s in service.overview('2026-10-15')['planning_states'] if s['topic_id']==t['topic_id'])
    assert restored['review_interval_days']==original['review_interval_days'] and service.store.events()==before


def test_policy_expiry_and_known_lots_restore_consistently():
    from osler.study_triage_policy import apply_triage
    state=strong(); state['pending_reviews']=[{'due_date':'2026-10-20','questions':3}]
    row={'topic_id':state['topic_id'],'action':'adiar','old_interval':14,'new_interval':21,'defer_until':'2026-11-10','reason':'teste'}
    policies=[{'start':'2026-10-15','end':'2026-10-30','rows':[row]}]
    changed=apply_triage([state],policies,'2026-10-15')[0]
    assert changed['next_review']=='2026-10-20'
    restored=apply_triage([changed],policies,'2026-10-31')[0]
    assert restored['theme_review_due']==state['theme_review_due']
    assert restored['review_interval_days']==state['review_interval_days']


def cut_policy(state):
    return [{'start':'2026-10-15','end':'2026-11-30','rows':[
        {'topic_id':state['topic_id'],'action':'reduzir frequência','new_interval':21,'reason':'teste'}]}]


def test_cut_survives_fresh_reconstruction_on_original_due_day():
    from osler.study_triage_policy import apply_triage
    state=strong(); policies=cut_policy(state)
    assert state['theme_review_due']=='2026-10-22'
    assert apply_triage([state],policies,'2026-10-15')[0]['theme_review_due']=='2026-10-29'
    assert apply_triage([state],policies,'2026-10-22')[0]['theme_review_due']=='2026-10-29'
    overdue={**state,'theme_review_due':'2026-10-14'}
    assert apply_triage([overdue],policies,'2026-10-22')[0]['theme_review_due']=='2026-10-14'


def test_cut_forecast_never_resurrects_a_consumed_return():
    from osler.study_calendar import forecast_calendar
    state=strong(); policies=cut_policy(state)
    state['pending_reviews']=[{'session_id':'lot','path':state['path'],'questions':10,
                              'due_date':'2026-10-16','source_date':'2026-10-09'}]
    state['next_review']='2026-10-16'
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    days=forecast_calendar([state],p,'2026-10-15',16,[],{},agenda={'rows':[],'overrides':{},'triage_policies':policies})
    contacts=[d['date'] for d in days if d['items']]
    assert contacts==['2026-10-16','2026-10-29']
    assert sum(d['pending_planned'] for d in days)==10


def test_unscheduled_catalog_is_not_recurring_review_demand():
    from osler.study_triage_policy import theme_demand,propose_triage
    unseen={**strong(),'review_committed':False,'status':'sem_registro','theme_review_due':None,'next_review':None}
    initial={**strong(),'review_committed':False}
    assert theme_demand(unseen,'2026-10-15','2026-11-15')==0
    assert theme_demand(initial,'2026-10-15','2026-11-15')==0
    initial['pending_reviews']=[{'due_date':'2026-10-20','questions':12}]
    assert theme_demand(initial,'2026-10-15','2026-11-15')==12
    result=propose_triage([initial],[{'date':'2026-10-15','target_questions':1}],'2026-10-15','2026-11-15')
    assert result['rows'][0]['action']=='manter'
