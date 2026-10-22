"""A dose reage à evidência real; o futuro não recebe acertos inventados."""
from copy import deepcopy

from osler.adaptive_planning import topic_states, allocate_day
from osler.study_models import AdaptiveProfile
from osler.topic_trajectory import topic_trajectory
from test_adaptive_planning import topic, session


def block(day, correct=20, confident=20, n=20, **extra):
    event = session(day=day, n=n, correct=correct, mode='repetidas')
    event['entry'].update(confident_correct=confident, **extra)
    return event


def state(events, day='2026-10-22', **topic_fields):
    return topic_states([{**topic(), **topic_fields}], events, [], {}, day, AdaptiveProfile())[0]


def test_spaced_success_allows_smaller_maintenance_than_one_success():
    once = state([block('2026-10-15')])
    twice = state([block('2026-10-08'), block('2026-10-15')])
    assert twice['recommended_questions'] < once['recommended_questions']
    assert twice['recommended_questions'] >= 10
    assert twice['dose_kind'] == 'maintenance'
    assert twice['performance']['exact_n'] == 0  # repetidas não viram amostra nova


def test_recent_failure_restores_reinforcement_despite_old_success():
    events = [block('2026-10-01'), block('2026-10-08')]
    good = state(events, '2026-10-09')
    bad = state(events + [block('2026-10-15', correct=12, confident=8)])
    assert bad['recommended_questions'] > good['recommended_questions']
    assert bad['dose_kind'] == 'reinforcement'


def test_elapsed_time_alone_never_creates_a_smaller_dose():
    events = [block('2026-10-01'), block('2026-10-08')]
    recent = state(events, '2026-10-09')
    stale = state(events, '2026-12-01')
    assert stale['recommended_questions'] > recent['recommended_questions']
    assert stale['dose_kind'] != 'maintenance'


def test_same_day_unmeasured_and_tiny_contacts_cannot_unlock_maintenance():
    cases = [
        [block('2026-10-15'), block('2026-10-15')],
        [block('2026-10-14'), block('2026-10-15')],
        [block('2026-10-08'), block('2026-10-15', confident=None)],
        [block('2026-10-08'), block('2026-10-15', n=1, correct=1, confident=1)],
        [block('2026-10-08'), block('2026-10-15', review_of='old')],
    ]
    for events in cases:
        assert state(events)['dose_kind'] != 'maintenance'


def test_manual_adverse_evidence_prevents_maintenance():
    events = [block('2026-10-08'), block('2026-10-15')]
    assert state(events, manual_context={'erros_criticos':True})['dose_kind'] == 'reinforcement'


def test_small_or_linked_failure_after_success_still_prevents_maintenance():
    events = [block('2026-10-01'), block('2026-10-08')]
    for extra in [block('2026-10-15', n=1, correct=0, confident=0),
                  block('2026-10-15', correct=10, confident=8, review_of='old')]:
        assert state(events+[extra])['dose_kind'] == 'reinforcement'


def test_ancient_success_cannot_combine_with_one_fresh_success_as_maintenance():
    events = [block('2026-05-01'), block('2026-10-15')]
    assert state(events)['dose_kind'] != 'maintenance'


def test_success_on_repeated_items_cannot_hide_failures_on_new_questions():
    fresh=session(day='2026-10-01',n=20,correct=10)
    events=[fresh,block('2026-10-08'),block('2026-10-15')]
    assert state(events,'2026-10-16')['dose_kind']=='reinforcement'
    assert state(events,'2026-10-16')['performance']['observed']==.5


def test_future_reviews_wait_for_results_instead_of_repeating_current_dose():
    current = state([])
    before = deepcopy(current)
    roadmap = topic_trajectory(current, AdaptiveProfile(), '2026-10-22')
    assert roadmap['steps'][0]['questions'] == current['recommended_questions']
    assert all(s['questions'] is None and s['date'] is None for s in roadmap['steps'][1:])
    assert roadmap['recommended_total'] is None
    assert current == before


def test_theme_trajectory_keeps_theme_date_and_complement_separate_from_error_lot():
    current=state([], total=5)
    current.update(recommended_questions=5, theme_recommended_questions=22,
                   next_review='2026-10-22', theme_review_due='2026-10-29', review_kind='lot_only')
    roadmap=topic_trajectory(current, AdaptiveProfile(), '2026-10-22')
    assert roadmap['steps'][0]['questions']==22
    assert roadmap['steps'][0]['date']=='2026-10-29'
    assert roadmap['complement_per_block']==17
    from osler.topic_trajectory import trajectory_summary
    summary=trajectory_summary([current],AdaptiveProfile(),'2026-10-22',[])
    assert summary['rows'][0]['Complemento por encontro']==17


def test_real_dose_reaches_daily_allocator_without_exceeding_budget():
    events = [block('2026-10-01'), block('2026-10-08')]
    current = state(events, '2026-10-22')
    plan = allocate_day([current], AdaptiveProfile(max_questions=20, new_share=0), None,
                        'normal', [], '2026-10-22', question_target=20)
    assert plan['items'][0]['dose_kind'] == 'maintenance'
    assert plan['items'][0]['recommended_questions'] == current['recommended_questions']
    assert plan['questions'] <= 20
