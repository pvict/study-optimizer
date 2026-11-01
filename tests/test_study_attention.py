"""Cruzamentos de atenção usam somente dados sintéticos em memória."""
from copy import deepcopy
from osler.study_attention import attention_overview,attention_filter,attention_table

DAY='2026-10-29'
PATH=['Clínica Médica','Cardiologia','Tema específico']


def state(topic_id='a',**values):
    return {'topic_id':topic_id,'path':PATH,'priority':'normal','score':.2,'importance':.1,
            'status':'sem_registro','recorded_attempts':0,'answered_pdf':0,'last_contact':None,
            'review_interval_days':7,'next_review':None,'performance':{},'review_committed':False,
            'recommended_questions':20,**values}


def dataset(value=12,path=None,**values):
    return {'id':1,'observed_date':'2026-10-28','institutions':['USP'],'unit':'questoes',
            'rows':[{'path':path or PATH,'value':value}],**values}


def overview(states=None,datasets=None,**values):
    view={'states':states if states is not None else [state()],
          'profile':{'institution_weights':{'USP':1}},**values}
    return attention_overview(view,datasets or [],DAY)


def test_incident_unpracticed_and_zero_are_distinct_from_absent():
    model=overview(datasets=[dataset()]); row=model['rows'][0]
    assert model['incident_unpracticed']==1 and row['attention'] and row['never_seen']
    assert row['last_contact'] is None and row['days_without_contact'] is None
    zero=overview(datasets=[dataset(0)])['rows'][0]
    absent=overview()['rows'][0]
    assert zero['incidences'][0]['value']==0 and not zero['incident_unpracticed']
    assert not absent['incidences'] and not absent['incident_unpracticed']
    assert attention_table([zero])[0]['Incidência bruta']==0
    assert attention_table([absent])[0]['Incidência bruta'] is None
    assert attention_table([absent])[0]['Acerto']=='Sem medição'


def test_specific_leaf_does_not_require_an_invented_third_level():
    s=state(path=['Clínica Cirúrgica','Queimaduras'],is_leaf=True,is_practice_unit=True)
    assert overview([s])['rows'][0]['path']==s['path']


def test_unpracticed_group_uses_institution_importance_before_contact_age():
    a=state('high',path=PATH[:-1]+['Incidente'],importance=.8,score=.1)
    b=state('low',path=PATH[:-1]+['Menos incidente'],importance=.1,score=5)
    rows=overview([b,a])['rows']
    assert [r['topic_id'] for r in attention_filter(rows,'Nunca praticados')]==['high','low']


def test_parent_incidence_does_not_claim_specific_incidence_or_add_sources():
    model=overview(datasets=[dataset(path=PATH[:-1])])
    row=model['rows'][0]
    assert not row['incident_unpracticed'] and not row['incidences'][0]['exact']
    assert attention_table([row])[0]['Incidência bruta'] is None
    assert 'não individual' in attention_table([row])[0]['Fonte da incidência']
    joint=dataset(institutions=['USP','UNIFESP'])
    model=overview(datasets=[joint],profile={'institution_weights':{'USP':1,'UNIFESP':1}})
    assert model['rows'][0]['incidences'][0]['institutions']==['USP','UNIFESP']
    assert len(model['rows'][0]['incidences'])==1


def test_incidence_counts_sort_numerically_in_both_directions():
    rows=[]
    for value in (36,4,11,100,0):
        rows.extend(overview(datasets=[dataset(value)])['rows'])
    table=attention_table(rows)
    assert sorted(r['Incidência bruta'] for r in table)==[0,4,11,36,100]
    assert sorted((r['Incidência bruta'] for r in table),reverse=True)==[100,36,11,4,0]


def test_multiple_incidence_sources_and_percentages_are_not_added_or_mislabeled():
    tables=[dataset(36,institutions=['USP','UNIFESP']),
            dataset(11,id=2),dataset(2.5,id=3,institutions=['UNIFESP'],unit='percentual')]
    row=overview(datasets=tables,profile={'institution_weights':{'USP':1,'UNIFESP':1}})['rows'][0]
    table=attention_table([row])[0]
    assert table['Incidência · USP, UNIFESP · tabela #1']==36
    assert table['Incidência · USP · tabela #2']==11
    assert table['Incidência (%)']==2.5
    assert '36 questões · tema' in table['Fonte da incidência']


