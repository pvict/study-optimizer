import pytest
from osler.error_cards import parse_error_cards, plan_error_cards


def node(name,n,indent=0,branch=None):
    icon='' if branch is None else '<svg class="lucide-chevron-'+branch+'"></svg>'
    return f'<div class="TreeNode-test" style="margin-left: {indent}px;"><span class="Label-test">{name}</span>{icon}<p class="StatInfo-test">{n}</p></div>'


def test_hierarchy_counts_only_non_overlapping_terminal_cards():
    v=parse_error_cards('<div>'+node('Área','1.000',branch='down')+node('A',600,20)+node('Grupo',400,20,'down')+node('B',400,40)+'</div>')
    assert v['total']==1000 and len(v['nodes'])==4
    assert sum(t['count'] for t in v['topics'])==1000
    assert v['topics'][1]['path']==['Área','Grupo','B']


def test_collapsed_group_and_parent_residue_are_not_specific_topics():
    v=parse_error_cards('<div>'+node('Área',100,branch='down')+node('A',50,20)+node('Recolhido',30,20,'right')+'</div>')
    assert v['total']==100 and v['schedulable']==50 and v['unallocated']==50
    assert len(v['topics'])==1 and len(v['unresolved'])==2


def test_distinct_source_spellings_of_same_topic_preserve_counts_and_aliases():
    v=parse_error_cards(node('Trauma',19,branch='down')+node('Trauma de face',5,20)+node('Trauma de Face',14,20))
    assert len(v['topics'])==1 and v['topics'][0]['count']==19
    assert len(v['topics'][0]['source_paths'])==2 and v['total']==19


def test_oversized_deck_is_not_silently_split_or_forced_into_small_day():
    v=plan_error_cards([{'topic_id':'a','path':['A'],'count':500}],{},[],'2026-10-24',200)
    assert v[0]['planned']==0 and v[0]['oversized']


@pytest.mark.parametrize('html',[
    node('A',2)[:-6], node('A','2,5'), node('A',2)+node('A',2),
    node('Área',1,branch='down')+node('A',2,20), node('A',2,20), '<script>alert(1)</script>',
])
def test_invalid_or_truncated_html_is_refused(html):
    with pytest.raises(ValueError):parse_error_cards(html)


def test_plan_limits_and_does_not_confuse_confidence_with_accuracy():
    topics=[{'topic_id':str(i),'path':['Área',str(i)],'count':100} for i in range(6)]
    states=[{'topic_id':'0','incidence_known':True,'incidence_strength':1,'performance':{'exact_n':20,'exact_correct':6},'confidence':{'observed':1}}]
    v=plan_error_cards(topics,{},states,'2026-10-24',200)
    assert sum(t['planned'] for t in v)==200 and all(t['planned'] in (0,t['remaining']) for t in v)
    assert v[0]['topic_id']=='0' and v[0]['accuracy']==pytest.approx(7/22)
    assert any(t['accuracy'] is None for t in v)
    assert not any(t['planned'] for t in plan_error_cards(topics,{},states,'2026-10-24',0))


def test_whole_decks_may_cross_the_reference_by_up_to_ten_percent():
    sizes=[72,22,17,35,35,27,13,61]
    topics=[{'topic_id':str(i),'path':[str(i)],'count':n} for i,n in enumerate(sizes)]
    states=[{'topic_id':str(i),'incidence_known':True,'incidence_strength':1-i/20} for i in range(len(sizes))]
    v=plan_error_cards(topics,{},states,'2026-10-24',200)
    assert [t['planned'] for t in v]==[72,22,17,35,35,27,0,0]
    assert sum(t['planned'] for t in v)==208


def test_whole_deck_does_not_use_a_tiny_budget_fragment():
    topics=[{'topic_id':'a','path':['A'],'count':153},{'topic_id':'b','path':['B'],'count':100}]
    v=plan_error_cards(topics,{},[],'2026-10-24',200)
    assert [t['planned'] for t in v]==[153,0]


def test_partial_work_is_real_and_the_same_deck_is_finished_first():
    topics=[{'topic_id':'a','path':['A'],'count':72},{'topic_id':'b','path':['B'],'count':100}]
    v=plan_error_cards(topics,{'a':{'covered':40,'last_day':'2026-10-24'}},[],'2026-10-24',160,reference_budget=200)
    assert v[0]['topic_id']=='a' and v[0]['planned']==32
    assert all(t['planned'] in (0,t['remaining']) for t in v)


def test_near_goal_keeps_the_margin_from_the_original_daily_reference():
    v=plan_error_cards([{'topic_id':'a','path':['A'],'count':20}],{},[],'2026-10-24',10,reference_budget=200)
    assert v[0]['planned']==20


def test_finish_started_deck_inside_margin_after_reaching_daily_reference():
    topics=[{'topic_id':'a','path':['A'],'count':220}]
    progress={'a':{'covered':200,'last_day':'2026-10-24'}}
    assert plan_error_cards(topics,progress,[],'2026-10-24',0,reference_budget=200,completed_today=200)[0]['planned']==20
    assert plan_error_cards(topics,progress,[],'2026-10-24',0,reference_budget=200,completed_today=205)[0]['planned']==0
