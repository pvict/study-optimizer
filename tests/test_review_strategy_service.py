from dataclasses import replace
import pytest
from osler.study_models import AdaptiveProfile
from osler.adaptive_service import AdaptiveService
from osler.study_feedback import result_feedback


def test_strategy_preview_is_read_only_and_apply_preserves_study_and_routine(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    repo,*_=setup_assessment(tmp_path,sample_pdf); s=AdaptiveService(repo)
    before=s.store.profile(); events=s.store.events()
    preview=s.preview_review_strategy('balanced_v2')
    assert s.store.profile()==before
    assert preview['before']['strategy']=='legacy_v1' and preview['after']['strategy']=='balanced_v2'
    assert preview['before']['max_questions']==preview['after']['max_questions']
    s.apply_review_strategy(preview)
    assert s.store.profile()['configured_profile']['review_strategy']=='balanced_v2'
    assert s.store.events()==events
    assert s.review_strategy_history()[-1]['profile_before']==before['id']
    with pytest.raises(ValueError): s.apply_review_strategy(preview)
    s.apply_review_strategy(s.preview_review_strategy('legacy_v1'))
    assert s.store.profile()['configured_profile']['review_strategy']=='legacy_v1'


def test_strategy_preview_invalidates_when_data_changes(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    repo,*_=setup_assessment(tmp_path,sample_pdf); s=AdaptiveService(repo)
    preview=s.preview_review_strategy('balanced_v2')
    s.store.save_profile(replace(AdaptiveProfile(**s.store.profile()['configured_profile']),max_questions=80),0)
    with pytest.raises(ValueError): s.apply_review_strategy(preview)


def test_balanced_feedback_uses_accuracy_goal_and_identifies_shared_lot():
    from test_balanced_reviews import block,state,profile
    e=block(); t=state([e]); p=profile().to_dict()
    feedback=result_feedback({'states':[t],'sessions':[e],'date':'2026-10-09','profile':p,
                             'review_queue':t['pending_reviews']},e['session_id'])
    assert 'Convicção abaixo da meta' not in feedback['message']
    assert feedback['coordinated_return']
    assert feedback['pending']['questions']==4
    assert feedback['next_questions']==max(t['theme_recommended_questions'],4) and feedback['next_questions']<20
    assert feedback['next_contact']=='2026-10-15'


def test_strategy_apply_race_does_not_save_profile_or_audit(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from osler.study_models import StudyDay
    repo,*_=setup_assessment(tmp_path,sample_pdf); s=AdaptiveService(repo)
    preview=s.preview_review_strategy('balanced_v2'); original=s.store.save_profile
    def concurrent(p,expected_id,**kwargs):
        s.store.save_day('2026-10-15',StudyDay(kind='descanso'),0)
        return original(p,expected_id,**kwargs)
    monkeypatch.setattr(s.store,'save_profile',concurrent)
    with pytest.raises(ValueError): s.apply_review_strategy(preview)
    assert s.store.profile()['id']==0 and not s.review_strategy_history()
