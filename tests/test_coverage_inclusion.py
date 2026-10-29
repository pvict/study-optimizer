from ui_actions import confirm_action
from copy import deepcopy
import pytest
from osler.adaptive_planning import topic_states,allocate_day
from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile
from test_adaptive_planning import topic,session


@pytest.mark.parametrize('strategy',['legacy_v1','balanced_v2'])
@pytest.mark.parametrize('mode',['fixed','adaptive'])
@pytest.mark.parametrize('total',[1,9])
def test_small_positive_bank_receives_real_slot_without_inventing_questions(total,strategy,mode):
    p=AdaptiveProfile(max_questions=120,max_topics=6,new_share=.5,review_strategy=strategy,workload_mode=mode)
    states=topic_states([topic('small',total=total)],[],[],{},'2026-10-15',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=120)
    assert [(i['topic_id'],i['questions']) for i in plan['items']]==[('small',total)]
    assert plan['done_questions']==0
    calendar=forecast_calendar(states,p,'2026-10-15',30,[],{},next_contact_only=True)
    assert [i['questions'] for d in calendar for i in d['items']]==[total]
    assert states[0]['performance']['exact_n']==0


def test_short_bank_still_obeys_priority_rest_and_normal_bank_minimum():
    p=AdaptiveProfile(max_questions=40,max_topics=1,new_share=1,workload_mode='adaptive',review_strategy='balanced_v2')
    topics=[topic('low',total=1),topic('high',total=9),topic('normal',total=100)]
    data=[{'id':1,'institutions':['X'],'unit':'questoes','observed_date':'2026-10-15',
           'rows':[{'path':t['path'],'value':n} for t,n in zip(topics,[1,100,10])]}]
    states=topic_states(topics,[],data,{},'2026-10-15',p)
    days=forecast_calendar(states,p,'2026-10-15',30,[],{'2026-10-15':{'questions':40,'kind':'descanso','extra_topics':[]}},next_contact_only=True)
    assert not days[0]['items']
    contacts=[i for d in days for i in d['items']]
    assert contacts[0]['topic_id']=='high'
    assert {i['topic_id'] for i in contacts}=={'low','high','normal'}
    assert next(i for i in contacts if i['topic_id']=='normal')['questions']>=p.min_block


def test_all_mixed_size_topics_have_actual_dates_when_calendar_has_capacity():
    p=AdaptiveProfile(max_questions=120,max_topics=6,new_share=.5,workload_mode='adaptive',review_strategy='balanced_v2')
    topics=[topic('T'+str(i),total=1+i%70) for i in range(1480)]
    states=topic_states(topics,[],[],{},'2026-10-15',p);before=deepcopy(states)
    days=forecast_calendar(states,p,'2026-10-15',412,[],{},next_contact_only=True)
    contacts={i['topic_id'] for d in days for i in d['items']}
    assert len(contacts)==len(topics)
    assert all(d['questions']<=120 and len(d['items'])<=6 for d in days)
    assert states==before


def test_specific_theme_with_own_content_is_not_lost_behind_its_one_question_child():
    from osler.topic_catalog import planning_frontier
    area={**topic('area',total=486),'path':['Área'],'is_leaf':False}
    group={**topic('group',total=486),'path':['Área','Medicina Legal'],'is_leaf':False}
    parent={**topic('parent',total=486),'path':['Área','Medicina Legal','Saúde do Trabalhador'],'is_leaf':False}
    child={**topic('child',total=1),'path':parent['path']+['Segurança do Trabalhador'],'is_leaf':True}
    from osler.topic_catalog import mark_practice_units
    marked=mark_practice_units([area,group,parent,child])
    frontier=planning_frontier(marked)
    assert {t['topic_id'] for t in frontier}=={'parent','child'}
    own=next(t for t in frontier if t['topic_id']=='parent')
    assert own['total']==486 and not own['is_leaf']
    assert own['direct_questions']==485 and own['is_practice_unit']
    assert own['non_additive'] and own['evidence_scope']=='inclusive_parent'


