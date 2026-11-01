from dataclasses import replace

import pytest

from test_mock_schedule import configured
from osler.mock_exams import MockExam,MockExams,convert_to_entries


def test_area_capacity_preview_result_and_conversion_count_once(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    preview=service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP'])
    assert service.area_schedule() is None
    service.apply_area_schedule(preview)
    before=service.overview('2026-10-15')['plan']
    assert before['target_questions']==40
    assert before['ordinary_target_questions']==20
    assert before['questions']<=40
    row=service.register_area_result('area-2026-10-15','2026-10-15',22,18,unseen=True,token=service.agenda.token())
    after=service.overview('2026-10-15')['plan']
    assert after['done_questions']==22
    assert after['ordinary_target_questions']==20  # two extra questions do not remove themes
    with pytest.raises(ValueError): service.register_area_result('area-2026-10-15','2026-10-15',20,18)
    exam=replace(MockExam(**row['exam']),topics=[{'path':topic.qbank.path,'questions':22,'correct':18}])
    updated=MockExams(service.repository).save(exam,exam_key=row['exam_key'],expected_version=row['version'])
    convert_to_entries(service,row['exam_key'],updated['version'])
    assert service.overview('2026-10-15')['plan']['done_questions']==22
    assert service.overview('2026-10-15')['plan']['ordinary_target_questions']==20


def test_zero_ordinary_budget_and_stale_previews(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    preview=service.preview_area_schedule('2026-10-15','2026-11-26',1,40,['UNESP'])
    service.apply_area_schedule(preview)
    plan=service.overview('2026-10-15')['plan']
    assert plan['target_questions']==40 and plan['ordinary_target_questions']==0
    assert plan['items']==[]
    preview=service.preview_area_schedule('2026-10-15','2026-11-26',1,40,['UNESP'],{'area-2026-10-15':'2026-10-16'})
    service.configure_day('2026-10-16',30,'normal',0)
    with pytest.raises(ValueError): service.apply_area_schedule(preview)


def test_errors_can_be_added_after_conversion_without_changing_results(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    mocks=MockExams(service.repository)
    row=mocks.save(MockExam('2026-10-15',20,15,unseen_questions=True,
        topics=[{'path':topic.qbank.path,'questions':20,'correct':15}]))
    convert_to_entries(service,row['exam_key'],1)
    events=service.store.events(); results=mocks.events()
    service.save_mock_errors(row['exam_key'],1,[{'path':topic.qbank.path,'errors':3}],0,service.agenda.token())
    assert service.store.events()==events and mocks.events()==results
    assert service.mock_errors(row['exam_key'])['errors'][0]['errors']==3
    with pytest.raises(ValueError): service.save_mock_errors(row['exam_key'],1,[],0,service.agenda.token())
    preview=service.preview_mock_correction(row['exam_key'],'2026-10-16',20)
    assert preview['rows'] and not preview['unassigned']
    service.apply_mock_correction(preview)
    reservation=next(r for r in service.agenda.active(service.store.active('2026-10-16'),'2026-10-16')['rows'] if r.get('source_exam_key'))
    assert reservation['remaining']==reservation['questions']


def test_changed_result_marks_error_mapping_stale_and_future_full_mock_blocks_area(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    mocks=MockExams(service.repository); row=mocks.save(MockExam('2026-10-15',20,15))
    service.save_mock_errors(row['exam_key'],1,[{'path':topic.qbank.path,'errors':None}],0,service.agenda.token())
    mocks.save(MockExam('2026-10-15',20,16),exam_key=row['exam_key'],expected_version=1)
    assert service.mock_errors(row['exam_key'])['stale']
    with pytest.raises(ValueError): service.preview_mock_correction(row['exam_key'],'2026-10-16')
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    preview=service.preview_area_schedule('2026-10-18','2026-11-29',1,20,['UNESP'])
    assert all(r.get('status')!='blocked' for r in preview['occurrences'])
    assert preview['occurrences'][0]['date']!='2026-10-18'
    service.apply_area_schedule(preview)
    assert not service.overview('2026-10-18')['plan'].get('area_tasks')


def test_automatic_area_fit_and_manual_preview_dates(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    preview=service.preview_area_schedule('2026-10-18','2026-11-29',2,20,['UNESP'])
    dates=[r['date'] for r in preview['occurrences'] if r['date']]
    assert len(dates)==len(set(dates))
    assert all(r.get('status')!='blocked' for r in preview['occurrences'])
    assert all(d not in service.mock_schedule()['overrides'] for d in dates)
    assert service.area_schedule() is None
    with pytest.raises(ValueError,match='protegida'):
        service.preview_area_schedule('2026-10-18','2026-11-29',1,20,['UNESP'],{'area-2026-10-18':'2026-10-25'})


def test_manual_topic_date_is_previewed_applied_and_undone(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    base=service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP'])
    item=max(base['topic_options'],key=lambda i:i['questions'])
    preview=service.preview_area_schedule(**{**base['request'],'topic_dates':{item['topic_id']:'2026-10-20'}})
    assert preview['rows'][0]['date']=='2026-10-20'
    assert not service.agenda.active([],'2026-10-15')['rows']
    plan_id=service.apply_area_schedule(preview)
    assert any(r['topic_id']==item['topic_id'] and r['date']=='2026-10-20' for r in service.agenda.active([],'2026-10-15')['rows'])
    service.cancel_replan(plan_id)
    assert not service.agenda.active([],'2026-10-15')['rows']


def test_unplaceable_series_cannot_be_applied(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.configure_day('2026-10-15',40,'descanso',0)
    preview=service.preview_area_schedule('2026-10-15','2026-10-15',1,20,['UNESP'])
    assert preview['occurrences'][0]['status']=='blocked'
    with pytest.raises(ValueError,match='vaga'):
        service.apply_area_schedule(preview)


def test_later_edits_preserve_auto_moved_history_and_expire_manual_topic_dates(tmp_path,sample_pdf,monkeypatch):
    from datetime import date
    import osler.exam_practice_service as module
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    preview=service.preview_area_schedule('2026-10-18','2026-11-29',1,20,['UNESP'])
    key=preview['topic_options'][0]['topic_id']
    preview=service.preview_area_schedule(**{**preview['request'],'topic_dates':{key:'2026-10-20'}})
    service.apply_area_schedule(preview)
    frozen=dict(preview['occurrences'][0])
    monkeypatch.setattr(module,'today_local',lambda:date(2026,10,22))
    edited=service.preview_area_schedule(**{**preview['request'],'exceptions':{'area-2026-10-25':'2026-10-27'}})
    recovered=edited['occurrences'][0]
    assert recovered['id']==frozen['id'] and recovered['original_date']==frozen['original_date']
    assert recovered['missed_date']==frozen['date'] and recovered['date']=='2026-10-22'
    assert not edited['request']['topic_dates']


def test_manual_training_cannot_collide_with_recorded_occurrence(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-26',1,40,['UNESP']))
    service.register_area_result('area-2026-10-15','2026-10-15',40,30)
    with pytest.raises(ValueError,match='outro treino'):
        service.preview_area_schedule('2026-10-15','2026-11-26',1,40,['UNESP'],{'area-2026-10-22':'2026-10-15'})


def test_moving_correction_topic_preserves_source_exclusion(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    exam=MockExams(service.repository).save(MockExam('2026-10-15',20,15,unseen_questions=True,
        topics=[{'path':topic.qbank.path,'questions':20,'correct':15}]))
    service.apply_mock_correction(service.preview_mock_correction(exam['exam_key'],'2026-10-16',40))
    preview=service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP'])
    key=next(i['topic_id'] for i in preview['topic_options'] if i['path']==topic.qbank.path)
    preview=service.preview_area_schedule(**{**preview['request'],'topic_dates':{key:'2026-10-20'}})
    assert preview['rows'][0]['source_exam_key']==exam['exam_key']
    service.apply_area_schedule(preview)
    convert_to_entries(service,exam['exam_key'],1)
    row=next(r for r in service.agenda.active(service.store.active('2026-10-20'),'2026-10-20')['rows'] if r['topic_id']==key)
    assert row['remaining']==row['questions']


def test_repreview_preserves_partial_completion_of_manual_topic(tmp_path,sample_pdf):
    from osler.study_models import StudyEntry
    service,topic=configured(tmp_path,sample_pdf)
    base=service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP'])
    item=max(base['topic_options'],key=lambda i:i['questions'])
    preview=service.preview_area_schedule(**{**base['request'],'topic_dates':{item['topic_id']:'2026-10-20'}})
    service.apply_area_schedule(preview)
    service.save_entry(StudyEntry(item['path'],'2026-10-15',5,4),'partial')
    new=service.preview_area_schedule(**preview['request'])
    assert new['rows'][0]['questions']==item['questions']-5
    service.apply_area_schedule(new)
    row=next(r for r in service.agenda.active(service.store.active('2026-10-15'),'2026-10-15')['rows'] if r['topic_id']==item['topic_id'])
    assert row['remaining']==item['questions']-5


def test_correction_date_can_be_moved_before_result_without_fabricating_work(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    source=next(r for r in service.exam_learning_agenda() if r['source_day']=='2026-10-18')
    assert source['date']=='2026-10-21' and source['needs_details']
    preview=service.preview_correction_day(source['source_id'],'2026-10-22')
    assert next(r for r in service.exam_learning_agenda() if r['source_id']==source['source_id'])['date']=='2026-10-21'
    service.apply_correction_day(preview)
    assert next(r for r in service.exam_learning_agenda() if r['source_id']==source['source_id'])['date']=='2026-10-22'
    assert not service.store.events()
    assert not service.agenda.active([],'2026-10-15')['rows']


def test_original_conversion_after_correction_creation_does_not_complete_its_reinforcement(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    row=MockExams(service.repository).save(MockExam('2026-10-15',20,15,unseen_questions=True,
        topics=[{'path':topic.qbank.path,'questions':20,'correct':15}]))
    preview=service.preview_mock_correction(row['exam_key'],'2026-10-15',40)
    service.apply_mock_correction(preview)
    convert_to_entries(service,row['exam_key'],1)
    rows=service.agenda.active(service.store.active('2026-10-15'),'2026-10-15')['rows']
    assert rows[0]['remaining']==rows[0]['questions']


def test_linked_area_results_are_preserved_when_moving_future_dates_and_undo_blocked(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    first=service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP']))
    service.register_area_result('area-2026-10-15','2026-10-15',20,15)
    preview=service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP'],{'area-2026-10-22':'2026-10-23'})
    service.apply_area_schedule(preview)
    assert service.overview('2026-10-15')['plan']['done_questions']==20
    with pytest.raises(ValueError): service.cancel_replan(service.area_schedule()['id'])
    with pytest.raises(ValueError): service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP'],{'area-2026-10-15':'2026-10-16'})


def test_week_volume_counts_unconverted_and_converted_area_result_once(tmp_path,sample_pdf):
    from osler.study_dashboard import week_summary
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP']))
    service.register_area_result('area-2026-10-15','2026-10-15',20,15)
    summary=week_summary(service.overview('2026-10-15'),{})
    assert summary['questions']==20
    assert summary['new_n']==0
    assert '2026-10-15' not in service.recorded_mock_days()
    from osler.study_evolution import evolution_snapshot
    view=service.overview('2026-10-15')
    summary=evolution_snapshot(view['states'],view['sessions'],[],'2026-10-15',area_results=view['agenda']['area_results'])
    assert summary['actual_attempts']==20
    assert summary['actual_days']==1
    from osler.evolution_history_ui import observed_history
    from osler.study_models import AdaptiveProfile
    history=observed_history(view['sessions'],'2026-10-15',AdaptiveProfile(**view['profile']),{},view['agenda']['overrides'],area_results=view['agenda']['area_results'])
    assert history['volume']==20 and history['new_n']==0 and history['study_days']==1


def test_partial_area_training_cannot_waive_the_whole_day(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP']))
    row=service.register_area_result('area-2026-10-15','2026-10-15',20,15)
    with pytest.raises(ValueError,match='área'):
        service.preview_mock_day(row['exam_key'],row['version'])
    assert service.overview('2026-10-15')['plan']['kind']=='normal'


def test_change_future_frequency_and_volume_preserves_recorded_occurrences(tmp_path,sample_pdf):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP']))
    saved=service.register_area_result('area-2026-10-15','2026-10-15',20,15)
    preview=service.preview_area_schedule('2026-10-16','2026-11-26',2,25,['UNESP','SUS-SP'])
    previous=next(r for r in preview['occurrences'] if r['id']=='area-2026-10-15')
    assert previous['questions']==20
    service.apply_area_schedule(preview)
    assert MockExams(service.repository).active()[0]==saved
    assert len([r for r in service.area_schedule()['occurrences'] if r['date']=='2026-10-16'])==1
