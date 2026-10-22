from copy import deepcopy

from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from test_assessments import setup_assessment


def setup(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    topic=service.catalog('2026-10-15')[0][0]
    return service,topic


def test_today_activity_uses_current_versions_and_excludes_old_totals(tmp_path,sample_pdf):
    from osler.study_feedback import day_activity
    service,t=setup(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',30,24,confident_correct=20),'today')
    service.save_entry(StudyEntry(t['path'],'2026-10-15',100,80,kind='acumulado'),'total')
    service.save_entry(StudyEntry(t['path'],'2026-10-14',20,15),'yesterday')
    service.save_entry(StudyEntry(t['path'],'2026-10-15',10,9),'voided')
    service.store.void('voided',1)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',25,20,confident_correct=18),'today',1)
    activity=day_activity(service.overview('2026-10-15'))
    assert activity['questions']==25
    assert activity['blocks']==1
    assert [e['session_id'] for e in activity['events']]==['today']
    assert activity['events'][0]['version']==2


def test_feedback_separates_performance_conviction_and_two_return_dates(tmp_path,sample_pdf):
    from osler.study_feedback import result_feedback
    service,t=setup(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',30,12,confident_correct=8),'poor')
    view=service.overview('2026-10-15'); before=deepcopy(view)
    feedback=result_feedback(view,'poor')
    assert feedback['accuracy_pct']==40
    assert feedback['conviction_pct']==100*8/30
    assert feedback['mistakes']==18 and feedback['guesses']==4
    assert feedback['pending']=={'questions':22,'due_date':'2026-10-22'}
    assert feedback['next_contact']=='2026-10-18'
    assert feedback['next_questions']>=20
    assert feedback['level']=='warning'
    assert view==before


def test_unknown_conviction_does_not_become_zero_or_a_fabricated_queue(tmp_path,sample_pdf):
    from osler.study_feedback import result_feedback
    service,t=setup(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',30,27),'unknown')
    feedback=result_feedback(service.overview('2026-10-15'),'unknown')
    assert feedback['accuracy_pct']==90
    assert feedback['conviction_pct'] is None and feedback['guesses'] is None
    assert feedback['pending'] is None
    assert feedback['level']=='info'


def test_low_accuracy_still_gets_feedback_when_conviction_is_unknown(tmp_path,sample_pdf):
    from osler.study_feedback import result_feedback
    service,t=setup(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',20,10),'weak')
    feedback=result_feedback(service.overview('2026-10-15'),'weak')
    assert feedback['accuracy_pct']==50 and feedback['conviction_pct'] is None
    assert feedback['level']=='warning'


def test_linked_review_feedback_shows_only_the_remaining_child_lot(tmp_path,sample_pdf):
    from osler.study_feedback import result_feedback
    service,t=setup(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(t['path'],'2026-10-08',10,6,confident_correct=4),'root')
    service.save_entry(StudyEntry(t['path'],'2026-10-15',6,5,mode='repetidas',confident_correct=3,review_of='root'),'child')
    feedback=result_feedback(service.overview('2026-10-15'),'child')
    assert feedback['pending']=={'questions':3,'due_date':'2026-10-22'}
    assert feedback['conviction_pct']==50


def test_approximate_percentage_never_invents_correct_counts(tmp_path,sample_pdf):
    from osler.study_feedback import result_feedback
    service,t=setup(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',7,percent=80),'approx')
    feedback=result_feedback(service.overview('2026-10-15'),'approx')
    assert feedback['accuracy_pct']==80 and feedback['approximate']
    assert feedback['entry']['correct'] is None and feedback['mistakes'] is None


def test_success_does_not_declare_mastery_and_uses_actual_smaller_next_dose(tmp_path,sample_pdf):
    from osler.study_feedback import result_feedback
    service,t=setup(tmp_path,sample_pdf)
    for sid,day in [('one','2026-10-01'),('two','2026-10-08')]:
        service.save_entry(StudyEntry(t['path'],day,20,20,mode='repetidas',confident_correct=20),sid)
    feedback=result_feedback(service.overview('2026-10-15'),'two')
    assert feedback['level']=='success'
    assert feedback['next_questions']==10
    assert feedback['next_contact']=='2026-10-22'
    assert feedback['pending'] is None
    assert feedback['dose_kind']=='maintenance'


def test_voided_receipt_and_non_question_entries_are_handled_truthfully(tmp_path,sample_pdf):
    from osler.study_feedback import result_feedback,day_activity
    service,t=setup(tmp_path,sample_pdf)
    service.save_entry(StudyEntry(t['path'],'2026-10-15',kind='contato',mode='mistas'),'contact')
    service.save_entry(StudyEntry(t['path'],'2026-10-15',30,24,kind='acumulado'),'total')
    view=service.overview('2026-10-15')
    assert result_feedback(view,'contact')['accuracy_pct'] is None
    assert result_feedback(view,'total')['pending'] is None
    assert day_activity(view)['questions']==0
    service.store.void('contact',1)
    assert result_feedback(service.overview('2026-10-15'),'contact') is None
