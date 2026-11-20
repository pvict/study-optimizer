import csv
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest


def database(tmp_path):
    path = tmp_path / 'active' / 'osler.sqlite3'
    path.parent.mkdir()
    with sqlite3.connect(path) as db:
        db.executescript('''
            PRAGMA user_version=9;
            CREATE TABLE study_events(id INTEGER PRIMARY KEY, session_id TEXT, version INTEGER, action TEXT, payload TEXT);
            CREATE TABLE study_plan_runs(id INTEGER PRIMARY KEY, payload TEXT);
        ''')
    return path


def add(db, sid, day, *, path=None, version=1, action='save', **fields):
    entry = dict(path=path or ['Clínica', 'Tema'], day=day, kind='bloco', mode='novas',
                 questions=10, correct=5, confident_correct=4, minutes=None)
    entry.update(fields)
    db.execute('INSERT INTO study_events(session_id,version,action,payload) VALUES(?,?,?,?)',
               (sid, version, action, json.dumps(entry)))


def test_empty_and_old_database_produce_reports_without_changes(tmp_path):
    from osler.calibration_analysis import write_report
    path = tmp_path / 'active' / 'osler.sqlite3'
    path.parent.mkdir()
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA user_version=2')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    md, csv_path = write_report(path, tmp_path / 'reports', '2026-10-15')
    assert 'Dados insuficientes' in md.read_text(encoding='utf-8')
    assert list(csv.DictReader(csv_path.open(encoding='utf-8-sig')))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert db.execute('SELECT name FROM sqlite_master').fetchall() == []


def test_lag_bands_links_versions_and_denominators_are_not_overlapped(tmp_path):
    from osler.calibration_analysis import analyze_database
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        add(db, 'initial', '2026-10-01', correct=9, confident_correct=8)
        add(db, 'initial', '2026-10-01', version=2, correct=5, confident_correct=4)
        add(db, 'unlinked', '2026-10-03', mode='repetidas', correct=2)
        add(db, 'linked', '2026-10-04', mode='repetidas', review_of='initial', correct=8)
        add(db, 'linked-again', '2026-10-08', mode='repetidas', review_of='initial', correct=9)
        add(db, 'approx', '2026-10-04', correct=None, percent=99)
        add(db, 'snapshot', '2026-10-04', kind='acumulado', questions=999, correct=999)
        add(db, 'future', '2026-10-16', questions=100, correct=100)
        add(db, 'void', '2026-10-01')
        add(db, 'void', '2026-10-01', version=2, action='void')
    before = path.read_bytes()
    result = analyze_database(path, '2026-10-15')
    rows = [r for r in result['rows'] if r['measurement'] == 'repeat_accuracy' and r['n_attempts']]
    assert len(rows) == 1
    assert (rows[0]['lag_min_days'], rows[0]['lag_max_days']) == (2, 4)
    assert rows[0]['initial_band'] == '<60%'
    assert rows[0]['linkage'] == 'review_of'
    assert (rows[0]['n_attempts'], rows[0]['n_sessions'], rows[0]['n_topicdays']) == (10, 1, 1)
    assert rows[0]['correct'] == 8
    assert 0 < rows[0]['wilson_low_pct'] < 80 < rows[0]['wilson_high_pct'] < 100
    confidence = [r for r in result['rows'] if r['measurement'] == 'confidence_next_review' and r['n_attempts']]
    assert confidence[0]['lag_days'] == 3
    assert confidence[0]['confidence_band'] == '<60%'
    assert confidence[0]['correct'] == 8
    assert path.read_bytes() == before


def test_nearest_prior_is_a_topic_association_not_item_identity(tmp_path):
    from osler.calibration_analysis import analyze_database
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        add(db, 'old', '2026-09-01', correct=10, confident_correct=10)
        add(db, 'first', '2026-10-01', correct=2, confident_correct=0)
        add(db, 'near', '2026-10-01', correct=7, confident_correct=6)
        add(db, 'same-day', '2026-10-08', correct=3, confident_correct=2)
        add(db, 'repeat', '2026-10-08', mode='repetidas', correct=9)
    result = analyze_database(path, '2026-10-15')
    row = next(r for r in result['rows'] if r['measurement'] == 'repeat_accuracy' and r['n_attempts'])
    assert (row['lag_min_days'], row['lag_max_days']) == (5, 9)
    assert (row['initial_band'], row['linkage']) == ('60–79%', 'same_topic_nearest_prior')
    assert 'os blocos tratam do mesmo assunto' in result['markdown']


