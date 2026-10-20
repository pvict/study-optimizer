import pytest
from osler.adaptive_planning import incidence_weights,topic_states
from osler.study_models import AdaptiveProfile,StudyEntry
from osler.adaptive_service import AdaptiveService
from test_adaptive_planning import topic,session
from test_assessments import setup_assessment


def test_group_keeps_its_full_incidence_when_children_are_replaced():
    group={**topic('Group'),'path':['Area','Group'],'rollup':True}
    other={**topic('Other'),'path':['Area','Other']}
    rows=[{'path':['Area','Group'],'value':90},{'path':['Area','Group','A'],'value':89},{'path':['Area','Group','Tiny'],'value':1},{'path':['Area','Other'],'value':10}]
    data=[{'id':1,'institutions':['A'],'observed_date':'2026-10-15','unit':'questoes','rows':rows}]
    assert incidence_weights([group,other],data,{},'2026-10-15')['weights']['Group']==pytest.approx(.9)


def test_reading_contact_does_not_renew_expired_mastery_evidence():
    event=session(day='2026-10-01',n=40,correct=40)
    event['entry']['confident_correct']=40
    state=topic_states([topic()],[event],[],{},'2026-10-15',AdaptiveProfile(),[(['Área','Tema'],'2026-10-15')])[0]
    assert state['learning_state']=='alerta'
    assert state['next_review']=='2026-10-08'


def test_weak_repeated_results_prevent_mastery_without_pooling_denominators():
    a=session(n=40,correct=40)
    a['entry']['confident_correct']=40
    b=session(mode='repetidas',n=20,correct=0)
    b['entry']['confident_correct']=0
    state=topic_states([topic()],[a,b],[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['learning_state']=='alerta'
    assert state['confidence']['exact_n']==40


def test_extras_cannot_schedule_overlapping_parent_and_child(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    topics,_=s.catalog('2026-10-15',include_parents=True)
    pair=next((a,b) for a in topics for b in topics if not a['is_leaf'] and b['is_leaf'] and len(a['path'])<len(b['path']) and b['path'][:len(a['path'])]==a['path'])
    with pytest.raises(ValueError,match='específico|grupo'): s.add_topic('2026-10-15',pair[0]['topic_id'],1,0)
    s.add_topic('2026-10-15',pair[1]['topic_id'],1,0)


def test_general_parent_with_direct_study_keeps_catalog_and_confidence(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    parents,_=s.catalog('2026-10-15',include_parents=True)
    parent=next(t for t in parents if not t['is_leaf'])
    s.save_entry(StudyEntry(parent['path'],'2026-10-15',40,40,confident_correct=40),'parent')
    state=next(t for t in s.overview('2026-10-15')['states'] if t['topic_id']==parent['topic_id'])
    assert state['confidence']['exact_n']==40


def test_low_pdf_accuracy_is_a_provisional_alert_without_invented_confidence():
    t=topic(answered=44)
    t['pdf_accuracy']['value']=50
    state=topic_states([t],[],[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['learning_state']=='alerta'
    assert state['confidence']['exact_n']==0
    assert state['low_accuracy']
