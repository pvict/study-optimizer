from dataclasses import replace
import csv
from io import StringIO

import pytest

from osler.storage import Repository
from osler.study_models import StudyEntry
from osler.study_storage import StudyStore
from osler.study_errors import ErrorStore, StudyError


def error(**changes):
    return replace(StudyError(['Clínica Médica', 'Diabetes'], '2026-10-15',
                             'lacuna_de_conteudo', 'Rever o conceito de basal'), **changes)


@pytest.mark.parametrize('changes', [
    {'path': []}, {'path': ['']}, {'path': 'Diabetes'}, {'day': '2026-02-30'},
    {'cause': 'preguica'}, {'note': 'a' * 281}, {'note': None}, {'critical': 1},
    {'source_session_id': ''}, {'flashcard_hint': 'a' * 281},
])
def test_error_rejects_invalid_data(changes):
    with pytest.raises(ValueError):
        error(**changes).validate()


def test_versions_keep_original_and_reject_stale_changes(tmp_path):
    store = ErrorStore(Repository(tmp_path))
    original = store.save(error())
    changed = store.save(error(note='Conceito corrigido'), error_key=original['error_key'], expected_version=1)
    assert changed['version'] == 2
    assert store.events()[0]['note'] == 'Rever o conceito de basal'
    assert changed['path'] == ['clinica medica', 'diabetes']
    with pytest.raises(ValueError, match='atualiz|mud'):
        store.save(error(), error_key=original['error_key'], expected_version=1)
    with pytest.raises(ValueError, match='atualiz|mud'):
        store.resolve(original['error_key'], 1)
    resolved = store.resolve(original['error_key'], 2)
    assert resolved['action'] == 'resolve' and resolved['version'] == 3
    assert not store.active('2026-10-15')
    assert store.events()[2]['note'] == 'Conceito corrigido'
    with pytest.raises(ValueError):
        store.resolve(original['error_key'], 3)
    reopened = store.save(error(), error_key=original['error_key'], expected_version=3)
    store.void(reopened['error_key'], 4)
    assert not store.active('2026-10-15')
    assert [e['action'] for e in store.events()] == ['save', 'save', 'resolve', 'save', 'void']


def test_adverse_signal_only_counts_distinct_open_keys_same_cause_in_last_30_days(tmp_path):
    store = ErrorStore(Repository(tmp_path))
    a = store.save(error(day='2026-09-15'))
    store.save(error(day='2026-10-15', cause='chute'))
    assert not store.adverse_paths('2026-10-15')
    b = store.save(error(path=['  CLÍNICA MÉDICA ', 'Diabetes'], day='2026-10-15'))
    assert store.adverse_paths('2026-10-15') == [('clinica medica', 'diabetes')]
    store.resolve(a['error_key'], 1)
    assert not store.adverse_paths('2026-10-15')
    store.save(error(), error_key=b['error_key'], expected_version=1)
    assert not store.adverse_paths('2026-10-15')
    critical = store.save(error(day='2026-01-01', critical=True))
    assert store.adverse_paths('2026-10-15') == [('clinica medica', 'diabetes')]
    store.void(critical['error_key'], 1)
    assert not store.adverse_paths('2026-10-15')
    assert not store.active('2025-12-31')


def test_old_recurring_errors_and_future_records_do_not_signal(tmp_path):
    store = ErrorStore(Repository(tmp_path))
    store.save(error(day='2026-09-14'))
    store.save(error(day='2026-09-14'))
    assert not store.adverse_paths('2026-10-15')
    assert not store.active('2026-09-13')
    with pytest.raises(ValueError):
        store.save(error(day='2026-10-16'))


def test_catalog_requires_unique_specific_topic_and_session_path_matches(tmp_path):
    repo = Repository(tmp_path)
    study = StudyStore(repo)
    study.save_batch([('block-1', StudyEntry(['Clínica Médica', 'Diabetes'], '2026-10-15', 10, correct=5), 0)])
    catalog = [{'path': ['Clínica Médica'], 'is_leaf': False},
               {'path': ['Clínica Médica', 'Diabetes'], 'is_leaf': True}]
    store = ErrorStore(repo, catalog=catalog)
    saved = store.save(error(source_session_id='block-1'))
    assert saved['source_session_id'] == 'block-1'
    for changes in [{'path': ['Clínica Médica']}, {'path': ['Ausente']},
                    {'source_session_id': 'missing'}, {'path': ['Outra'], 'source_session_id': 'block-1'}]:
        with pytest.raises(ValueError):
            store.save(error(**changes))
    with pytest.raises(ValueError):
        ErrorStore(repo).save(error(path=['Outra'], source_session_id='block-1'))
    study.void('block-1', 1)
    with pytest.raises(ValueError):
        store.save(error(source_session_id='block-1'))
    with pytest.raises(ValueError):
        ErrorStore(repo, catalog=catalog + [catalog[-1]]).save(error())


def test_csv_includes_history_and_escapes_formula_cells(tmp_path):
    store = ErrorStore(Repository(tmp_path))
    saved = store.save(error(note='=1+1', flashcard_hint='@formula'))
    store.resolve(saved['error_key'], 1)
    rows = list(csv.DictReader(StringIO(store.export_csv().decode('utf-8-sig')), delimiter=';'))
    assert [r['action'] for r in rows] == ['save', 'resolve']
    assert rows[0]['note'] == "'=1+1" and rows[0]['flashcard_hint'] == "'@formula"


def test_error_store_never_decreases_newer_schema(tmp_path):
    repo = Repository(tmp_path)
    ErrorStore(repo)
    with repo._connection() as db:
        db.execute('PRAGMA user_version=12')
    ErrorStore(repo)
    with repo._connection() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 12


def test_read_only_adverse_helper_does_not_initialize_or_migrate(tmp_path):
    from osler.study_errors import adverse_error_paths
    repo = Repository(tmp_path)
    with repo._connection() as db:
        before = db.execute('PRAGMA user_version').fetchone()[0]
    assert adverse_error_paths(repo, '2026-10-15') == []
    with repo._connection() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == before
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='study_errors'").fetchone()
    store = ErrorStore(repo)
    store.save(error(critical=True))
    assert adverse_error_paths(repo, '2026-10-15') == [('clinica medica', 'diabetes')]


def test_linked_error_must_use_session_day(tmp_path):
    repo = Repository(tmp_path)
    StudyStore(repo).save_batch([('block-1', StudyEntry(['Clínica Médica', 'Diabetes'], '2026-10-14', 10, correct=5), 0)])
    with pytest.raises(ValueError, match='sessão|bloco'):
        ErrorStore(repo).save(error(source_session_id='block-1'))