def test_unlinked_pairs_reuse_normalized_topic_paths(tmp_path, monkeypatch):
    from osler import calibration_analysis
    path = database(tmp_path)
    count = 40
    with sqlite3.connect(path) as db:
        for i in range(count):
            topic = ['Clínica', f'Tema {i}']
            add(db, f'initial-{i}', '2026-10-01', path=topic, confident_correct=None)
            add(db, f'repeat-{i}', '2026-10-09', path=topic, mode='repetidas')
    normalize = calibration_analysis.normalize_path
    calls = 0

    def count_normalizations(path):
        nonlocal calls
        calls += 1
        return normalize(path)

    monkeypatch.setattr(calibration_analysis, 'normalize_path', count_normalizations)
    result = calibration_analysis.analyze_database(path, '2026-10-15')
    assert result['repeat_pair_counts'] == {'included': count, 'matched': count}
    assert calls <= 6 * count


def test_review_lags_include_eight_days_and_group_inclusive_boundaries(tmp_path):
    from osler.calibration_analysis import write_report
    path = database(tmp_path)
    first = date(2026, 9, 1)
    lags = [1, 2, 4, 5, 7, 8, 9, 10, 18, 19, 25, 26, 35, 36]
    with sqlite3.connect(path) as db:
        for lag in lags:
            topic = ['Clínica', f'Tema {lag}']
            add(db, f'source-{lag}', first.isoformat(), path=topic)
            add(db, f'repeat-{lag}', (first + timedelta(days=lag)).isoformat(), path=topic,
                review_of=f'source-{lag}', mode='repetidas', correct=8)
    md, target = write_report(path, tmp_path / 'reports', '2026-10-15')
    with target.open(encoding='utf-8-sig') as file:
        rows = list(csv.DictReader(file))
    observed = [r for r in rows if r['measurement'] == 'repeat_accuracy']
    assert [(r['lag_min_days'], r['lag_max_days'], r['n_sessions']) for r in observed] == [
        ('2', '4', '2'), ('5', '9', '4'), ('10', '18', '2'), ('19', '25', '2'), ('26', '35', '2'),
    ]
    middle = observed[1]
    assert (middle['lag_days'], middle['n_attempts'], middle['correct'], middle['n_topicdays']) == ('', '40', '32', '4')
    assert {int(r['lag_days']) for r in rows if r['measurement'] == 'confidence_next_review'} == set(lags)
    report = md.read_text(encoding='utf-8')
    assert '5–9 dias' in report
    assert '12 de 14 pares' in report
    assert 'desempenho anterior' in report


