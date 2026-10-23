from dataclasses import FrozenInstanceError,replace
import pytest
from osler.storage import Repository


def test_parameters_are_immutable_and_selection_is_explicit_versioned(tmp_path):
    from osler.algorithm_parameters import AlgorithmParameters,ParameterStore
    p=AlgorithmParameters()
    assert (p.first_interval,p.second_interval,p.max_contact_gap,p.failure_interval)==(7,14,30,3)
    with pytest.raises(FrozenInstanceError): p.first_interval=8
    store=ParameterStore(Repository(tmp_path))
    assert store.current()['parameters'].version==1
    store.register(replace(p,version=2),expected_latest=1)
    assert store.current()['parameters'].version==1
    first=store.select(2,expected_id=0)
    assert store.current()['parameters'].version==2
    with pytest.raises(ValueError): store.select(1,expected_id=0)
    store.select(1,expected_id=first)
    assert len(store.history())==2
    with pytest.raises(ValueError): store.register(replace(p,first_interval=10),expected_latest=2)


def test_schema12_parameters_and_weekly_roundtrip(tmp_path):
    from osler.study_storage import StudyStore
    from osler.backups import create_backup,restore_backup,inspect_backup
    from osler.algorithm_parameters import ParameterStore
    repo=Repository(tmp_path/'source'); StudyStore(repo)
    from osler.weekly_review import WeeklyReviewStore
    from osler.algorithm_parameters import V1
    parameters=ParameterStore(repo)
    parameters.register(replace(V1,version=2),expected_latest=1)
    parameters.select(2,0)
    weekly=WeeklyReviewStore(repo)
    weekly.save('2026-10-12',{'blocked':'Plantão','needs_rest':True})
    weekly.save('2026-10-12',{'blocked':'Descanso','needs_rest':False},expected_version=1)
    backup=create_backup(repo)
    assert inspect_backup(backup.read_bytes())['schema_version']==12
    restored=Repository(restore_backup(backup.read_bytes(),tmp_path/'restored'))
    assert ParameterStore(restored).versions()==ParameterStore(repo).versions()
    assert ParameterStore(restored).history()==parameters.history()
    assert WeeklyReviewStore(restored).events()==weekly.events()


def test_v1_payload_cannot_silently_be_changed():
    from osler.algorithm_parameters import V1
    with pytest.raises(ValueError): replace(V1,first_interval=8).validate()
