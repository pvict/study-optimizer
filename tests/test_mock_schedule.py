from dataclasses import replace
import pytest
from osler.adaptive_service import AdaptiveService
from osler.study_models import AdaptiveProfile,StudyEntry
from osler.storage import Repository


def configured(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    repo,*_,topic=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.store.save_profile(AdaptiveProfile(max_questions=40,max_topics=3,new_share=.5,workload_mode='fixed',exam_date='2026-11-30',mock_cadence_days=7),0)
    return service,topic


def test_series_moves_one_occurrence_without_shifting_the_others():
    from osler.mock_schedule import schedule_dates
    rows=schedule_dates('2026-10-18',7,'2026-11-08',{'2026-10-25':'2026-10-27','2026-11-01':None})
    assert [(r['occurrence_id'],r['date']) for r in rows]==[
        ('2026-10-18','2026-10-18'),('2026-10-25','2026-10-27'),('2026-11-01',None),('2026-11-08','2026-11-08')]
    with pytest.raises(ValueError): schedule_dates('2026-10-18',7,'2026-11-08',{'2026-10-25':'2026-11-01'})
    with pytest.raises(ValueError): schedule_dates('2026-10-18',0,'2026-11-08',{})
    with pytest.raises(ValueError): schedule_dates('2026-10-18',7,'2026-11-08',{'2026-10-26':'2026-10-27'})


def test_schedule_preview_apply_move_undo_preserves_results_and_capacity(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    before=service.store.events()
    preview=service.preview_mock_schedule('2026-10-18',7)
    assert preview['occurrences'][0]['date']=='2026-10-18'
    assert service.mock_schedule() is None
    first=service.apply_mock_schedule(preview)
    assert service.overview('2026-10-18')['plan']['items']==[]
    assert service.overview('2026-10-18')['plan']['routine_override']['mode']=='mock_reserved'
    planned=service.calendar(20)
    assert all(d['questions']<=40 for d in planned)
    assert not next(d for d in planned if d['date']=='2026-10-18')['items']
    move=service.preview_mock_move('2026-10-18','2026-10-20')
    second=service.apply_mock_schedule(move)
    assert service.mock_schedule()['id']==second
    assert service.overview('2026-10-18')['plan']['kind']=='normal'
    assert service.overview('2026-10-20')['plan']['kind']=='descanso'
    assert service.overview('2026-10-25')['plan']['kind']=='descanso'
    service.cancel_replan(second)
    assert service.mock_schedule()['id']==first
    assert service.overview('2026-10-18')['plan']['kind']=='descanso'
    assert service.overview('2026-10-20')['plan']['kind']=='normal'
    assert service.store.events()==before
    with service.repository._connection() as db:
        assert db.execute('SELECT COUNT(*) FROM mock_exams').fetchone()[0]==0


def test_cancel_one_date_and_stale_preview_are_safe(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    remove=service.preview_mock_move('2026-10-18',None)
    service.apply_mock_schedule(remove)
    assert service.overview('2026-10-18')['plan']['kind']=='normal'
    assert service.overview('2026-10-25')['plan']['kind']=='descanso'
    move=service.preview_mock_move('2026-10-25','2026-10-26')
    service.configure_day('2026-10-16',30,'normal',0)
    with pytest.raises(ValueError): service.apply_mock_schedule(move)
    with pytest.raises(ValueError): service.preview_mock_move('2026-10-25','2026-10-14')


def test_reserved_today_has_no_saved_normal_plan_or_fake_adherence(tmp_path,sample_pdf):
    from osler.study_read_model import waived_days,read_events
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-15',7))
    service.remember_day(service.overview('2026-10-15'))
    assert not service.agenda.daily_plans()
    assert '2026-10-15' in waived_days(read_events(service.repository,'study_plan_runs'),'2026-10-15')


def test_changed_dates_preview_contains_topics_and_preserves_seven_day_queue(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(topic.qbank.path,'2026-10-08',20,10,confident_correct=10),'pending')
    before=service.overview('2026-10-15')['states']
    preview=service.preview_mock_schedule('2026-10-15',7)
    assert preview['topic_changes']
    assert all(r['after_date'] is None or r['after_date']!='2026-10-15' for r in preview['topic_changes'])
    service.apply_mock_schedule(preview)
    after=service.overview('2026-10-15')['states']
    assert [(t['topic_id'],t['pending_reviews']) for t in after]==[(t['topic_id'],t['pending_reviews']) for t in before]
    assert service.overview('2026-10-15')['plan']['done_questions']==0


def test_exam_day_and_existing_final_rest_are_not_overwritten(tmp_path,sample_pdf):
    from osler.exam_goals import ExamGoals,ExamTarget
    service,topic=configured(tmp_path,sample_pdf)
    ExamGoals(service.repository).save(ExamTarget('Banca A','2026-10-25',70,100,'Edital'))
    preview=service.preview_mock_schedule('2026-10-18',7)
    assert next(r for r in preview['occurrences'] if r['date']=='2026-10-25')['status']=='blocked'
    service.apply_mock_schedule(preview)
    with pytest.raises(ValueError): service.preview_mock_move('2026-10-18','2026-10-25')


def test_future_occurrences_remain_editable_after_first_mock_has_passed(tmp_path,sample_pdf,monkeypatch):
    from datetime import datetime
    import osler.planner_service
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    class Later(datetime):
        @classmethod
        def now(cls,tz=None): return cls(2026,10,20,12,tzinfo=tz)
    monkeypatch.setattr(osler.planner_service,'datetime',Later)
    service.apply_mock_schedule(service.preview_mock_move('2026-10-25','2026-10-27'))
    assert service.overview('2026-10-27')['plan']['kind']=='descanso'
    with pytest.raises(ValueError): service.preview_mock_move('2026-10-18','2026-10-22')


def test_three_versions_undo_and_adherence_use_only_effective_dates(tmp_path,sample_pdf):
    from osler.study_read_model import waived_days,read_events
    service,topic=configured(tmp_path,sample_pdf)
    first=service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    second=service.apply_mock_schedule(service.preview_mock_move('2026-10-18','2026-10-19'))
    third=service.apply_mock_schedule(service.preview_mock_move('2026-10-18','2026-10-20'))
    def days(): return waived_days(read_events(service.repository,'study_plan_runs'),'2026-10-15')
    assert '2026-10-20' in days() and not {'2026-10-18','2026-10-19'}&days()
    service.cancel_replan(third)
    assert service.mock_schedule()['id']==second and '2026-10-19' in days() and '2026-10-18' not in days()
    service.cancel_replan(second)
    assert service.mock_schedule()['id']==first and '2026-10-18' in days()


def test_final_review_and_prevention_preserve_a_reserved_mock(tmp_path,sample_pdf):
    from osler.exam_goals import ExamGoals,ExamTarget
    service,topic=configured(tmp_path,sample_pdf)
    target=ExamGoals(service.repository).save(ExamTarget('Banca A','2026-10-29',70,100,'Edital'))
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    preview=service.preview_final_review(target['target_id'],'2026-10-16',40)
    assert '2026-10-18' not in preview['overrides']
    service.apply_final_review(preview)
    assert service.overview('2026-10-18')['plan']['routine_override']['mode']=='mock_reserved'


def test_recorded_mock_cannot_be_moved_as_if_still_only_planned(tmp_path,sample_pdf):
    from osler.mock_exams import MockExams,MockExam
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-15',7))
    MockExams(service.repository).save(MockExam('2026-10-15',100,75))
    with pytest.raises(ValueError,match='resultado'): service.preview_mock_move('2026-10-15','2026-10-16')


def test_individual_move_cannot_precede_preparation_start(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    old=service.store.profile()
    service.store.save_profile(replace(AdaptiveProfile(**old['configured_profile']),start_date='2026-10-20'),old['id'])
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-21',7))
    with pytest.raises(ValueError): service.preview_mock_move('2026-10-21','2026-10-18')


def test_undo_does_not_rewrite_past_reserved_days(tmp_path,sample_pdf,monkeypatch):
    from datetime import datetime
    import osler.planner_service
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    moved=service.apply_mock_schedule(service.preview_mock_move('2026-10-18','2026-10-19'))
    class Later(datetime):
        @classmethod
        def now(cls,tz=None): return cls(2026,10,20,12,tzinfo=tz)
    monkeypatch.setattr(osler.planner_service,'datetime',Later)
    with pytest.raises(ValueError,match='passadas'): service.cancel_replan(moved)


def test_final_eve_never_silently_erases_a_mock_reservation(tmp_path,sample_pdf):
    from osler.exam_goals import ExamGoals,ExamTarget
    service,topic=configured(tmp_path,sample_pdf)
    target=ExamGoals(service.repository).save(ExamTarget('Banca A','2026-10-29',70,100,'Edital'))
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-28',7))
    with pytest.raises(ValueError,match='simulado'): service.preview_final_review(target['target_id'],'2026-10-20',40)


def test_manual_reservation_collision_preview_matches_the_applied_calendar(tmp_path,monkeypatch):
    from test_adaptive_planning import topic
    service=AdaptiveService(Repository(tmp_path))
    service.store.save_profile(AdaptiveProfile(max_questions=40,max_topics=1,new_share=1,workload_mode='fixed',exam_date='2026-11-30'),0)
    monkeypatch.setattr(service,'catalog',lambda as_of,include_parents=False:([topic('A'),topic('B')],{}))
    rows=[{'topic_id':name,'path':['Área',name],'date':day,'original_due':day,'questions':40,'new_topic':True}
          for name,day in [('A','2026-10-15'),('B','2026-10-16')]]
    service.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-15','scope':'manual','selected':[],
                          'rows':rows,'cutoff':0},service.agenda.token())
    preview=service.preview_mock_schedule('2026-10-15',7)
    service.apply_mock_schedule(preview)
    actual={}
    for day in service.calendar(28):
        for item in day['items']: actual.setdefault(item['topic_id'],day['date'])
    for row in preview['topic_changes']:
        assert row['after_date']==actual.get(row['topic_id'])
