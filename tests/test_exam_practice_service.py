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
    assert all(r.get('status')=='blocked' for r in preview['occurrences'])
    service.apply_area_schedule(preview)
    assert not service.overview('2026-10-18')['plan'].get('area_tasks')


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
