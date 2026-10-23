from dataclasses import replace

import pytest

from osler.mock_exams import MockExam, MockExams, convert_to_entries, retract_conversion
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from test_assessments import setup_assessment


def exam(**changes):
    return replace(MockExam(day='2026-10-15', questions=100, correct=70), **changes)


@pytest.mark.parametrize('changes', [
    {'questions': 0}, {'questions': True}, {'correct': 101}, {'correct': -1},
    {'blank': 31}, {'blank': True}, {'kind': 'invalido'}, {'day': '2026-02-30'},
    {'minutes_used': float('nan')}, {'minutes_allowed': 0}, {'score': 8},
    {'score': 11, 'max_score': 10}, {'conditions': 'ideal'}, {'unseen_questions': 1},
    {'areas': [{'area': 'Clínica', 'questions': 101, 'correct': 70}]},
    {'topics': [{'path': ['Área', 'Tema'], 'questions': 10, 'correct': 11}]},
    {'topics': [{'path': ['Área', 'Tema'], 'questions': 10, 'correct': 7},
                {'path': ['área', 'tema'], 'questions': 10, 'correct': 7}]},
])
def test_invalid_mock_results_are_rejected(changes):
    with pytest.raises(ValueError):
        exam(**changes).validate()


def test_mock_versions_children_and_concurrency_preserve_original(tmp_path):
    mocks = MockExams(Repository(tmp_path))
    saved = mocks.save(exam(areas=[{'area': 'Clínica', 'questions': 100, 'correct': 70}]))
    edited = mocks.save(exam(correct=80), exam_key=saved['exam_key'], expected_version=1)
    assert edited['version'] == 2
    assert mocks.events()[0]['exam']['correct'] == 70
    assert mocks.events()[0]['exam']['areas'][0]['questions'] == 100
    with pytest.raises(ValueError, match='atualiz|mudou'):
        mocks.save(exam(), exam_key=saved['exam_key'], expected_version=1)
    with pytest.raises(ValueError, match='atualiz|mudou'):
        mocks.void(saved['exam_key'], 1)
    mocks.void(saved['exam_key'], 2)
    assert not mocks.active() and len(mocks.events()) == 3


def test_mock_target_must_exist_and_match_institution(tmp_path):
    from osler.exam_goals import ExamGoals, ExamTarget
    repo = Repository(tmp_path)
    mocks = MockExams(repo)
    with pytest.raises(ValueError, match='prova'):
        mocks.save(exam(target_id='missing'))
    target = ExamGoals(repo).save(ExamTarget('Banca A', '2027-11-01', 70, 100, 'Fonte teste'))
    with pytest.raises(ValueError, match='instituição'):
        mocks.save(exam(target_id=target['target_id'], institution='Banca B'))
    assert mocks.save(exam(target_id=target['target_id'], institution='Banca A'))['exam']['target_id'] == target['target_id']


def test_explicit_conversion_only_for_unseen_specific_topics_and_idempotent(tmp_path, sample_pdf):
    repo, *_, row = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    mocks = MockExams(repo)
    topics = [{'path': row.qbank.path, 'questions': 20, 'correct': 14}]
    saved = mocks.save(exam(name='Teste local', unseen_questions=True, topics=topics))
    assert service.store.active('2026-10-15') == []
    first = convert_to_entries(service, saved['exam_key'], 1)
    assert convert_to_entries(service, saved['exam_key'], 1) == first
    entries = service.store.active('2026-10-15')
    assert len(entries) == len(first) == 1
    assert entries[0]['entry']['questions'] == 20
    assert entries[0]['entry']['source'] == 'Simulado Teste local'
    assert entries[0]['entry']['mode'] == 'novas'
    assert len(service.store.events()) == 1
    for result in [exam(topics=topics), exam(unseen_questions=True, areas=[{'area': 'Clínica', 'questions': 100, 'correct': 70}]),
                   exam(unseen_questions=True, topics=[{'path': row.qbank.path[:1], 'questions': 20, 'correct': 14}])]:
        rejected = mocks.save(result)
        with pytest.raises(ValueError):
            convert_to_entries(service, rejected['exam_key'], 1)
    assert len(service.store.events()) == 1


