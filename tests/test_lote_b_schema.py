from osler.storage import Repository
from osler.study_storage import StudyStore
from osler.database_check import check_database
from osler.study_errors import ErrorStore,StudyError
from osler.mock_exams import MockExamStore,MockExam
from osler.backups import create_backup,inspect_backup,restore_backup
import pytest


def test_schema11_is_additive_and_stores_do_not_downgrade(tmp_path):
    repo=Repository(tmp_path)
    StudyStore(repo)
    with repo._connection() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==12
        for name in ('study_errors','mock_exams','mock_exam_areas','mock_exam_topics'):
            assert db.execute("SELECT name FROM sqlite_master WHERE name=?",(name,)).fetchone()
    assert check_database(repo.db_path)[0]==12
    StudyStore(repo)
    assert check_database(repo.db_path)[0]==12


def test_schema11_backup_roundtrip_keeps_new_events_and_children(tmp_path):
    repo=Repository(tmp_path/'source')
    error=ErrorStore(repo).save(StudyError(['Área','Tema'],'2026-10-15','chute',critical=True))
    ErrorStore(repo).resolve(error['error_key'],1)
    mocks=MockExamStore(repo)
    mocks.save(MockExam('2026-10-15',20,15,areas=[{'area':'Clínica','questions':10,'correct':8}],
                        topics=[{'path':['Área','Tema'],'questions':5,'correct':4}]))
    backup=create_backup(repo)
    assert inspect_backup(backup.read_bytes())['schema_version']==12
    restored=Repository(restore_backup(backup.read_bytes(),tmp_path/'restored'))
    assert ErrorStore(restored).events()==ErrorStore(repo).events()
    assert MockExamStore(restored).events()==mocks.events()
    with repo._connection() as a,restored._connection() as b:
        for table in ('mock_exam_areas','mock_exam_topics'):
            assert [tuple(r) for r in a.execute('SELECT * FROM '+table)]==[tuple(r) for r in b.execute('SELECT * FROM '+table)]


def test_database_check_rejects_invalid_error_or_mock_children(tmp_path):
    repo=Repository(tmp_path)
    ErrorStore(repo).save(StudyError(['Área','Tema'],'2026-10-15','chute'))
    with repo._connection() as db: db.execute("UPDATE study_errors SET cause='invalido'")
    with pytest.raises(ValueError): check_database(repo.db_path)
