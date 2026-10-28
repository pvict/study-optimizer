from copy import deepcopy
import pytest
from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from osler.study_models import AdaptiveProfile,StudyEntry
from test_planner_supply import supplied

DAY='2026-10-15'


def setup_plan(tmp_path,monkeypatch,available=10,done=10,new_share=1):
    service=AdaptiveService(Repository(tmp_path))
    topics=[{**supplied(name,available=available),'is_leaf':True} for name in ('A','B','C')]
    monkeypatch.setattr(service,'catalog',lambda *a,**kw:(deepcopy(topics),{'qbank':None,'flashcards':None}))
    service.store.save_profile(AdaptiveProfile(max_questions=60,max_topics=3,new_share=new_share),0)
    service.agenda.append({'kind':'reschedule.apply','created_day':DAY,'cutoff':0,'selected':['A'],
        'mode':'balanced','start':DAY,'days':7,
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':DAY,'original_due':'2026-10-13',
                 'questions':20,'new_topic':True}]},service.agenda.token())
    if done:service.save_entry(StudyEntry(topics[0]['path'],DAY,done,done),'actual')
    return service,topics


def test_optional_completion_persists_without_fake_answers_or_changed_review(tmp_path,monkeypatch):
    s,topics=setup_plan(tmp_path,monkeypatch);before=s.overview(DAY);events=s.store.events()
    state=next(t for t in before['states'] if t['topic_id']=='A')
    peers={i['topic_id']:i['questions'] for i in before['plan']['items'] if i['topic_id']!='A'}
    decision=s.skip_planner_complement(DAY,'A',before['planning_token'])
    after=s.overview(DAY)
    assert {i['topic_id']:i['questions'] for i in after['plan']['items']}==peers
    assert after['plan']['done_questions']==10 and after['plan']['target_questions']==60
    assert after['plan']['questions']==sum(peers.values())
    assert after['plan']['planner_completions'][0]['id']==decision
    assert after['plan']['planner_completions'][0]['skipped_questions']==10
    updated=next(t for t in after['states'] if t['topic_id']=='A')
    for key in ('performance','review_interval_days','next_review','learning_state','pending_reviews'):
        assert updated[key]==state[key]
    assert s.store.events()==events
    s.remember_day(after)
    reloaded=AdaptiveService(s.repository);monkeypatch.setattr(reloaded,'catalog',s.catalog)
    assert not any(i['topic_id']=='A' for i in reloaded.overview(DAY)['plan']['items'])
    assert not any(r['topic_id']=='A' for r in reloaded.agenda.active(s.store.active('2026-10-16'),'2026-10-16')['rows'])
    calendar=s.calendar(30)
    assert not any(i['topic_id']=='A' for i in calendar[0]['items'])
    future=next(p['date'] for p in calendar[1:] if any(i['topic_id']=='A' for i in p['items']))
    assert future>=state['next_review'] and future>DAY


@pytest.mark.parametrize('available,done',[(10,9),(0,0),(30,10)])
def test_completion_rejects_unfinished_empty_or_sufficient_planner(tmp_path,monkeypatch,available,done):
    s,_=setup_plan(tmp_path,monkeypatch,available,done)
    with pytest.raises(ValueError):s.skip_planner_complement(DAY,'A',s.agenda.token())


def test_decision_can_be_undone_and_correction_or_void_restores_real_remainder(tmp_path,monkeypatch):
    s,topics=setup_plan(tmp_path,monkeypatch)
    decision=s.skip_planner_complement(DAY,'A',s.agenda.token())
    s.restore_planner_complement(DAY,decision,s.agenda.token())
    assert any(i['topic_id']=='A' for i in s.overview(DAY)['plan']['items'])
    again=s.skip_planner_complement(DAY,'A',s.agenda.token())
    assert again!=decision
    assert not any(i['topic_id']=='A' for i in s.overview(DAY)['plan']['items'])
    s.save_entry(StudyEntry(topics[0]['path'],DAY,4,3),'actual',1)
    item=next(i for i in s.overview(DAY)['plan']['items'] if i['topic_id']=='A')
    assert item['planner_supply']['planner_remaining']==6
    assert not s.overview(DAY)['plan']['planner_completions']
    s.store.void('actual',2)
    assert next(i for i in s.overview(DAY)['plan']['items'] if i['topic_id']=='A')['planner_supply']['completed']==0


