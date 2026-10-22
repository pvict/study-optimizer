from copy import deepcopy
from osler.study_evolution import evolution_snapshot,evolution_attention
from test_initial_review_policy import imported
from test_adaptive_planning import session


def state(name,n=0,rate=90):
    t=imported(name,rate,n=n,contact='2026-10-01' if n else None)
    return {**t,'planner_safety':t['planner_snapshot'],'importance':.5,'low_accuracy':rate<60,
            'last_contact':'2026-10-01' if n else None,'review_interval_days':7,'confidence':{'observed':None},
            'performance':{'observed':None},'is_leaf':True}


def test_attempts_distinct_sources_and_coverage_are_not_added_twice():
    states=[state('A',34),state('B')]
    events=[session('A',n=10,mode='repetidas')]
    days=[{'date':'2026-10-16','questions':20,'items':[{'topic_id':'A','path':['Área','A'],'questions':10},{'topic_id':'B','path':['Área','B'],'questions':10}]}]
    before=deepcopy((states,events,days))
    result=evolution_snapshot(states,events,days,'2026-10-15')
    assert result['imported_unique']==34 and result['actual_attempts']==10
    assert result['points'][0]['covered']==1
    assert result['points'][-1]['covered']==2 and result['points'][-1]['attempts']==30
    assert result['points'][-1]['future_attempts']==20
    assert (states,events,days)==before


def test_planned_contact_does_not_cure_weakness_or_award_actual_achievement():
    states=[state('A',50,40),state('B')]
    days=[{'date':'2026-10-16','questions':100,'items':[{'topic_id':'A','path':['Área','A'],'questions':100}]}]
    result=evolution_snapshot(states,[],days,'2026-10-15')
    attention=evolution_attention(result,'2026-10-16')
    assert next(r for r in attention if r['topic_id']=='A')['kind']=='Reforçar'
    assert next(r for r in attention if r['topic_id']=='B')['kind']=='Não visto'
    badge=next(b for b in result['achievements'] if b['id']=='questions100')
    assert not badge['earned'] and badge['projected_date']=='2026-10-16'


def test_future_entries_and_broad_topics_do_not_manufacture_coverage():
    states=[state('A'),{**state('Broad',99),'is_leaf':False}]
    result=evolution_snapshot(states,[session('A',day='2026-10-18')],[],'2026-10-15')
    assert result['actual_attempts']==0 and result['total_topics']==1
    assert result['points'][0]['covered']==0
    assert not any(b['earned'] for b in result['achievements'])


def test_empty_data_and_contact_gap_are_safe():
    result=evolution_snapshot([],[],[],'2026-10-15')
    assert result['points'][0]['coverage_pct']==0
    assert evolution_attention(result,'2026-10-15')==[]
    result=evolution_snapshot([state('A',50)],[],[],'2026-10-15',max_gap=30)
    assert evolution_attention(result,'2026-12-01')[0]['kind']=='Retomar contato'


def test_snapshot_from_future_is_not_credited_as_imported_progress():
    t=state('A',34); t['answered_pdf']=0
    t['planner_safety']['observed_date']='2026-10-20'
    result=evolution_snapshot([t],[],[],'2026-10-15')
    assert result['imported_unique']==0 and result['covered_now']==0


def test_manual_accumulated_records_cover_theme_without_block_totals_or_badges():
    t=state('A'); t['performance']={'observed':.8}; t['performance_source']='acumulado'
    events=[session('A',kind='acumulado',n=40,correct=32)]
    s=evolution_snapshot([t],events,[],'2026-10-15')
    assert s['actual_attempts']==0 and s['covered_now']==1
    assert 'A' in s['covered_ids_now']
    assert s['topics'][0]['rate_source']=='Total acumulado informado'
    assert not next(b for b in s['achievements'] if b['id']=='first')['earned']
    assert not any(r['kind']=='Não visto' for r in evolution_attention(s,'2026-10-15'))


def test_journey_near_exam_labels_real_end_instead_of_clamped_two_weeks():
    from osler.evolution_components import journey_svg
    s=evolution_snapshot([state('A')],[],[],'2026-10-15')
    svg=journey_svg({'as_of':'2026-10-15','end':'2026-10-22','exam_in_horizon':True,'snapshot':s},'2026-10-22')
    assert 'Fim da preparação' in svg and '2 semanas' not in svg


def test_imported_safety_is_a_separate_descriptive_baseline():
    s=evolution_snapshot([state('A',34,73.5),state('B',16,50)],[],[],'2026-10-15')
    safety=s['imported_safety']
    assert safety['topics']==2 and safety['questions_per_topic_sum']==50
    assert abs(safety['weighted_pct']-65.98)<.001
    assert s['actual_attempts']==0
