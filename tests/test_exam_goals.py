from dataclasses import replace
import json
import pytest
from osler.storage import Repository
from osler.study_storage import StudyStore
from osler.study_models import AdaptiveProfile
from osler.exam_goals import ExamTarget,ExamGoals


def target(name='Prova A',day='2027-10-01'):
    return ExamTarget(institution=name,exam_date=day,cutoff_score=75,max_score=100,cutoff_source='Fonte informada no teste')


@pytest.mark.parametrize('changes',[{'cutoff_source':''},{'cutoff_score':101},{'max_score':0},{'cutoff_score':float('nan')},{'exam_date':'2027-02-30'},{'registration_deadline':'x'},{'registration_deadline':False},{'registration_deadline':''},{'registration_deadline':'2027-12-01'},{'cutoff_confidence':'garantido'},{'exam_year':True}])
def test_invalid_exam_target_is_rejected(changes):
    with pytest.raises(ValueError): replace(target(),**changes).validate()


def test_three_exams_versions_concurrency_and_effective_date(tmp_path):
    repo=Repository(tmp_path)
    store=StudyStore(repo)
    exams=ExamGoals(repo)
    a=exams.save(target(),expected_version=0)
    b=exams.save(target('Prova B','2027-09-01'),expected_version=0)
    exams.save(target('Prova C','2027-11-01'),expected_version=0)
    assert len(exams.active())==3
    assert store.profile()['profile']['exam_date']=='2027-09-01'
    store.save_profile(AdaptiveProfile(primary_exam_id=a['target_id']),0)
    assert store.profile()['profile']['exam_date']=='2027-10-01'
    assert store.profile()['configured_profile']['exam_date']=='2027-11-30'
    edited=exams.save(replace(target(),cutoff_score=80),target_id=a['target_id'],expected_version=1)
    assert edited['version']==2
    with pytest.raises(ValueError,match='atualiz|mud'): exams.save(target(),target_id=a['target_id'],expected_version=1)
    with pytest.raises(ValueError,match='atualiz|mud'): exams.void(a['target_id'],1)
    exams.void(a['target_id'],2)
    assert len(exams.active())==2 and len(exams.events())==5
    assert store.profile()['profile']['exam_date']=='2027-09-01'
    assert b['target']['cutoff_score']/b['target']['max_score']==.75


def test_legacy_profile_is_not_rewritten_and_area_defaults_are_compatible(tmp_path):
    repo=Repository(tmp_path)
    store=StudyStore(repo)
    payload=json.dumps({'target_accuracy':88,'exam_date':'2028-05-01'})
    with repo._connection() as db: db.execute('INSERT INTO study_profiles(payload,created_at) VALUES(?,?)',(payload,'test'))
    record=store.profile()
    p=AdaptiveProfile(**record['profile']).validate()
    assert p.target_for_area('Clínica Médica')==88 and p.exam_date=='2028-05-01'
    p=replace(p,area_targets={'Clínica Médica':92}).validate()
    assert p.target_for_area('Clínica Médica')==92 and p.target_for_area('Pediatria')==88
    with pytest.raises(ValueError): replace(p,area_targets={'Clínica Médica':101}).validate()
    with repo._connection() as db: assert db.execute('SELECT payload FROM study_profiles').fetchone()[0]==payload


def test_schema10_backup_restores_versions_and_invalidates_preview(tmp_path):
    from osler.backups import create_backup,inspect_backup,restore_backup
    from osler.study_agenda import StudyAgenda
    repo=Repository(tmp_path/'source')
    store=StudyStore(repo)
    agenda=StudyAgenda(repo)
    old=agenda.token()
    exams=ExamGoals(repo)
    saved=exams.save(target(),expected_version=0)
    assert old!=agenda.token()
    store.save_profile(AdaptiveProfile(primary_exam_id=saved['target_id'],area_targets={'Pediatria':95}),0)
    exams.save(replace(target(),notes='corrigido'),target_id=saved['target_id'],expected_version=1)
    backup=create_backup(repo)
    assert inspect_backup(backup.read_bytes())['schema_version']==11
    restored=Repository(restore_backup(backup.read_bytes(),tmp_path/'restored'))
    assert ExamGoals(restored).events()==exams.events()
    assert StudyStore(restored).profile()==store.profile()


def test_area_target_is_resolved_for_each_topic_without_leaking_to_other_areas():
    from osler.adaptive_planning import topic_states
    from test_adaptive_planning import topic
    p=AdaptiveProfile(area_targets={'Área':95})
    states=topic_states([topic('A'),{**topic('B'),'path':['Outra área','B']}],[],[],{},'2026-10-15',p)
    assert {t['path'][0]:t['target_accuracy'] for t in states}=={'Área':95,'Outra área':90}


def test_schema9_backup_migrates_additively_and_keeps_old_profile(tmp_path):
    from osler.backups import create_backup,restore_backup,inspect_backup
    from osler.database_check import check_database
    repo=Repository(tmp_path/'old')
    store=StudyStore(repo)
    store.save_profile(AdaptiveProfile(max_questions=120),0)
    with repo._connection() as db:
        db.execute('DROP TABLE exam_targets')
        db.execute('PRAGMA user_version=9')
        previous=[tuple(r) for r in db.execute('SELECT * FROM study_profiles')]
    backup=create_backup(repo)
    assert inspect_backup(backup.read_bytes())['schema_version']==9
    restored=Repository(restore_backup(backup.read_bytes(),tmp_path/'migrated'))
    StudyStore(restored)
    assert check_database(restored.db_path)[0]==11
    with restored._connection() as db:
        assert previous==[tuple(r) for r in db.execute('SELECT * FROM study_profiles')]
        assert db.execute('SELECT COUNT(*) FROM exam_targets').fetchone()[0]==0
