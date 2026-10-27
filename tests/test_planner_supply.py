from conftest import open_view
from copy import deepcopy
import pytest

from osler.adaptive_planning import topic_states,allocate_day
from osler.study_models import AdaptiveProfile,StudyEntry
from osler.study_replanning import collect_backlog
from osler.planner_snapshot import planner_supply
from test_adaptive_planning import topic,session


def supplied(name='A',available=10):
    return {**topic(name,total=40),'planner_snapshot':{
        'observed_date':'2026-10-14','unique_questions':0,'available_questions':available,
        'confident_accuracy_pct':None,'pending_reviews':None,'last_contact':None}}


@pytest.mark.parametrize('available,required,done,left',[(10,20,10,10),(6,15,6,9),(10,20,5,15),(0,20,0,20)])
def test_supply_explains_complement_without_reducing_recommendation(available,required,done,left):
    t=supplied(available=available);before=deepcopy(t)
    info=planner_supply(t,required,done,'2026-10-15')
    assert info['recommended']==required and info['planner_total']==available
    assert info['remaining']==left and info['external_part']==required-available
    assert info['external_only']==(done>=available)
    assert t==before


def test_unknown_future_and_sufficient_supply_are_not_shortages():
    assert planner_supply(topic(),20,0,'2026-10-15') is None
    t=supplied();t['planner_snapshot']['observed_date']='2026-10-16'
    assert planner_supply(t,20,0,'2026-10-15') is None
    assert planner_supply(supplied(available=40),20,5,'2026-10-15')['external_part']==0


def test_existing_recovery_keeps_complement_registrable_without_claiming_more_study():
    p=AdaptiveProfile(max_questions=120,new_share=1)
    e={**session('A',n=10,correct=7),'id':2,'session_id':'actual','first_event_id':2}
    states=topic_states([supplied()], [e],[],{},'2026-10-15',p)
    booking={'topic_id':'A','date':'2026-10-15','original_due':'2026-10-13',
             'questions':20,'remaining':10,'cutoff':1}
    plan=allocate_day(states,p,None,'normal',[e],'2026-10-15',question_target=120,reservations=[booking])
    item=next(i for i in plan['items'] if i['topic_id']=='A')
    assert item['questions']==10 and plan['done_questions']==10
    assert item['planner_supply']['recommended']==20
    assert item['planner_supply']['external_only']
    assert states[0]['performance']['exact_n']==10


def test_only_unfinished_planner_portion_becomes_missed_plan_debt():
    p=AdaptiveProfile();t=supplied();states=topic_states([t],[],[],{},'2026-10-15',p)
    saved=[{'id':1,'plan':{'date':'2026-10-14','items':[{'path':t['path'],'questions':20}]}}]
    done=[session('A',day='2026-10-14',n=10,correct=7)]
    assert not collect_backlog(states,done,saved,'2026-10-15')
    partial=[session('A',day='2026-10-14',n=4,correct=3)]
    rows=collect_backlog(states,partial,saved,'2026-10-15')
    assert rows[0]['missed_questions']==6


def test_small_planner_completion_clears_old_plan_debt_without_mastery():
    t=supplied(available=6);e=session('A',day='2026-10-15',n=6,correct=6)
    states=topic_states([t],[e],[],{},'2026-10-16',AdaptiveProfile())
    saved=[{'id':1,'plan':{'date':'2026-10-14','items':[{'path':t['path'],'questions':15}]}}]
    assert not collect_backlog(states,[e],saved,'2026-10-16')
    assert states[0]['learning_state']!='dominado'
    assert states[0]['performance']['exact_n']==6


def test_supply_does_not_reduce_future_review_or_remove_topic_from_catalog():
    p=AdaptiveProfile(max_questions=120,new_share=1)
    states=topic_states([supplied()],[],[],{},'2026-10-15',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=120)
    assert states[0]['total']==40 and states[0]['recommended_questions']>=20
    assert plan['items'][0]['questions']>=20
    assert plan['items'][0]['planner_supply']['external_part']>0