def test_catalog_registration_and_statistics_keep_specific_parent_source_and_child_separate(tmp_path,monkeypatch):
    from osler.storage import Repository
    from osler.adaptive_service import AdaptiveService
    from osler.models import Report,TopicRecord,Percentage,stable_topic_id
    from streamlit.testing.v1 import AppTest
    parent_path=['Preventiva & Social','Medicina Legal','Saúde do Trabalhador']
    paths=[parent_path[:1],parent_path[:2],parent_path,parent_path+['Segurança do Trabalhador']]
    records=[TopicRecord(stable_topic_id(path),path,len(path)-1,total,0,Percentage(0,'=','0%'),1,'',48.,100.,is_leaf=i==3)
             for i,(path,total) in enumerate(zip(paths,[486,486,486,1]))]
    q=Report('sintetico.pdf','a'*64,'qbank','todos','2026-10-14',1,{}, {},records)
    s=AdaptiveService(Repository(tmp_path))
    monkeypatch.setattr(s.guide,'_report',lambda kind,*a:q if kind=='qbank' else None)
    catalog,_=s.catalog('2026-10-15')
    assert {t['topic_id'] for t in catalog}=={r.topic_id for r in records[2:]}
    app=AppTest.from_string('''
import streamlit as st
from osler.adaptive_ui import _register
_register(st.session_state.service)
''',default_timeout=60)
    app.session_state['service']=s
    app.session_state['adaptive_topic']=records[2].topic_id
    app.session_state['study_n']=20
    app.run()
    assert not app.exception and any(h.value=='Saúde do Trabalhador' for h in app.subheader)
    app.number_input(key='study_correct').set_value(18)
    app.number_input(key='study_confident').set_value(16)
    app.number_input(key='study_cards_created').set_value(2)
    confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
    assert not app.exception
    view=s.overview('2026-10-15')
    parent=next(t for t in view['states'] if t['topic_id']==records[2].topic_id)
    child=next(t for t in view['states'] if t['topic_id']==records[3].topic_id)
    assert parent['performance']['exact_n']==20 and child['performance']['exact_n']==0
    assert parent['total']==486 and child['total']==1
    assert not parent.get('historical_aggregate')
    from osler.study_errors import ErrorStore,StudyError
    assert ErrorStore(s.repository,catalog=s.catalog).save(StudyError(parent_path,'2026-10-15','chute','Conceito específico'))
    from osler.mock_exams import _entries,MockExam
    exam=MockExam(day='2026-10-15',questions=20,correct=18,name='Teste',unseen_questions=True,
                  topics=[{'path':parent_path,'questions':20,'correct':18}])
    assert _entries(s,'mock-test',exam)[0][1].path==parent_path
    from osler.study_evolution import evolution_snapshot
    snap=evolution_snapshot(view['states'],view['sessions'],[],'2026-10-15')
    assert snap['total_topics']==2 and snap['actual_attempts']==20
    from osler.study_swaps import replacement_candidates
    original={**parent,'topic_id':'other','questions':10}
    assert parent['topic_id'] in {t['topic_id'] for t in replacement_candidates(original,[parent],set(),'2026-10-15')['manual']}
    f=Report('cards-sintetico.pdf','b'*64,'flashcards','todos','2026-10-14',1,{}, {},records)
    monkeypatch.setattr(s.guide,'_report',lambda kind,*a:q if kind=='qbank' else f)
    ordinary=next(t for t in s.catalog('2026-10-15')[0] if t['topic_id']==parent['topic_id'])
    complete=next(t for t in s.catalog('2026-10-15',include_parents=True)[0] if t['topic_id']==parent['topic_id'])
    assert ordinary['studied_cards']==complete['studied_cards']==0


def test_inclusive_parent_is_visible_without_adding_its_snapshot_to_child_totals():
    from osler.study_evolution import evolution_snapshot
    from test_evolution import state
    parent={**state('parent',30),'is_leaf':False,'is_practice_unit':True,'non_additive':True}
    child=state('child',10)
    snapshot=evolution_snapshot([parent,child],[],[],'2026-10-15')
    assert snapshot['total_topics']==2 and snapshot['covered_now']==2
    assert snapshot['imported_unique']==10 and snapshot['imported_safety']['questions_per_topic_sum']==10
    assert snapshot['non_additive_topics']==1
