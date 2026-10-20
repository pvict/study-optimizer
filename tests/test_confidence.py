from dataclasses import replace
import pytest

from osler.study_models import StudyEntry
from osler.review_queue import review_queue, review_progress
from osler.storage import Repository
from osler.study_storage import StudyStore


def event(sid,day='2026-10-01',n=10,correct=8,confident=6,review_of=None):
    entry=StudyEntry(['Área','Tema'],day,n,correct,mode='repetidas' if review_of else 'novas',confident_correct=confident,review_of=review_of)
    return {'session_id':sid,'entry':entry.to_dict()}


def test_guesses_and_errors_return_in_seven_days_until_confident():
    first=event('a')
    queue=review_queue([first])
    assert queue[0]['questions']==4 and queue[0]['due_date']=='2026-10-08'
    second=event('b','2026-10-08',3,2,1,'a')
    queue=review_queue([first,second])
    assert {q['session_id']:q['questions'] for q in queue}=={'a':1,'b':2}
    assert next(q['due_date'] for q in queue if q['session_id']=='b')=='2026-10-15'
    third=event('c','2026-10-15',2,2,2,'b')
    assert [q['session_id'] for q in review_queue([first,second,third])]==['a']


def test_unknown_confidence_is_not_invented_and_invalid_counts_rejected():
    old=event('old',confident=None)
    assert review_queue([old])==[]
    with pytest.raises(ValueError): StudyEntry(**{**old['entry'],'confident_correct':9}).validate()
    with pytest.raises(ValueError): review_queue([old,event('child',review_of='old')])


def test_parent_edits_or_voids_cannot_orphan_or_overconsume_reviews(tmp_path):
    store=StudyStore(Repository(tmp_path))
    a,b=event('a'),event('b','2026-10-08',4,4,3,'a')
    store.save_batch([('a',StudyEntry(**a['entry']),0),('b',StudyEntry(**b['entry']),0)])
    with pytest.raises(ValueError): store.void('a',1)
    with pytest.raises(ValueError): store.save_batch([('a',replace(StudyEntry(**a['entry']),confident_correct=9),1)])
    assert len(store.events())==2


def test_linked_review_updates_consolidated_cohort_without_counting_questions_twice():
    first=event('a',n=10,correct=8,confident=6)
    reviewed=event('b','2026-10-08',4,4,4,'a')
    progress=review_progress([first,reviewed])
    assert progress[0]['questions']==10
    assert progress[0]['consolidated']==10


def test_weak_parent_conviction_protects_descendants_in_advanced_reduction(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    from test_classification import known
    from osler.adaptive_service import AdaptiveService
    repo,assessment,matching,row=setup_assessment(tmp_path,sample_pdf)
    assessment.save_observation(matching,row.row_id,known(),0)
    AdaptiveService(repo).save_entry(StudyEntry(row.qbank.path[:-1],'2026-10-15',10,10,confident_correct=2),'weak-parent')
    item=next(i for i in assessment.analyze(matching,'2026-10-15')['items'] if i['row_id']==row.row_id)
    assert item['classification']['category']=='C'
