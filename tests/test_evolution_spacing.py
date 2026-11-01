from copy import deepcopy
from osler.study_models import AdaptiveProfile
from osler.adaptive_planning import topic_states
from osler.study_calendar import forecast_calendar
from test_initial_review_policy import imported


def scenario():
    p=AdaptiveProfile(max_questions=120,max_topics=5,new_share=.5,workload_mode='adaptive',start_date='2026-10-15')
    states=topic_states([imported(str(i),n=0,contact=None) for i in range(100)],[],[],{},'2026-10-15',p)
    return states,p


def covered(days):
    return {i['topic_id'] for d in days for i in d['items']}


def test_conditional_spacing_opens_capacity_without_modifying_real_evidence():
    states,p=scenario(); before=deepcopy(states)
    # Isola o efeito dos intervalos; o piso de novos também abre cobertura.
    from dataclasses import replace
    p=replace(p,minimum_new_share=0)
    frozen=forecast_calendar(states,p,'2026-10-15',120,[],{})
    advancing=forecast_calendar(states,p,'2026-10-15',120,[],{},spacing_scenario='progressive')
    assert len(covered(advancing))>len(covered(frozen))
    assert len(covered(advancing[:30]))<len(covered(advancing[:90]))
    assert states==before
    assert all(d['questions']<=p.max_questions and len(d['items'])<=p.max_topics for d in advancing)
    assert all(not s['spacing']['streak'] for s in states)


def test_current_interval_scenario_matches_operational_calendar():
    states,p=scenario()
    a=forecast_calendar(states,p,'2026-10-15',20,[],{})
    b=forecast_calendar(states,p,'2026-10-15',20,[],{},spacing_scenario='unchanged')
    assert a==b


def test_spacing_assumption_respects_cap_and_does_not_advance_lot_only():
    from osler.evolution_spacing import advance_projected_spacing
    states,p=scenario(); t=states[0]
    for day in ['2026-10-15','2026-10-22','2026-11-05','2026-12-05']:
        advance_projected_spacing(t,p,day,p.min_block)
    assert t['projected_spacing']['streak']==4
    assert t['review_interval_days']<=p.max_contact_gap
    before=deepcopy(t)
    advance_projected_spacing(t,p,'2027-01-04',p.min_block,lot_only=True)
    assert t==before


def test_rest_start_and_exam_limits_apply_to_conditional_scenario():
    from dataclasses import replace
    states,p=scenario(); p=replace(p,start_date='2026-10-17',exam_date='2026-10-25')
    settings={'2026-10-18':{'questions':120,'kind':'descanso','extra_topics':[]}}
    days=forecast_calendar(states,p,'2026-10-15',20,[],settings,spacing_scenario='progressive')
    assert all(not d['questions'] for d in days if d['date']<p.start_date or d['date']>p.exam_date or d['date']=='2026-10-18')


def test_invalid_spacing_scenario_is_rejected():
    import pytest
    states,p=scenario()
    with pytest.raises(ValueError): forecast_calendar(states,p,'2026-10-15',5,[],{},spacing_scenario='invalid')


def test_assumed_success_requires_full_spaced_contact_and_preserves_adverse_flags():
    from osler.evolution_spacing import advance_projected_spacing
    states,p=scenario(); t=states[0]; before=deepcopy(t)
    advance_projected_spacing(t,p,'2026-10-15',p.min_block-1)
    assert t==before
    t['manual_adverse']=True; before=deepcopy(t)
    advance_projected_spacing(t,p,'2026-10-15',20)
    assert t==before
    t['manual_adverse']=False
    advance_projected_spacing(t,p,'2026-10-15',20)
    before=deepcopy(t)
    advance_projected_spacing(t,p,'2026-10-15',20)
    assert t==before and t['projected_spacing']['streak']==1


def test_exam_compression_does_not_manufacture_daily_qualifying_successes():
    from osler.evolution_spacing import advance_projected_spacing
    states,p=scenario(); t=states[0]
    t['spacing'].update(streak=2,base_interval=14,last_evidence_day='2026-10-15')
    t['review_interval_days']=1
    before=deepcopy(t)
    advance_projected_spacing(t,p,'2026-10-16',20)
    assert t==before
