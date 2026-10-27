from datetime import date
from pathlib import Path
import tempfile

import pytest

from scripts.seed_demo_data import seed_demo_data


@pytest.mark.parametrize('name',['data','data/descendente'])
def test_seed_refuses_data_paths_before_writing(tmp_path,name):
    target=tmp_path/name
    with pytest.raises(ValueError):seed_demo_data(target,date(2026,10,15))
    assert not target.exists()


def test_seed_refuses_existing_database_and_does_not_touch_it(tmp_path):
    target=tmp_path/'existing';target.mkdir();original=target/'osler.sqlite3';original.write_bytes(b'preservar')
    with pytest.raises(ValueError):seed_demo_data(target,date(2026,10,15))
    assert original.read_bytes()==b'preservar' and len(list(target.iterdir()))==1


def test_seed_refuses_existing_folder_and_destination_outside_system_temp(tmp_path,project_root):
    with pytest.raises(ValueError):seed_demo_data(tmp_path,date(2026,10,15))
    target=project_root/'seed-demo-must-not-exist'
    with pytest.raises(ValueError):seed_demo_data(target,date(2026,10,15))
    assert not target.exists()


def test_seed_refuses_parent_database_and_symlink(tmp_path):
    parent=tmp_path/'parent';parent.mkdir();(parent/'osler.sqlite3').write_bytes(b'original')
    with pytest.raises(ValueError):seed_demo_data(parent/'child',date(2026,10,15))
    real=tmp_path/'real';real.mkdir();link=tmp_path/'link'
    try:link.symlink_to(real,target_is_directory=True)
    except OSError:pytest.skip('Criação de symlink indisponível no Windows.')
    with pytest.raises(ValueError):seed_demo_data(link/'child',date(2026,10,15))
    assert list(real.iterdir())==[]


def test_seed_generates_only_synthetic_scenario_through_existing_models(tmp_path):
    from osler.storage import Repository
    from osler.adaptive_service import AdaptiveService
    from osler.study_errors import ErrorStore
    from osler.exam_goals import ExamGoals
    from osler.mock_exams import MockExams
    target=tmp_path/'demo';result=seed_demo_data(target,date(2026,10,15));repo=Repository(target)
    assert result['synthetic'] is True and result['topics']==40
    assert len(repo.list_reports())==2
    service=AdaptiveService(repo);topics,_=service.catalog('2026-10-15')
    assert len(topics)==40 and len({t['path'][0] for t in topics})==5
    assert len({r['entry']['day'] for r in service.store.active('2026-10-15')})==13
    assert any(v['kind']=='descanso' for v in service.store.days().values())
    assert len(ErrorStore(repo).active('2026-10-15'))==3
    assert len(ExamGoals(repo).active())==1
    assert len(MockExams(repo).active())==1
    assert len(MockExams(repo).active()[0]['exam']['areas'])==5
    assert (target/'SYNTHETIC-DEMO.json').is_file()


@pytest.mark.parametrize('url',['https://example.com:8602/','http://127.0.0.1:8501/','http://user:secret@127.0.0.1:8602/'])
def test_capture_refuses_remote_or_user_app_url(url):
    from scripts.capture_bento import validate_url
    with pytest.raises(ValueError):validate_url(url)


def test_seed_guard_is_compatible_with_python311_without_is_junction(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'is_junction',None,raising=False)
    result=seed_demo_data(tmp_path/'portable',date(2026,10,15))
    assert result['synthetic'] is True


def test_indirect_ancestor_is_rejected_even_when_windows_cannot_create_test_links(tmp_path,monkeypatch):
    real=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda p:p==tmp_path or real(p))
    with pytest.raises(ValueError):seed_demo_data(tmp_path/'indirect',date(2026,10,15))
    assert not (tmp_path/'indirect').exists()
