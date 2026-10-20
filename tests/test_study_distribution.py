from dataclasses import replace
from osler.adaptive_planning import topic_states,allocate_day
from osler.study_models import AdaptiveProfile
from test_adaptive_planning import topic,session


def mixed_states(profile,sessions=()):
    return topic_states([*[topic('N'+str(i)) for i in range(5)],*[topic('R'+str(i),answered=50) for i in range(5)]],list(sessions),[],{},'2026-10-15',profile)


def test_fifty_fifty_allocates_questions_across_multiple_new_topics():
    p=AdaptiveProfile(max_questions=120,max_topics=5,new_share=.5)
    plan=allocate_day(mixed_states(p),p,None,'normal',[],'2026-10-15',question_target=120)
    assert sum(i['questions'] for i in plan['items'] if i['topic_id'].startswith('N'))==60
    assert sum(i['questions'] for i in plan['items'] if i['topic_id'].startswith('R'))==60
    assert sum(i['topic_id'].startswith('N') for i in plan['items'])>=2
    assert len(plan['items'])<=5


def test_new_contact_today_consumes_new_quota_after_state_has_changed():
    p=AdaptiveProfile(max_questions=120,new_share=.5,max_topics=5)
    e=session('N0',n=20,correct=18)
    states=mixed_states(p,[e])
    plan=allocate_day(states,p,None,'normal',[e],'2026-10-15',question_target=120)
    assert plan['distribution']['done_new']==20
    assert plan['distribution']['planned_new']==40
    assert plan['distribution']['planned_reviews']==60
    assert plan['questions']==100


def test_zero_and_full_share_are_respected_and_missing_group_is_explained():
    for share,prefix in [(0,'R'),(1,'N')]:
        p=AdaptiveProfile(new_share=share)
        plan=allocate_day(mixed_states(p),p,None,'normal',[],'2026-10-15',question_target=60)
        assert all(i['topic_id'].startswith(prefix) for i in plan['items'])
    p=AdaptiveProfile(new_share=.5)
    states=topic_states([topic('Only')],[],[],{},'2026-10-15',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=60)
    assert plan['questions']==60 and plan['distribution']['adjusted']


def test_urgent_reviews_do_not_silently_override_requested_ratio():
    p=AdaptiveProfile(new_share=.5,max_questions=120,max_topics=5)
    events=[session('R'+str(i),day='2026-09-01',correct=0) for i in range(5)]
    plan=allocate_day(mixed_states(p,events),p,None,'normal',[],'2026-10-15',question_target=120)
    assert sum(i['questions'] for i in plan['items'] if i['topic_id'].startswith('N'))==60
