from dataclasses import replace
import pytest
from osler.study_models import AdaptiveProfile,StudyEntry
from osler.adaptive_planning import topic_states,allocate_day
from osler.algorithm_parameters import V1
from test_adaptive_planning import topic


def profile(**kwargs): return AdaptiveProfile(review_strategy='balanced_v2',target_accuracy=95,**kwargs)


def block(day='2026-10-08',n=19,correct=17,confident=15,mode='novas',review_of=None):
    return {'id':int(day[-2:]),'session_id':day+mode+str(n),'version':1,
            'entry':StudyEntry(['Área','Tema'],day,n,correct,mode=mode,confident_correct=confident,review_of=review_of).to_dict()}


def state(events,day='2026-10-09',p=None,**fields):
    return topic_states([{**topic(),**fields}],events,[],{},day,p or profile())[0]


def test_legacy_remains_default_and_unknown_strategy_is_rejected():
    assert AdaptiveProfile().review_strategy=='legacy_v1'
    with pytest.raises(ValueError): replace(profile(),review_strategy='inventada').validate()


def test_near_target_small_sample_has_variable_dose_and_keeps_initial_week():
    t=state([block()])
    assert 10<=t['theme_recommended_questions']<20
    assert t['review_interval_days']==7
    assert t['theme_review_due']=='2026-10-15'
    assert t['performance']['exact_correct']==17 and t['confidence']['exact_correct']==15
    assert t['dose_kind']!='reinforcement'


def test_low_confidence_does_not_imitate_objective_failure():
    good=state([block(confident=15)]); insecure=state([block(confident=2)])
    for field in ['review_interval_days','theme_recommended_questions','evidence_priority','learning_state']:
        assert good[field]==insecure[field]
    bad=state([block(correct=9,confident=8)])
    assert bad['theme_recommended_questions']>good['theme_recommended_questions']
    assert bad['review_interval_days']<good['review_interval_days']
    assert bad['priority']=='urgente'


def test_spaced_objective_success_can_grow_without_perfect_confidence():
    once=state([block(confident=None)])
    twice=state([block(confident=None),block('2026-10-15',confident=None)],'2026-10-16')
    assert twice['review_interval_days']>once['review_interval_days']
    assert twice['theme_recommended_questions']<once['theme_recommended_questions']
    assert twice['confidence']['exact_n']==0
    assert twice['learning_state']!='dominado'  # abaixo da meta, sem domínio fictício


def test_early_practice_or_linked_returns_do_not_prove_spaced_retention():
    early=state([block(),block('2026-10-09')],'2026-10-10')
    linked=state([block(),block('2026-10-15',n=4,correct=4,confident=4,mode='repetidas',review_of=block()['session_id'])],'2026-10-16')
    assert early['review_interval_days']==7 and early['dose_kind']!='maintenance'
    assert linked['spacing']['last_evidence_day']=='2026-10-08'
    assert linked['performance']['exact_n']==19


def test_good_repeated_results_cannot_hide_bad_new_questions():
    t=state([block(correct=9,confident=8),block('2026-10-15',n=20,correct=20,confident=20,mode='repetidas')],'2026-10-16')
    assert t['performance']['exact_correct']==9
    assert t['dose_kind']=='reinforcement' and t['review_interval_days']<=3


def test_no_objective_measurement_keeps_diagnostic_and_unknown_accuracy():
    t=state([],answered_pdf=34)
    assert t['performance']['exact_n']==0
    assert t['theme_recommended_questions']>=20


def test_close_dates_coordinate_without_changing_lot_deadline_or_delaying_weak_theme():
    p=profile(parameter_values=replace(V1,version=2,first_interval=6).to_dict())
    t=state([block()],p=p)
    assert t['theme_review_due']=='2026-10-15'
    assert t['pending_reviews'][0]['due_date']=='2026-10-15'
    assert t['review_coordination']['original_due']=='2026-10-14'
    bad=state([block(correct=9,confident=8)],p=p)
    assert bad['theme_review_due']=='2026-10-11'


def test_small_known_lot_gets_its_real_size_without_inflating_to_ten():
    p=profile(parameter_values=replace(V1,version=2,first_interval=14).to_dict())
    t=state([block()],'2026-10-15',p)
    plan=allocate_day([t],p,None,'normal',[block()],'2026-10-15',question_target=20)
    assert plan['questions']==4
    assert plan['items'][0]['review_kind']=='lot_only'
    assert t['theme_review_due']=='2026-10-22'


def test_combined_lot_and_theme_count_once_with_measurable_complement():
    p=profile(); original=block(); t=state([original],'2026-10-15',p)
    plan=allocate_day([t],p,None,'normal',[original],'2026-10-15',question_target=30)
    assert plan['items'][0]['questions']==max(4,t['theme_recommended_questions'])  # orçamento compartilhado, sem piso extra
    linked=block('2026-10-15',n=4,correct=4,confident=4,mode='repetidas',review_of=original['session_id'])
    updated=state([original,linked],'2026-10-15',p)
    after=allocate_day([updated],p,None,'normal',[original,linked],'2026-10-15',question_target=30)
    assert after['done_questions']==4
    assert after['items'][0]['questions']==plan['items'][0]['questions']-4


