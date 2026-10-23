from dataclasses import replace
from osler.study_errors import ErrorStore,StudyError
from osler.study_signals import poor_study_paths,study_event_token
from osler.adaptive_planning import topic_states
from osler.study_models import AdaptiveProfile
from test_adaptive_planning import topic
from osler.storage import Repository


def test_registered_error_is_high_not_urgent_and_keeps_spacing(tmp_path):
    repo=Repository(tmp_path)
    errors=ErrorStore(repo)
    t=topic(answered=10)
    errors.save(StudyError(t['path'],'2026-10-15','chute',critical=True))
    before=topic_states([t],[],[],{},'2026-10-15',AdaptiveProfile())[0]
    after=topic_states([t],[],[],{},'2026-10-15',AdaptiveProfile(),error_paths=errors.adverse_paths('2026-10-15'))[0]
    assert after['priority']=='alta' and after['evidence_priority']=='alta'
    assert after['reason']=='Erros recorrentes registrados neste tema'
    assert before['review_interval_days']==after['review_interval_days']
    assert after['registered_error']


def test_error_blocks_flashcard_reduction_and_changes_evidence_token(tmp_path):
    repo=Repository(tmp_path)
    errors=ErrorStore(repo)
    with repo._connection() as db: before=study_event_token(db)
    row=errors.save(StudyError(['Área','Tema'],'2026-10-15','chute',critical=True))
    assert poor_study_paths(repo,'2026-10-15')==[list(row['path'])]
    with repo._connection() as db: assert before!=study_event_token(db)
    errors.resolve(row['error_key'],row['version'])
    assert poor_study_paths(repo,'2026-10-15')==[]