def test_scope_matches_selected_contexts_and_ignores_future_tables():
    tables=[dataset(),dataset(90,id=2,observed_date='2026-11-01')]
    assert overview(datasets=tables)['rows'][0]['incidences'][0]['value']==12
    assert not overview(datasets=tables,incidence={'contexts':[]})['rows'][0]['incidences']


def test_no_parents_areas_historical_rollups_or_own_content_parent_recommendations():
    rows=[state('area',path=PATH[:1]),state('specialty',path=PATH[:2]),
          state('parent',is_leaf=False,is_practice_unit=True),
          state('child',path=PATH+['Filho']),state('history',path=PATH[:-1]+['Histórico'],historical_aggregate=True),
          state('rollup',path=PATH[:-1]+['Agrupado'],rollup=True)]
    assert [r['topic_id'] for r in overview(rows)['rows']]==['child']


def test_objective_accuracy_modality_and_conviction_remain_separate():
    s=state(status='diagnostico',answered_pdf=70,report_date='2026-10-28',
            pdf_accuracy={'raw':'99%','value':99,'operator':'='},
            planner_safety={'observed_date':'2026-10-28','confident_accuracy_pct':0,'unique_questions':80})
    row=overview([s])['rows'][0]
    assert row['accuracy']['rate'] is None and row['conviction']['rate']==0
    assert row['last_contact'] is None and row['attention'] and not row['never_practiced']
    s.update(performance={'exact_n':10,'observed':0,'reported_n':30,'reported_percent':.6,'interval':[0,.28]},performance_source='novas',
             repeated={'exact_n':100,'observed':1})
    row=overview([s])['rows'][0]
    assert row['accuracy']['rate']==0 and row['accuracy']['n']==10
    assert row['accuracy']['mode']=='novas'
    assert '0.0% · n=10 · novas' in attention_table([row])[0]['Acerto']
    s.update(performance={'exact_n':0,'reported_n':20,'reported_percent':.8},repeated={})
    assert overview([s])['rows'][0]['accuracy']['approximate']


def test_contact_unknown_is_not_a_zero_age_and_known_gap_uses_existing_interval():
    a=state('old',status='revisao',answered_pdf=10,last_contact='2026-10-01',next_review='2026-10-08')
    b=state('today',path=PATH[:-1]+['Hoje'],last_contact=DAY,recorded_attempts=10,
            performance_source='novas',performance={'exact_n':10,'observed':.9})
    c=state('unknown',path=PATH[:-1]+['Desconhecido'],answered_pdf=10)
    model=overview([a,b,c]); indexed={r['topic_id']:r for r in model['rows']}
    assert indexed['old']['days_without_contact']==28 and indexed['old']['stale']
    assert indexed['today']['days_without_contact']==0 and not indexed['today']['stale']
    assert indexed['unknown']['days_without_contact'] is None
    assert {r['topic_id'] for r in attention_filter(model['rows'],'Sem contato')}=={'old','unknown'}


def test_existing_review_order_and_search_are_preserved_without_input_mutation():
    a=state('due',path=PATH[:-1]+['Revisão'],review_committed=True,next_review='2026-10-28',score=.01)
    b=state('high',path=PATH[:-1]+['Hipertensão'],score=100)
    view={'states':[b,a],'profile':{}}; tables=[dataset()]
    before=deepcopy((view,tables)); model=attention_overview(view,tables,DAY)
    assert [r['topic_id'] for r in model['rows']]==['due','high']
    assert [r['topic_id'] for r in attention_filter(model['rows'],'Todos','hipertensao')]==['high']
    assert before==(view,tables)


def test_cards_contact_does_not_claim_no_study_when_no_questions_are_known():
    row=overview([state(status='diagnostico',studied_cards=5,last_contact='2026-10-28')])['rows'][0]
    assert row['never_practiced'] and not row['never_seen']
    assert 'Sem questões registradas' in row['reason']


def test_small_sample_uses_existing_minimum_block_and_does_not_claim_mastery():
    row=overview([state(status='revisao',recorded_attempts=1,last_contact=DAY,minimum_block=10,
                        performance_source='novas',performance={'exact_n':1,'observed':1,'reported_n':1})])['rows'][0]
    assert row['attention'] and 'Amostra pequena' in row['reason']
    assert row['accuracy']['n']==1 and row['accuracy']['rate']==1
