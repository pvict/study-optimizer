from dataclasses import replace

import pytest

from osler.study_models import StudyEntry, AdaptiveProfile
from osler.study_storage import StudyStore
from osler.storage import Repository


def entry(**kwargs):
    return StudyEntry(**{'path':['Clínica','Tema'], 'day':'2026-10-15', 'questions':10, 'correct':8, **kwargs})


def test_sessions_versions_preserve_identical_real_blocks_and_corrections(tmp_path):
    store = StudyStore(Repository(tmp_path))
    store.save_batch([('one', entry(), 0), ('two', entry(), 0)])
    assert len(store.active('2026-10-15')) == 2
    assert store.save_batch([('one', entry(), 0)])
    assert len(store.events()) == 2
    store.save_batch([('one', entry(correct=9), 1)])
    assert sum(s['entry']['correct'] for s in store.active('2026-10-15')) == 17
    with pytest.raises(ValueError):
        store.save_batch([('one', entry(correct=7), 1)])
    store.void('one', 2)
    assert len(store.active('2026-10-15')) == 1
    assert len(store.events()) == 4


def test_import_validation_is_atomic_and_percentage_never_invents_exact_correct(tmp_path):
    store = StudyStore(Repository(tmp_path))
    with pytest.raises(ValueError):
        store.save_batch([('ok', entry(), 0), ('bad', entry(correct=11), 0)])
    assert store.events() == []
    approximate = entry(correct=None, percent=85)
    store.save_batch([('approximate', approximate, 0)])
    assert store.active('2026-10-15')[0]['entry']['correct'] is None


def test_contact_and_profile_are_validated_without_fake_performance(tmp_path):
    store = StudyStore(Repository(tmp_path))
    store.save_batch([('contact', entry(kind='contato', questions=0, correct=None), 0)])
    assert store.active('2026-10-15')[0]['entry']['questions'] == 0
    profile = AdaptiveProfile()
    assert profile.target_accuracy == 90
    store.save_profile(profile, 0)
    assert store.profile()['profile']['target_accuracy'] == 90
    with pytest.raises(ValueError):
        store.save_profile(profile, 0)
    with pytest.raises(ValueError):
        replace(profile, institution_weights={'A':-1}).validate()


def test_schema10_backup_roundtrip_preserves_new_and_old_data(tmp_path):
    from osler.backups import create_backup, inspect_backup, restore_backup
    repo = Repository(tmp_path/'data')
    store = StudyStore(repo)
    store.save_batch([('one', entry(), 0)])
    backup = create_backup(repo)
    assert inspect_backup(backup.read_bytes())['schema_version'] == 12
    other = StudyStore(Repository(restore_backup(backup.read_bytes(), tmp_path/'restored')))
    assert other.events() == store.events()