def test_parameter_settings_display_calibration_on_request_without_writing(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from osler.algorithm_parameters import ParameterStore
    from osler.planner_service import today_local
    from osler.storage import Repository

    repo = Repository(tmp_path)
    ParameterStore(repo)
    repeat_day = today_local()
    first_day = repeat_day - timedelta(days=8)
    with sqlite3.connect(repo.db_path) as db:
        entries = [
            ('first', dict(day=first_day.isoformat(), mode='novas', correct=7, confident_correct=6)),
            ('repeat', dict(day=repeat_day.isoformat(), mode='repetidas', correct=8, review_of='first')),
        ]
        for session, entry in entries:
            entry.update(path=['Clínica', 'Tema'], kind='bloco', questions=10)
            db.execute('INSERT INTO study_events(session_id,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                       (session, 1, 'save', json.dumps(entry), entry['day']))
    monkeypatch.setenv('OSLER_TEST_CALIBRATION_ROOT', str(tmp_path))
    app = AppTest.from_string("""
import os
from types import SimpleNamespace
from osler.parameter_ui import render_parameter_settings
from osler.storage import Repository
render_parameter_settings(SimpleNamespace(repository=Repository(os.environ['OSLER_TEST_CALIBRATION_ROOT'])))
""").run()
    assert not app.dataframe and not app.exception
    before = repo.db_path.read_bytes()
    app.button(key='parameter_show_calibration').click().run()
    assert not app.exception and not app.error and len(app.dataframe) == 1
    row = app.dataframe[0].value.iloc[0]
    assert (row['De (dias)'], row['Até (dias)'], row['Acertos'], row['Questões'], row['Sessões']) == (5, 9, 8, 10, 1)
    assert repo.db_path.read_bytes() == before


def test_time_is_weighted_modes_separate_and_csv_cells_safe(tmp_path):
    from osler.calibration_analysis import write_report
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        add(db, 'one', '2026-10-01', path=['=1+1', 'Tema'], questions=10, minutes=10)
        add(db, 'two', '2026-10-02', path=['=1+1', 'Tema'], questions=30, minutes=90)
        add(db, 'repeat', '2026-10-03', mode='repetidas', minutes=50)
        add(db, 'mock-import', '2026-10-03', minutes=1000)
    _, target = write_report(path, tmp_path / 'reports', '2026-10-15')
    rows = list(csv.DictReader(target.open(encoding='utf-8-sig')))
    row = next(r for r in rows if r['measurement']=='time_per_question' and r['area']=="'=1+1")
    assert float(row['value']) == 2.5
    assert row['n_attempts'] == '40'
    assert row['mode'] == 'novas'
    assert row['wilson_low_pct'] == ''


def test_adherence_latest_plan_caps_per_topicday_and_waives_mock_day(tmp_path):
    from osler.calibration_analysis import analyze_database
    path = database(tmp_path)
    def plan(day, n):
        return dict(kind='daily_schedule', plan=dict(date=day, items=[dict(path=['Clínica', 'Tema'], questions=n)]))
    with sqlite3.connect(path) as db:
        for payload in [plan('2026-10-01', 99), plan('2026-10-01', 20), plan('2026-10-02', 10),
                        dict(kind='reschedule.apply', created_day='2026-10-01', overrides={'2026-10-02': {'mode':'mock_day'}})]:
            db.execute('INSERT INTO study_plan_runs(payload) VALUES(?)', (json.dumps(payload),))
        add(db, 'one', '2026-10-01', questions=30)
        add(db, 'accumulated', '2026-10-01', kind='acumulado', questions=200)
    result = analyze_database(path, '2026-10-15')
    questions = next(r for r in result['rows'] if r['measurement']=='adherence_questions')
    blocks = next(r for r in result['rows'] if r['measurement']=='adherence_topicdays')
    assert (questions['numerator'], questions['denominator'], questions['value']) == (20, 20, 100)
    assert (blocks['numerator'], blocks['denominator']) == (1, 1)
    assert result['waived_days'] == ['2026-10-02']


def test_output_cannot_touch_active_directory_or_overwrite_and_missing_db_is_not_created(tmp_path):
    from osler.calibration_analysis import write_report
    path = database(tmp_path)
    with pytest.raises(ValueError, match='pasta do banco'):
        write_report(path, path.parent / 'analysis', '2026-10-15')
    write_report(path, tmp_path / 'reports', '2026-10-15')
    with pytest.raises(FileExistsError):
        write_report(path, tmp_path / 'reports', '2026-10-15')
    missing = tmp_path / 'missing.sqlite3'
    with pytest.raises(FileNotFoundError):
        write_report(missing, tmp_path / 'missing-output', '2026-10-15')
    assert not missing.exists()
    assert not (tmp_path / 'missing-output').exists()


def test_cli_works_with_empty_sqlite(tmp_path):
    path = database(tmp_path)
    command = [sys.executable, str(Path(__file__).parents[1] / 'scripts' / 'analise_calibracao.py'),
               '--db', str(path), '--output', str(tmp_path / 'reports'), '--as-of', '2026-10-15']
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / 'reports' / 'analise-calibracao-2026-10-15.md').is_file()
