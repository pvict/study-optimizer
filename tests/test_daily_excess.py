from dataclasses import replace
import pytest
from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from osler.study_models import AdaptiveProfile,StudyEntry
from test_adaptive_planning import topic


def configured(tmp_path,monkeypatch,mode='adaptive'):
    s=AdaptiveService(Repository(tmp_path))
    topics=[{**topic(name),'is_leaf':True} for name in ['A','B','C','D','E','F']]
    monkeypatch.setattr(s,'catalog',lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None}))
    s.store.save_profile(AdaptiveProfile(max_questions=120,max_topics=6,new_share=1,workload_mode=mode),0)
    return s


@pytest.mark.parametrize('mode',['fixed','adaptive'])
def test_two_extra_answers_keep_every_other_proposed_topic(tmp_path,monkeypatch,mode):
    s=configured(tmp_path,monkeypatch,mode); before=s.overview('2026-10-15'); s.remember_day(before)
    first=before['plan']['items'][0]; peers={i['topic_id']:i['questions'] for i in before['plan']['items'][1:]}
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']+2),'first')
    after=s.overview('2026-10-15')['plan']
    assert {i['topic_id']:i['questions'] for i in after['items']}==peers
    assert after['done_questions']==first['questions']+2
    assert after['excess_done_questions']==2
    assert after['target_questions']==120
    assert after['questions']+after['done_questions']==122
    actual=next(t for t in s.overview('2026-10-15')['states'] if t['topic_id']==first['topic_id'])
    assert actual['performance']['exact_n']==first['questions']+2
    assert actual['performance']['exact_correct']==first['questions']+2


def test_excess_and_pending_blocks_survive_reload_and_correction(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); view=s.overview('2026-10-15'); s.remember_day(view)
    first=view['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']),'first')
    after=s.overview('2026-10-15'); peers={i['topic_id']:i['questions'] for i in after['plan']['items']}; s.remember_day(after)
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+4,first['questions']),'first',1)
    corrected=s.overview('2026-10-15')['plan']
    assert corrected['excess_done_questions']==4
    assert {i['topic_id']:i['questions'] for i in corrected['items']}==peers
    s.store.void('first',2)
    assert s.overview('2026-10-15')['plan']['excess_done_questions']==0


def test_extra_answers_do_not_change_tomorrows_target_or_create_completed_study(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); view=s.overview('2026-10-15'); s.remember_day(view)
    first=view['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']),'first')
    tomorrow=s.overview('2026-10-16')['plan']
    assert tomorrow['target_questions']==120 and tomorrow['done_questions']==0
    assert len(s.store.active('2026-10-16'))==1


def test_explicit_rest_still_cancels_remaining_blocks(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); view=s.overview('2026-10-15'); s.remember_day(view)
    first=view['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']),'first')
    s.configure_day('2026-10-15',120,'descanso',0)
    assert s.overview('2026-10-15')['plan']['items']==[]


def test_legacy_proposal_without_new_metadata_is_still_understood(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); view=s.overview('2026-10-15')
    s.store.save_plan({'kind':'daily_schedule','plan':{'date':view['date'],'items':[
        {'topic_id':i['topic_id'],'path':i['path'],'questions':i['questions']} for i in view['plan']['items']]}})
    first=view['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']),'first')
    assert s.overview('2026-10-15')['plan']['excess_done_questions']==2


def test_partial_block_then_two_extra_answers_preserves_peers(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); initial=s.overview('2026-10-15'); s.remember_day(initial)
    first=initial['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',10,9),'part-one')
    # A proposal for the remaining ten, as a user would see before completing it.
    remaining={**initial,'sessions':s.store.active('2026-10-15'),'plan':{**initial['plan'],'items':[
        {**i,'questions':i['questions']-10 if i['topic_id']==first['topic_id'] else i['questions']} for i in initial['plan']['items']]}}
    remaining.pop('planning_token',None)
    s.remember_day(remaining)
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']-10+2,first['questions']-10),'part-two')
    after=s.overview('2026-10-15')['plan']
    assert after['excess_done_questions']==2
    assert {i['topic_id']:i['questions'] for i in after['items']}=={i['topic_id']:i['questions'] for i in initial['plan']['items'][1:]}