def test_critical_errors_and_long_gap_keep_protection():
    t=state([block(),block('2026-10-15')],'2026-10-16',manual_context={'erros_criticos':True})
    assert t['dose_kind']=='reinforcement' and t['review_interval_days']<=3
    recent=state([block(),block('2026-10-15')],'2026-10-16')
    stale=state([block(),block('2026-10-15')],'2027-01-01')
    assert stale['theme_recommended_questions']>=recent['theme_recommended_questions']


@pytest.mark.parametrize('budget,share',[(4,0),(12,.2)])
def test_small_daily_budget_can_fit_the_lot_without_claiming_whole_theme_review(budget,share):
    from osler.study_calendar import forecast_calendar
    p=profile(max_questions=budget,new_share=share); e=block(); t=state([e],'2026-10-15',p)
    plan=allocate_day([t],p,None,'normal',[e],'2026-10-15',question_target=budget)
    assert plan['questions']==4 and plan['items'][0]['review_kind']=='lot_only'
    assert len(plan['items'])==1
    calendar=forecast_calendar([t],p,'2026-10-15',2,[e],{},next_contact_only=True)
    assert not calendar[0]['awaiting_results']


def test_balanced_projection_does_not_reintroduce_incidence_shortening():
    from osler.evolution_spacing import advance_projected_spacing
    p=profile(); e=block(); t=state([e]); t['incidence_strength']=1
    original=t['performance'].copy()
    advance_projected_spacing(t,p,'2026-10-15',20)
    assert t['review_interval_days']==14
    assert t['performance']==original


def test_combined_parts_preserve_links_and_count_each_attempt_once():
    from osler.balanced_reviews import review_parts
    e=block(); t=state([e],'2026-10-15'); t['questions']=15
    parts=review_parts(t,'2026-10-15')
    assert parts['lot_questions']==4 and parts['complement']==11
    assert parts['lots'][0]['session_id']==e['session_id']
    t['questions']=2
    parts=review_parts(t,'2026-10-15')
    assert parts['lot_questions']==2 and parts['complement']==0
    assert t['pending_reviews'][0]['questions']==4


def test_failed_linked_return_blocks_mastery_without_polluting_new_question_posterior():
    a=block('2026-10-01',n=40,correct=40,confident=30)
    b=block('2026-10-08',n=40,correct=40,confident=40)
    failed=block('2026-10-09',n=10,correct=0,confident=0,mode='repetidas',review_of=a['session_id'])
    t=state([a,b,failed],'2026-10-09')
    assert t['performance']['exact_n']==80 and t['performance']['exact_correct']==80
    assert t['learning_state']!='dominado' and t['dose_kind']=='reinforcement'
    assert t['evidence_priority'] in {'alta','urgente'}
    recovered=block('2026-10-16',n=10,correct=10,confident=10,mode='repetidas',review_of=failed['session_id'])
    restored=state([a,b,failed,recovered],'2026-10-16')
    assert not restored['linked_adverse']
    assert restored['performance']['exact_n']==80


def test_combined_capacity_matches_real_lot_plus_representative_requirement():
    from osler.study_capacity import capacity_policy
    p=profile(workload_mode='adaptive',max_questions=40)
    t=state([block(confident=1)],'2026-10-15',p)
    _,_,meta=capacity_policy([t],p,'2026-10-15',40,40)
    assert meta['due_questions']==t['recommended_questions']==18  # lote real; sem acrescentar dez automaticamente


def test_large_lot_can_be_partially_reviewed_in_a_small_budget():
    p=profile(max_questions=4,new_share=0); e=block(n=40,correct=30,confident=25)
    t=state([e],'2026-10-15',p)
    plan=allocate_day([t],p,None,'normal',[e],'2026-10-15',question_target=4)
    assert plan['questions']==4 and plan['items'][0]['review_kind']=='lot_only'


def test_progressive_scenario_requires_same_spacing_as_real_evidence():
    from osler.evolution_spacing import advance_projected_spacing
    p=profile(); t=state([block()]); before=t['review_interval_days']
    advance_projected_spacing(t,p,'2026-10-11',20)
    assert t['review_interval_days']==before


def test_lot_completed_yesterday_is_credited_in_nearby_theme_complement():
    p=profile(max_questions=10,new_share=0); original=block()
    linked=block('2026-10-15',n=4,correct=4,confident=4,mode='repetidas',review_of=original['session_id'])
    t=state([original,linked],'2026-10-16',p)
    assert t['recommended_questions']==t['theme_recommended_questions']-4
    from osler.study_calendar import forecast_calendar
    calendar=forecast_calendar([state([original],'2026-10-15',p)],p,'2026-10-15',2,[original],{},next_contact_only=True)
    assert calendar[0]['items'][0]['questions']==4
    assert calendar[1]['items'][0]['questions']==t['recommended_questions']
