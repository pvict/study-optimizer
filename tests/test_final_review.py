from dataclasses import replace
import pytest
from osler.exam_goals import ExamGoals,ExamTarget
from osler.study_models import AdaptiveProfile
from test_study_prevention import prevention_service


def configured(tmp_path,sample_pdf):
    service,topic=prevention_service(tmp_path,sample_pdf)
    event=ExamGoals(service.repository).save(ExamTarget('Banca A','2026-10-29',70,100,'Edital'))
    return service,topic,event


def test_final_review_preview_apply_cancel_preserves_results_and_rest(tmp_path,sample_pdf):
    service,topic,event=configured(tmp_path,sample_pdf)
    before=service.store.events()
    preview=service.preview_final_review(event['target_id'],'2026-10-15',30)
    assert preview['rest_day']=='2026-10-28'
    assert all(r['date']<'2026-10-28' for r in preview['rows'])
    assert all(sum(r['questions'] for r in preview['rows'] if r['date']==d)<=30 for d in preview['overrides'])
    assert not service.agenda.active(service.store.active('2026-10-15'),'2026-10-15')['active']
    pid=service.apply_final_review(preview)
    assert service.overview('2026-10-28')['plan']['kind']=='descanso'
    assert service.store.events()==before
    service.cancel_replan(pid)
    assert service.overview('2026-10-28')['plan']['kind']=='normal'
    assert service.store.events()==before


def test_final_review_stale_preview_and_invalid_window_are_rejected(tmp_path,sample_pdf):
    service,topic,event=configured(tmp_path,sample_pdf)
    with pytest.raises(ValueError): service.preview_final_review(event['target_id'],'2026-10-29',30)
    with pytest.raises(ValueError): service.preview_final_review(event['target_id'],'2026-10-15',0)
    preview=service.preview_final_review(event['target_id'],'2026-10-15',30)
    service.configure_day('2026-10-16',15,'normal',0)
    with pytest.raises(ValueError): service.apply_final_review(preview)


def test_exam_weights_link_ids_and_preserve_joint_incidence_rule(tmp_path,sample_pdf):
    service,topic,event=configured(tmp_path,sample_pdf)
    record=service.store.profile()
    p=AdaptiveProfile(**record['configured_profile'])
    with pytest.raises(ValueError): service.store.save_profile(replace(p,exam_weights={event['target_id']:3}),record['id'])
    service.guide.store.save_dataset({'institutions':['Banca A'],'observed_date':'2026-10-15','unit':'questoes',
                                    'rows':[{'path':topic['path'],'value':100,'band':'alta'}]})
    service.apply_exam_weights(service.preview_exam_weights({event['target_id']:3},30))
    assert service.store.profile()['profile']['institution_weights']=={'Banca A':3}
    ExamGoals(service.repository).save(ExamTarget('Banca B','2026-10-29',70,100,'Edital'),target_id=event['target_id'],expected_version=1)
    assert service.store.profile()['profile']['institution_weights']=={}
    assert not service.store.profile()['weight_policy']['allowed']


def test_final_review_is_not_carried_as_a_missed_daily_plan(tmp_path,sample_pdf):
    service,topic,event=configured(tmp_path,sample_pdf)
    preview=service.preview_final_review(event['target_id'],'2026-10-15',30)
    service.apply_final_review(preview)
    service.remember_day(service.overview('2026-10-15'))
    assert not service.agenda.daily_plans()


@pytest.mark.parametrize('mode',['balanced','reviews','extra','custom'])
def test_generic_replan_preserves_final_eve_rest(tmp_path,sample_pdf,mode):
    from osler.study_models import StudyEntry
    service,topic,event=configured(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(topic['path'],'2026-10-01',20,10,confident_correct=10),'actual',1)
    service.apply_final_review(service.preview_final_review(event['target_id'],'2026-10-15',30))
    preview=service.preview_replan('2026-10-28',1,mode,dates={topic['topic_id']:'2026-10-28'})
    assert not preview['rows']
    assert service.overview('2026-10-28')['plan']['kind']=='descanso'


def test_final_preview_does_not_credit_preexisting_same_day_work_twice(tmp_path,sample_pdf):
    from osler.study_models import StudyEntry
    from osler.study_errors import ErrorStore,StudyError
    service,topic,event=configured(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(topic['path'],'2026-10-15',10,10),'today')
    ErrorStore(service.repository).save(StudyError(topic['path'],'2026-10-15','chute',critical=True))
    preview=service.preview_final_review(event['target_id'],'2026-10-15',30)
    expected=next(r for r in preview['rows'] if r['date']=='2026-10-15' and r['topic_id']==topic['topic_id'])
    service.apply_final_review(preview)
    actual=next(r for r in service.overview('2026-10-15')['plan']['items'] if r['topic_id']==topic['topic_id'])
    assert actual['questions']==expected['questions']==20


def test_final_rest_is_preserved_when_prevention_is_applied(tmp_path,sample_pdf):
    from osler.study_models import StudyEntry
    service,topic,event=configured(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(topic['path'],'2026-10-01',20,10,confident_correct=10),'actual',1)
    service.apply_final_review(service.preview_final_review(event['target_id'],'2026-10-15',30))
    preview=service.preview_prevention('2026-10-28',1,'reviews')
    assert '2026-10-28' not in preview['overrides']
    service.apply_prevention(preview)
    assert service.overview('2026-10-28')['plan']['kind']=='descanso'
