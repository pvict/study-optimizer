from ui_actions import confirm_action
from copy import deepcopy
from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from osler.study_calendar_ui import _day_state, _shift_month, _month_label, _day_area_chips


TODAY = date(2026, 10, 15)


@pytest.mark.parametrize('day,plan,state', [
    (TODAY, None, 'semplano'),
    (TODAY, {'kind': 'normal', 'items': []}, 'hoje'),
    (TODAY, {'kind': 'normal', 'done_questions': 10}, 'feito'),
    (TODAY, {'routine_override': {'mode': 'mock_reserved'}}, 'simulado'),
    (TODAY, {'routine_override': {'mode': 'final_rest'}}, 'descanso'),
    (TODAY, {'kind': 'descanso'}, 'descanso'),
    (TODAY, {'not_started': True}, 'semplano'),
    (date(2026, 10, 14), {'historical': True, 'has_plan': False, 'done_questions': None}, 'semplano'),
    (date(2026, 10, 14), {'historical': True, 'has_plan': False, 'done_questions': 12}, 'feito'),
    (date(2026, 10, 16), {'questions': 12, 'items': [{'path': ['A', 'B']}]}, 'previsao'),
    (date(2026, 10, 16), {'questions': None, 'items': []}, 'semplano'),
])
def test_day_state_uses_observed_work_and_explicit_overrides(day, plan, state):
    original = deepcopy(plan)
    assert _day_state(day, plan, TODAY) == state
    assert plan == original


