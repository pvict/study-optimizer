from dataclasses import replace
import pytest

from osler.adaptive_planning import allocate_day, topic_states
from osler.adaptive_service import AdaptiveService
from osler.study_models import AdaptiveProfile, StudyEntry, StudyDay
from osler.study_storage import StudyStore
from osler.storage import Repository
from test_adaptive_planning import topic, session
from test_assessments import setup_assessment


def test_count_target_is_independent_of_time_and_subtracts_completed_questions():
    p=AdaptiveProfile()
    states=topic_states([topic(total=200)],[],[],{},'2026-10-15',p)
    initial=allocate_day(states,p,15,'normal',[],'2026-10-15',question_target=60)
    after=allocate_day(states,p,15,'normal',[session(n=10,correct=8)],'2026-10-15',question_target=60)
    assert initial['questions']==60
    assert after['questions']==50
    assert initial['target_questions']==60
    assert initial['mode']=='questions'


def test_day_settings_are_persistent_versioned_and_do_not_change_tomorrow(tmp_path):
    store=StudyStore(Repository(tmp_path))
    initial=store.day('2026-10-15',60)
    store.save_day('2026-10-15',StudyDay(questions=80),initial['revision'])
    reopened=StudyStore(Repository(tmp_path))
    assert reopened.day('2026-10-15',60)['settings']['questions']==80
    assert reopened.day('2026-10-16',60)['settings']['questions']==60
    with pytest.raises(ValueError,match='atualizado'): reopened.save_day('2026-10-15',StudyDay(questions=90),0)
    with pytest.raises(ValueError): replace(StudyDay(),questions=-1).validate()


def test_extra_theme_increases_only_today_and_prior_study_does_not_complete_it(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    view=service.overview('2026-10-15')
    t=max(view['states'],key=lambda t:t['total'])
    service.save_entry(StudyEntry(t['path'],'2026-10-15',10,8),'before-extra')
    service.add_topic('2026-10-15',t['topic_id'],10,0)
    added=service.overview('2026-10-15')
    assert added['plan']['target_questions']==70
    item=next(i for i in added['plan']['items'] if i['topic_id']==t['topic_id'])
    assert item['extra_pending']==10 and item['added_by_user']
    assert service.store.active('2026-10-15')[0]['session_id']=='before-extra'
    service.save_entry(StudyEntry(t['path'],'2026-10-15',4,3),'after-extra')
    current=service.overview('2026-10-15')
    assert next(i for i in current['plan']['items'] if i['topic_id']==t['topic_id'])['extra_pending']==6
    assert current['plan']['questions']<=56
    assert service.overview('2026-10-16')['plan']['target_questions']==60
    with pytest.raises(ValueError): service.add_topic('2026-10-15',t['topic_id'],5,0)
    service.remove_added_topic('2026-10-15',t['topic_id'],1)
    assert service.overview('2026-10-15')['plan']['target_questions']==60


def test_rest_suppresses_extras_and_configured_goal_survives_reload(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.configure_day('2026-10-15',80,'descanso',0)
    view=AdaptiveService(repo).overview('2026-10-15')
    assert view['plan']['items']==[]
    assert view['day']['settings']['questions']==80
    service.configure_day('2026-10-15',80,'normal',1)
    assert service.overview('2026-10-15')['plan']['target_questions']==80


def test_correcting_a_prior_session_does_not_complete_a_later_extra(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    t=max(service.overview('2026-10-15')['states'],key=lambda t:t['total'])
    service.save_entry(StudyEntry(t['path'],'2026-10-15',10,8),'before')
    service.add_topic('2026-10-15',t['topic_id'],10,0)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',20,16),'before',1)
    view=service.overview('2026-10-15')
    assert next(i for i in view['plan']['items'] if i['topic_id']==t['topic_id'])['extra_pending']==10


def test_adding_to_only_available_topic_keeps_the_base_plan(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    t=max(service.overview('2026-10-15')['states'],key=lambda t:t['total'])
    service.catalog=lambda day,include_parents=False:([t],{})
    service.configure_day('2026-10-15',20,'normal',0)
    service.add_topic('2026-10-15',t['topic_id'],10,1)
    view=service.overview('2026-10-15')
    assert view['plan']['questions']==30
    assert len(view['plan']['items'])==1
    assert view['plan']['items'][0]['extra_pending']==10


def test_extra_after_over_target_and_second_addition_require_new_work(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    t=max(service.overview('2026-10-15')['states'],key=lambda t:t['total'])
    service.configure_day('2026-10-15',5,'normal',0)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',10,8),'old')
    service.add_topic('2026-10-15',t['topic_id'],5,1)
    plan=service.overview('2026-10-15')['plan']
    assert plan['target_questions']==15 and plan['questions']==5
    service.save_entry(StudyEntry(t['path'],'2026-10-15',8,6),'new')
    service.add_topic('2026-10-15',t['topic_id'],5,2)
    item=next(i for i in service.overview('2026-10-15')['plan']['items'] if i['topic_id']==t['topic_id'])
    assert item['extra_pending']==5