def test_conversion_stale_and_correction_require_explicit_retraction(tmp_path, sample_pdf):
    repo, *_, row = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    mocks = MockExams(repo)
    result = exam(unseen_questions=True, topics=[{'path': row.qbank.path, 'questions': 20, 'correct': 14}])
    saved = mocks.save(result)
    ids = convert_to_entries(service, saved['exam_key'], 1)
    with pytest.raises(ValueError, match='blocos'):
        mocks.save(replace(result, correct=80), exam_key=saved['exam_key'], expected_version=1)
    with pytest.raises(ValueError, match='blocos'):
        mocks.void(saved['exam_key'], 1)
    assert retract_conversion(service, saved['exam_key'], 1) == 1
    assert service.store.active('2026-10-15') == []
    revised = mocks.save(replace(result, topics=[{'path': row.qbank.path, 'questions': 20, 'correct': 18}]),
                         exam_key=saved['exam_key'], expected_version=1)
    with pytest.raises(ValueError, match='atualiz|mudou'):
        convert_to_entries(service, saved['exam_key'], 1)
    convert_to_entries(service, saved['exam_key'], revised['version'])
    entries = service.store.active('2026-10-15')
    assert len(entries) == 1 and entries[0]['entry']['correct'] == 18
    assert entries[0]['version'] == 3 and len(service.store.events()) == 3


def test_invalid_later_topic_does_not_partially_convert(tmp_path, sample_pdf):
    repo, *_, row = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    saved = MockExams(repo).save(exam(unseen_questions=True, topics=[
        {'path': row.qbank.path, 'questions': 20, 'correct': 14},
        {'path': ['Área', 'Ausente'], 'questions': 10, 'correct': 7},
    ]))
    with pytest.raises(ValueError):
        convert_to_entries(service, saved['exam_key'], 1)
    assert not service.store.events()


def test_conversion_survives_backup_restore_without_duplicate(tmp_path, sample_pdf):
    from osler.backups import create_backup, restore_backup
    repo, *_, row = setup_assessment(tmp_path/'source', sample_pdf)
    service = AdaptiveService(repo)
    saved = MockExams(repo).save(exam(unseen_questions=True, topics=[{'path': row.qbank.path, 'questions': 20, 'correct': 14}]))
    ids = convert_to_entries(service, saved['exam_key'], 1)
    backup = create_backup(repo)
    restored = Repository(restore_backup(backup.read_bytes(), tmp_path/'restored'))
    restored_service = AdaptiveService(restored)
    assert convert_to_entries(restored_service, saved['exam_key'], 1) == ids
    assert len(restored_service.store.events()) == 1
    assert MockExams(restored).events() == MockExams(repo).events()


def test_manual_correction_of_converted_block_is_not_overwritten_or_retracted(tmp_path, sample_pdf):
    from osler.study_models import StudyEntry
    repo, *_, row = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    saved = MockExams(repo).save(exam(unseen_questions=True, topics=[{'path': row.qbank.path, 'questions': 20, 'correct': 14}]))
    convert_to_entries(service, saved['exam_key'], 1)
    entry = service.store.active('2026-10-15')[0]
    service.save_entry(replace(StudyEntry(**entry['entry']), correct=15), entry['session_id'], 1)
    with pytest.raises(ValueError, match='corrigid'):
        convert_to_entries(service, saved['exam_key'], 1)
    with pytest.raises(ValueError, match='corrigid'):
        retract_conversion(service, saved['exam_key'], 1)
    assert service.store.active('2026-10-15')[0]['entry']['correct'] == 15


def test_normalized_paths_match_one_specific_leaf(tmp_path, sample_pdf):
    repo, *_, row = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    from osler.models import normalize_path
    saved = MockExams(repo).save(exam(unseen_questions=True, topics=[{'path': normalize_path(row.qbank.path), 'questions': 20, 'correct': 14}]))
    convert_to_entries(service, saved['exam_key'], 1)
    assert service.store.active('2026-10-15')[0]['entry']['path'] == row.qbank.path


def test_correction_changes_topic_set_only_after_all_old_blocks_retracted(tmp_path, sample_pdf):
    repo, *_, row = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    mocks = MockExams(repo)
    initial = exam(unseen_questions=True, topics=[{'path': row.qbank.path, 'questions': 20, 'correct': 14}])
    saved = mocks.save(initial)
    convert_to_entries(service, saved['exam_key'], 1)
    assert retract_conversion(service, saved['exam_key'], 1) == 1
    other = next(t['path'] for t in service.catalog('2026-10-15')[0] if t['path'] != row.qbank.path)
    mocks.save(replace(initial, topics=[{'path': other, 'questions': 1, 'correct': 1}]), exam_key=saved['exam_key'], expected_version=1)
    convert_to_entries(service, saved['exam_key'], 2)
    active = service.store.active('2026-10-15')
    assert len(active) == 1 and active[0]['entry']['path'] == other