def test_today_and_calendar_explain_external_complement_without_late_label(tmp_path,monkeypatch,project_root):
    from osler.adaptive_service import AdaptiveService
    from osler.storage import Repository
    from streamlit.testing.v1 import AppTest
    topics=[{**supplied(),'is_leaf':True}]
    monkeypatch.setattr(AdaptiveService,'catalog',lambda *a,**kw:(deepcopy(topics),{'qbank':None,'flashcards':None}))
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    s=AdaptiveService(Repository(tmp_path))
    s.store.save_profile(AdaptiveProfile(max_questions=120,new_share=1),0)
    s.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-15','cutoff':0,'selected':['A'],
        'mode':'balanced','start':'2026-10-15','days':7,
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':'2026-10-15','original_due':'2026-10-13',
                 'questions':20,'new_topic':True}]},s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],'2026-10-15',10,7),'actual')
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    text=' '.join(c.value for c in app.caption)
    assert 'Revisão recomendada: 20' in text and 'Planner: 10' in text
    assert any('banco completo' in c.value and '10' in c.value for c in app.info)
    assert not any('atraso original' in c.value for c in app.caption)
    assert any(b.label=='Registrar complemento' for b in app.button)
    open_view(app,adaptive='Calendário')
    assert not app.exception
    assert any('complemento' in c.value.lower() and 'banco completo' in c.value for c in app.caption)
    assert not any('vencimento original' in c.value for c in app.caption)


def test_correction_completion_and_void_recalculate_complement_without_deleting_history(tmp_path,monkeypatch):
    from osler.adaptive_service import AdaptiveService
    from osler.storage import Repository
    t=supplied();s=AdaptiveService(Repository(tmp_path))
    monkeypatch.setattr(s,'catalog',lambda *a,**kw:([t],{'qbank':None,'flashcards':None}))
    s.store.save_profile(AdaptiveProfile(max_questions=120,new_share=1),0)
    s.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-15','cutoff':0,'selected':['A'],
        'rows':[{'topic_id':'A','path':t['path'],'date':'2026-10-15','original_due':'2026-10-13',
                 'questions':20,'new_topic':True}]},s.agenda.token())
    s.save_entry(StudyEntry(t['path'],'2026-10-15',10,7),'actual')
    assert s.overview('2026-10-15')['plan']['items'][0]['planner_supply']['external_only']
    s.save_entry(StudyEntry(t['path'],'2026-10-15',4,3),'actual',1)
    info=s.overview('2026-10-15')['plan']['items'][0]['planner_supply']
    assert not info['external_only'] and info['planner_remaining']==6
    s.save_entry(StudyEntry(t['path'],'2026-10-15',20,17),'actual',2)
    assert not s.agenda.active(s.store.active('2026-10-15'),'2026-10-15')['rows']
    s.store.void('actual',3)
    assert s.overview('2026-10-15')['plan']['items'][0]['planner_supply']['completed']==0
    assert len(s.store.events())==4


def test_captured_planner_capacity_is_not_replaced_by_a_later_import():
    t=supplied(available=30)
    t['planner_snapshot']['observed_date']='2026-10-16'
    e=session('A',day='2026-10-15',n=6,correct=6)
    states=topic_states([t],[e],[],{},'2026-10-16',AdaptiveProfile())
    old=planner_supply(supplied(available=6),15,0,'2026-10-15')
    saved=[{'id':1,'plan':{'date':'2026-10-14','items':[{'path':t['path'],'questions':15}]}},
           {'id':2,'plan':{'date':'2026-10-15','items':[{'path':t['path'],'questions':15,'planner_supply':old}]}}]
    assert not collect_backlog(states,[e],saved,'2026-10-16')


def test_daily_capture_preserves_documented_capacity(tmp_path,monkeypatch):
    from osler.adaptive_service import AdaptiveService
    from osler.storage import Repository
    t=supplied();s=AdaptiveService(Repository(tmp_path))
    monkeypatch.setattr(s,'catalog',lambda *a,**kw:([t],{'qbank':None,'flashcards':None}))
    s.store.save_profile(AdaptiveProfile(new_share=1),0)
    view=s.overview('2026-10-15');s.remember_day(view)
    saved=s.agenda.daily_plans()[-1]['plan']['items'][0]['planner_supply']
    assert saved==view['plan']['items'][0]['planner_supply']