def test_no_proposal_does_not_invent_original_dose(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); view=s.overview('2026-10-15'); first=view['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']),'first')
    assert s.overview('2026-10-15')['plan']['excess_done_questions']==0


def test_stale_view_cannot_be_saved_as_if_it_preceded_new_study(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); view=s.overview('2026-10-15'); first=view['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',22,20),'new')
    with pytest.raises(ValueError): s.remember_day(view)


def test_correction_of_earlier_partial_does_not_consume_peer_blocks(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); initial=s.overview('2026-10-15'); s.remember_day(initial)
    first=initial['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',10,9),'one')
    partial={**initial,'sessions':s.store.active('2026-10-15'),'plan':{**initial['plan'],'items':[
        {**i,'questions':10 if i['topic_id']==first['topic_id'] else i['questions']} for i in initial['plan']['items']]}}
    partial.pop('planning_token',None); s.remember_day(partial)
    s.save_entry(StudyEntry(first['path'],'2026-10-15',12,10),'two')
    s.save_entry(StudyEntry(first['path'],'2026-10-15',15,13),'one',1)
    after=s.overview('2026-10-15')['plan']
    assert after['excess_done_questions']==7
    assert {i['topic_id']:i['questions'] for i in after['items']}=={i['topic_id']:i['questions'] for i in initial['plan']['items'][1:]}


def test_explicit_review_only_programming_overrides_old_new_topic_proposal(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); view=s.overview('2026-10-15'); s.remember_day(view)
    first=view['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',22,22),'first')
    s.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-15','cutoff':1,'selected':[],
        'rows':[],'overrides':{'2026-10-15':{'mode':'reviews'}}},s.agenda.token())
    plan=s.overview('2026-10-15')['plan']
    assert plan['distribution']['target_new']==0 and plan['distribution']['planned_new']==0


def test_manual_swap_of_peer_still_wins_after_excess(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch)
    topics=[{**topic(name),'is_leaf':True} for name in 'ABCDEFGH']
    monkeypatch.setattr(s,'catalog',lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None}))
    before=s.overview('2026-10-15'); s.remember_day(before); first=before['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',first['questions']+2,first['questions']),'first')
    peer=s.overview('2026-10-15')['plan']['items'][0]
    options=s.swap_options('2026-10-15',peer['topic_id'])
    target=next(t for t in topics if t['topic_id'] not in {i['topic_id'] for i in before['plan']['items']})
    s.swap_topic('2026-10-15',peer['topic_id'],target['topic_id'],options['token'],'manual')
    after=s.overview('2026-10-15')['plan']
    ids={i['topic_id'] for i in after['items']}
    assert target['topic_id'] in ids and peer['topic_id'] not in ids
    assert len(ids)==len(before['plan']['items'])-1
    assert after['excess_done_questions']==2


def test_review_method_change_does_not_erase_unfinished_daily_promises(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); initial=s.overview('2026-10-15'); s.remember_day(initial)
    first=initial['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',22,22),'first')
    record=s.store.profile()
    s.store.save_profile(replace(AdaptiveProfile(**record['configured_profile']),review_strategy='balanced_v2'),record['id'])
    after=s.overview('2026-10-15')['plan']
    assert {i['topic_id']:i['questions'] for i in after['items']}=={i['topic_id']:i['questions'] for i in initial['plan']['items'][1:]}


def test_new_smaller_daily_goal_can_explicitly_reduce_the_proposal(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch); initial=s.overview('2026-10-15'); s.remember_day(initial)
    first=initial['plan']['items'][0]
    s.save_entry(StudyEntry(first['path'],'2026-10-15',22,22),'first')
    s.configure_day('2026-10-15',80,'normal',0)
    after=s.overview('2026-10-15')['plan']
    assert after['target_questions']==80 and after['questions']<=60
