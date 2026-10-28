from osler.topic_catalog import planning_frontier
from osler.topic_spacing import spacing_state, learning_state
from osler.adaptive_planning import allocate_day, topic_states
from osler.study_models import AdaptiveProfile
from test_adaptive_planning import topic,session


def test_small_leaf_keeps_specific_identity_without_parent_child_overlap():
    topics=[{**topic('Retino',total=1),'path':['Pediatria','Oncologia','Retino'],'is_leaf':True},
            {**topic('Outro',total=100),'path':['Pediatria','Oncologia','Outro'],'is_leaf':True},
            {**topic('Oncologia',total=376),'path':['Pediatria','Oncologia'],'is_leaf':False}]
    frontier=planning_frontier(topics,10)
    assert [t['topic_id'] for t in frontier]==['Retino','Outro']
    assert all(t['is_leaf'] and not t['rollup'] for t in frontier)


def test_count_plan_keeps_daily_quantity_and_limits_small_blocks_to_small_banks():
    p=AdaptiveProfile()
    states=topic_states([topic('Tiny',total=1),topic('A'),topic('B'),topic('C')],[],[],{},'2026-10-15',p)
    result=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=60)
    assert result['questions']==60
    assert all(i['questions']>=10 or i['total']<10 and i['questions']==i['total'] for i in result['items'])
    assert next(i for i in result['items'] if i['topic_id']=='Tiny')['questions']==1


def test_spacing_grows_on_confident_success_and_resets_after_errors():
    def e(day,n=20,correct=20,confidence=20):
        return {**session(day=day,n=n,correct=correct)['entry'],'confident_correct':confidence}
    first=spacing_state([e('2026-09-01')],AdaptiveProfile(),'2026-10-15')
    second=spacing_state([e('2026-09-01'),e('2026-09-08')],AdaptiveProfile(),'2026-10-15')
    bad=spacing_state([e('2026-09-01'),e('2026-09-08'),e('2026-09-22',correct=10,confidence=8)],AdaptiveProfile(),'2026-10-15')
    assert first['interval']==7 and second['interval']==14
    assert bad['interval']==3 and bad['next_due']=='2026-09-25'
    assert spacing_state([e('2026-10-01',confidence=None)],AdaptiveProfile(),'2026-10-15')['interval']<=7


def test_mastery_requires_confidence_and_sample_not_pdf_or_guesses():
    p=AdaptiveProfile()
    base={'seen':True,'n':40,'rate':.95,'lower':.84,'source':'novas','overdue':False,'pending_due':0,'raw_rate':.95}
    assert learning_state(base,p)=='dominado'
    assert learning_state({**base,'n':0,'rate':None},p)=='aprendendo'
    assert learning_state({**base,'rate':.4},p)=='alerta'
    assert learning_state({**base,'seen':False},p)=='alerta'