def test_stale_date_token_and_linked_due_lots_cannot_be_dismissed(tmp_path,monkeypatch):
    s,topics=setup_plan(tmp_path,monkeypatch)
    token=s.agenda.token();s.remember_day(s.overview(DAY))
    with pytest.raises(ValueError,match='mudou'):s.skip_planner_complement(DAY,'A',token)
    with pytest.raises(ValueError):s.skip_planner_complement('2026-10-14','A',s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],'2026-10-08',10,8,confident_correct=0),'due-lot')
    with pytest.raises(ValueError):s.skip_planner_complement(DAY,'A',s.agenda.token())
    assert s.overview(DAY)['review_queue']


def test_new_reservations_and_future_returns_survive_completion(tmp_path,monkeypatch):
    s,topics=setup_plan(tmp_path,monkeypatch)
    s.save_entry(StudyEntry(topics[0]['path'],DAY,10,8,confident_correct=7),'actual',1)
    s.skip_planner_complement(DAY,'A',s.agenda.token())
    assert any(q['session_id']=='actual' for q in s.overview(DAY)['review_queue'])
    s.agenda.append({'kind':'reschedule.apply','created_day':DAY,'cutoff':1,'selected':['A'],
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':'2026-10-18','original_due':'2026-10-18',
                 'questions':20,'new_topic':False}]},s.agenda.token())
    assert any(r['topic_id']=='A' for r in s.agenda.active(s.store.active('2026-10-18'),'2026-10-18')['rows'])


def test_user_can_add_an_extra_review_after_dismissing_complement(tmp_path,monkeypatch):
    s,_=setup_plan(tmp_path,monkeypatch)
    s.skip_planner_complement(DAY,'A',s.agenda.token())
    s.add_topic(DAY,'A',10,0)
    assert any(i['topic_id']=='A' and i['added_by_user'] for i in s.overview(DAY)['plan']['items'])


def test_answering_the_complement_later_does_not_keep_a_fictitious_dispensed_count(tmp_path,monkeypatch):
    s,topics=setup_plan(tmp_path,monkeypatch)
    s.skip_planner_complement(DAY,'A',s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],DAY,10,9),'complement')
    assert s.overview(DAY)['plan']['done_questions']==20
    assert not s.overview(DAY)['plan']['planner_completions']


def test_new_reservation_for_today_is_not_removed_by_an_older_choice(tmp_path,monkeypatch):
    s,topics=setup_plan(tmp_path,monkeypatch)
    s.skip_planner_complement(DAY,'A',s.agenda.token())
    s.agenda.append({'kind':'reschedule.apply','created_day':DAY,'cutoff':0,'selected':['A'],
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':DAY,'original_due':DAY,
                 'questions':30,'new_topic':False}]},s.agenda.token())
    view=s.overview(DAY)
    assert next(i for i in view['plan']['items'] if i['topic_id']=='A')['questions']==20
    assert not view['plan']['planner_completions']


def test_resumed_planner_uses_the_same_prior_day_credits_and_revalidates_corrections(tmp_path,monkeypatch):
    s,topics=setup_plan(tmp_path,monkeypatch,done=0,new_share=.5)
    s.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-14','cutoff':0,'selected':['A'],
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':DAY,'original_due':'2026-10-14',
                 'questions':20,'new_topic':False}]},s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],'2026-10-14',10,8),'yesterday')
    s.skip_planner_complement(DAY,'A',s.agenda.token())
    assert not any(i['topic_id']=='A' for i in s.overview(DAY)['plan']['items'])
    assert s.overview(DAY)['plan']['planner_completions']
    s.save_entry(StudyEntry(topics[0]['path'],'2026-10-14',4,3),'yesterday',1)
    assert any(i['topic_id']=='A' for i in s.overview(DAY)['plan']['items'])
    assert not s.overview(DAY)['plan']['planner_completions']
