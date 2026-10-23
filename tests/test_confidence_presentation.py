from copy import deepcopy

import pytest

from osler.confidence_presentation import confidence_presentation
from osler.study_statistics import topic_statistics
from test_adaptive_planning import session
from test_study_statistics import state


def measured_rows(snapshot_date='2026-10-14',confident=0):
    current={**state(),'planner_safety':{'observed_date':snapshot_date,'unique_questions':34,'confident_accuracy_pct':73.5}}
    event=session(n=17,correct=11)
    event['entry']['confident_correct']=confident
    rows=topic_statistics([current],[event],'Todo o período','2026-10-15')
    return rows,[event]


def test_display_uses_newer_app_measurement_and_preserves_zero_and_raw_sources():
    rows,sessions=measured_rows(); before=deepcopy((rows,sessions))
    shown=confidence_presentation(rows,sessions,'Todo o período','2026-10-15',include_snapshot=True)
    assert shown[0]['Convicção principal (%)']==0
    assert '17 tentativas' in shown[0]['Base da convicção']
    assert '15/10/2026' in shown[0]['Base da convicção']
    assert shown[0]['Convicção (%)']==73.5
    assert (rows,sessions)==before


def test_newer_snapshot_is_displayed_without_averaging_it_with_app_results():
    rows,sessions=measured_rows('2026-10-16',confident=5)
    # As linhas são obtidas novamente com o novo corte, mantendo as mesmas tentativas.
    shown=confidence_presentation(rows,sessions,'Todo o período','2026-10-16',include_snapshot=True)
    assert shown[0]['Convicção principal (%)']==73.5
    assert '34 questões distintas' in shown[0]['Base da convicção']
    assert '16/10/2026' in shown[0]['Base da convicção']


def test_same_day_prefers_identified_app_measurement_without_claiming_time_order():
    rows,sessions=measured_rows('2026-10-15',confident=5)
    shown=confidence_presentation(rows,sessions,'Todo o período','2026-10-15',include_snapshot=True)
    assert shown[0]['Convicção principal (%)']==pytest.approx(100*5/17)
    assert 'mesmo dia' in shown[0]['Base da convicção']


def test_missing_app_confidence_uses_snapshot_but_period_view_keeps_unknown():
    rows,sessions=measured_rows(confident=None)
    history=confidence_presentation(rows,sessions,'Todo o período','2026-10-15',include_snapshot=True)
    period=confidence_presentation(rows,sessions,'Todo o período','2026-10-15')
    assert history[0]['Convicção principal (%)']==73.5
    assert period[0]['Convicção principal (%)'] is None


def test_period_and_modality_bound_the_app_date_and_denominator():
    current=state()
    older=session(day='2026-10-14',n=20,correct=20); older['entry']['confident_correct']=20
    recent=session(mode='repetidas',n=10,correct=8); recent['entry']['confident_correct']=5
    events=[older,recent]
    rows=topic_statistics([current],events,'Dia','2026-10-15','Repetidas')
    shown=confidence_presentation(rows,events,'Dia','2026-10-15','Repetidas')
    assert shown[0]['Convicção principal (%)']==50
    assert '10 tentativas' in shown[0]['Base da convicção']
    assert '14/10' not in shown[0]['Base da convicção']


def test_future_snapshot_does_not_replace_an_available_app_measurement():
    rows,sessions=measured_rows('2026-10-16',confident=0)
    shown=confidence_presentation(rows,sessions,'Todo o período','2026-10-15',include_snapshot=True)
    assert shown[0]['Convicção principal (%)']==0
    assert shown[0]['Base da convicção'].startswith('App')


def test_imported_zero_is_not_treated_as_missing():
    rows,sessions=measured_rows(confident=None)
    rows[0]['Convicção (%)']=0
    shown=confidence_presentation(rows,sessions,'Todo o período','2026-10-15',include_snapshot=True)
    assert shown[0]['Convicção principal (%)']==0
    assert shown[0]['Base da convicção'].startswith('Osler')
