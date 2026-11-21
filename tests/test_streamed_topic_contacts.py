"""Consultar primeiras datas não exige calcular meses posteriores à última delas."""
from copy import deepcopy
from osler.adaptive_planning import topic_states
from osler.planning import _date
from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile
from osler import topic_contacts
from test_adaptive_planning import topic
from test_mock_schedule import configured


def test_first_contacts_stop_when_every_topic_has_a_date_but_keep_the_full_horizon(tmp_path, sample_pdf, monkeypatch):
    service, _ = configured(tmp_path, sample_pdf)
    view = service.overview('2026-10-15')
    horizon = min(548, (_date(view['profile']['exam_date']) - _date(view['date'])).days + 1)
    full = forecast_calendar(view['planning_states'], AdaptiveProfile(**view['profile']), view['date'], horizon,
                             view['sessions'], service.store.days(), view['plan'], view['agenda'], next_contact_only=True)
    expected = {}
    for plan in full:
        for item in plan['items']:
            expected.setdefault(item['topic_id'], {'date': plan['date'], 'stage': item['stage'], 'questions': item['questions']})
    from osler import study_calendar
    visited = []
    def stream(*args, **kwargs):
        for plan in study_calendar.iter_forecast_calendar(*args, **kwargs):
            visited.append(plan['date'])
            yield plan
    monkeypatch.setattr(topic_contacts, 'iter_forecast_calendar', stream, raising=False)
    before = deepcopy(view)
    forecast = topic_contacts.forecast_topic_contacts(service, view)
    assert forecast['contacts'] == expected
    assert forecast['end'] == full[-1]['date']
    assert forecast['coverage']['scheduled'] == forecast['coverage']['total']
    assert 0 < len(visited) < horizon
    assert view == before


def test_unassignable_topic_still_examines_the_full_horizon(tmp_path, sample_pdf, monkeypatch):
    service, _ = configured(tmp_path, sample_pdf)
    for day in ['2026-10-15', '2026-10-16', '2026-10-17']:
        service.configure_day(day, 40, 'descanso', 0)
    view = service.overview('2026-10-15')
    view['profile']['exam_date'] = '2026-10-17'
    forecast = topic_contacts.forecast_topic_contacts(service, view)
    assert forecast['end'] == '2026-10-17'
    assert forecast['coverage']['scheduled'] < forecast['coverage']['total']
    assert forecast['unassigned_ids']


def test_dose_is_not_recomputed_on_a_day_when_the_topic_is_ineligible(monkeypatch):
    from osler import study_calendar
    profile = AdaptiveProfile(start_date='2026-10-01')
    states = topic_states([topic('Later')], [], [], {}, '2026-10-15', profile)
    states[0].update(next_review='2026-10-17', theme_review_due='2026-10-17', review_committed=True)
    calls = []
    original = study_calendar.practice_state
    def dose(state, day, profile):
        calls.append(day)
        return original(state, day, profile)
    monkeypatch.setattr(study_calendar, 'practice_state', dose)
    forecast_calendar(states, profile, '2026-10-15', 3, [], {})
    assert '2026-10-16' not in calls
    assert '2026-10-17' in calls