def test_month_navigation_keeps_day_when_possible_clamps_end_and_bounds():
    assert _shift_month(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert _shift_month(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert _shift_month(date(2026, 1, 15), -1) == date(2025, 12, 15)
    assert _shift_month(TODAY, -1, date(2026, 10, 1), date(2027, 1, 1)) == date(2026, 10, 1)
    assert _month_label(TODAY) == 'Outubro 2026'


def test_area_chips_are_unique_limited_and_html_escaped():
    plan = {'items': [{'path': ['<img src=x>', 'Tema']}, {'path': ['<img src=x>', 'Outro']},
                      {'path': ['Pediatria', 'Tema']}, {'path': ['Clínica Médica', 'Tema']}]}
    text = _day_area_chips(plan)
    assert text.count('<span ') == 2
    assert '&lt;img src=x&gt;' in text and '<img' not in text
    assert 'Pediatria' in text and 'Clínica Médica' not in text
    assert _day_area_chips(None) == ''


def _app(service):
    app = AppTest.from_string('''
import streamlit as st
from osler.study_calendar_ui import render_calendar
def record(*args): st.session_state['record_args'] = args
def review(*args): st.session_state['review_args'] = args
render_calendar(st.session_state.service, record, review)
''', default_timeout=60)
    app.session_state['service'] = service
    return app.run()


def test_calendar_keeps_selection_navigation_and_record_callback(tmp_path, monkeypatch):
    from test_daily_swaps import service_fixture
    service, _ = service_fixture(tmp_path, monkeypatch)
    app = _app(service)
    assert not app.exception
    assert app.radio(key='calendar_mode').value == 'Semana'
    assert len([b for b in app.button if b.key and b.key.startswith('calendar_cell_')]) == 7
    action = next(b for b in app.button if b.key and b.key.startswith('calendar_record_'))
    action.click().run()
    assert not app.exception and app.session_state['record_args'][0] == action.key.removeprefix('calendar_record_')
    app.button(key='calendar_next_month').click().run()
    assert not app.exception and app.date_input(key='calendar_reference').value == date(2026, 11, 15)
    assert app.session_state['calendar_selected'] == '2026-11-15'
    app.button(key='calendar_previous_month').click().run()
    assert not app.exception and app.session_state['calendar_selected'] == '2026-10-15'
    app.button(key='calendar_cell_2026-10-16').click().run()
    for mode in ['Semana', 'Mês', 'Agenda']:
        app.radio(key='calendar_mode').set_value(mode).run()
        assert not app.exception and app.session_state['calendar_selected'] == '2026-10-16'
        assert app.radio(key='calendar_mode').value == mode
    assert any(e.label.startswith('Reorganizar · ') and not e.proto.expanded for e in app.expander)


def test_unknown_total_and_external_text_stay_honest():
    app = AppTest.from_string('''
from datetime import date
from osler.study_calendar_ui import _day_summary
_day_summary(date(2026,10,16), {'kind':'normal','questions':None,'items':[{'path':['<script>x</script>','Tema']}], 'forecast_mode':'next_contact'}, {'exam_dates':[], 'backlog':[]}, date(2026,10,15))
''').run()
    assert not app.exception
    assert any('não informada' in c.value for c in app.caption)
    assert not any('0 questões' in c.value for c in app.caption)
    assert all('<script>' not in str(h.value) for h in app.get('html'))


def test_calendar_swap_preserves_questions_and_results(tmp_path, monkeypatch):
    from test_daily_swaps import service_fixture
    service, _ = service_fixture(tmp_path, monkeypatch)
    before = deepcopy(service.store.active('2026-10-15'))
    app = _app(service)
    app.button(key='swap_open_calendar_A').click().run()
    assert not app.exception
    confirm_action(app.button(key='swap_suggest_calendar_A').click().run())
    assert not app.exception
    plan = service.overview('2026-10-15')['plan']
    assert plan['items'][0]['topic_id'] == 'B'
    assert plan['target_questions'] == 20
    assert service.store.active('2026-10-15') == before


def test_calendar_balanced_parts_keep_review_and_complement_callbacks(tmp_path, sample_pdf):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    from osler.study_models import AdaptiveProfile, StudyEntry
    repo, *_, topic = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    service.store.save_profile(AdaptiveProfile(review_strategy='balanced_v2', target_accuracy=95), 0)
    service.save_entry(StudyEntry(topic.qbank.path, '2026-10-08', 19, 17, confident_correct=15), 'origin')
    before = deepcopy(service.store.active('2026-10-15'))
    app = _app(service)
    lot = next(b for b in app.button if b.key and b.key.startswith('calendar_lot_'))
    lot.click().run()
    assert not app.exception and app.session_state['review_args'][0]['questions'] == 4
    complement = next(b for b in app.button if b.key and b.key.startswith('calendar_complement_'))
    complement.click().run()
    assert not app.exception and app.session_state['record_args'][0] == complement.key.removeprefix('calendar_complement_')
    assert service.store.active('2026-10-15') == before


def test_calendar_completion_can_be_reversed_without_recording_answers(tmp_path, monkeypatch):
    from test_planner_completion import setup_plan, DAY
    service, _ = setup_plan(tmp_path, monkeypatch)
    before = deepcopy(service.store.events())
    app = _app(service)
    assert not app.exception
    confirm_action(app.button(key='calendar_skip_complement_A').click().run())
    assert not app.exception
    assert not any(i['topic_id'] == 'A' for i in service.overview(DAY)['plan']['items'])
    confirm_action(next(b for b in app.button if b.label == 'Desfazer dispensa').click().run())
    assert not app.exception and app.button(key='calendar_skip_complement_A')
    assert service.store.events() == before


@pytest.mark.parametrize('action', ['calendar_risks_2026-10-21', 'prevent_selected_day'])
def test_prevention_actions_open_their_collapsed_destination(tmp_path, sample_pdf, action):
    from test_study_prevention import prevention_service
    service, _ = prevention_service(tmp_path, sample_pdf)
    app = _app(service)
    app.date_input(key='calendar_reference').set_value(date(2026, 10, 21)).run()
    assert not app.exception
    assert not next(e for e in app.expander if e.label == 'Mais opções do calendário').proto.expanded
    app.button(key=action).click().run()
    assert not app.exception
    assert app.toggle(key='prevention_enabled').value
    assert next(e for e in app.expander if e.label == 'Mais opções do calendário').proto.expanded
    assert any(h.value == 'Prevenir atrasos nas próximas semanas' for h in app.subheader)
