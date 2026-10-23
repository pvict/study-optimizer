from dataclasses import replace
from datetime import date

import pytest

from osler.adaptive_service import AdaptiveService
from osler.exam_goals import ExamGoals, ExamTarget
from osler.mock_exams import MockExam, MockExams, convert_to_entries
from osler.storage import Repository
from osler.study_models import AdaptiveProfile, StudyEntry


DAY = '2026-10-15'


def setup_goal(tmp_path):
    service = AdaptiveService(Repository(tmp_path))
    target = ExamGoals(service.repository).save(ExamTarget('Banca A', '2026-11-15', 70, 100, 'Documento local'))
    return service, target


def report(service):
    from osler.goal_risk import goal_risk_report
    return goal_risk_report(service, DAY)


def test_empty_evidence_retains_target_source_and_has_no_invented_gap(tmp_path):
    service, target = setup_goal(tmp_path)
    row = report(service)['targets'][0]
    assert row['target_id'] == target['target_id']
    assert row['days_remaining'] == 31
    assert row['cutoff_source'] == 'Documento local'
    assert row['label'] == 'Sem dados suficientes'
    assert row['mocks'] == [] and row['areas'] == []


def test_new_area_counts_exclude_repeats_approximate_snapshots_and_old_records(tmp_path):
    service, _ = setup_goal(tmp_path)
    base = StudyEntry(['Clínica', 'Tema'], DAY, 40, correct=20)
    entries = [base, replace(base, mode='repetidas'), replace(base, mode='mistas'),
               replace(base, kind='acumulado'), replace(base, correct=None, percent=50),
               replace(base, day='2026-07-17'), replace(base, day='2026-10-16')]
    service.store.save_batch([(f'block-{i}', e, 0) for i, e in enumerate(entries)])
    area = report(service)['targets'][0]['areas'][0]
    assert area['n'] == 40 and area['correct'] == 20
    assert area['wilson95'] == pytest.approx([35.1995, 64.8005], abs=.001)
    assert area['label'] == 'Sem dados suficientes'  # area is not the global cutoff


def test_recent_window_uses_profile_and_includes_both_boundaries(tmp_path):
    service, _ = setup_goal(tmp_path)
    service.store.save_profile(AdaptiveProfile(recent_days=7), 0)
    entries = [StudyEntry(['Área', 'Tema'], day, 10, correct=5) for day in ['2026-10-08', '2026-10-09', DAY]]
    service.store.save_batch([(f's-{i}', e, 0) for i, e in enumerate(entries)])
    result = report(service)
    assert result['window_start'] == '2026-10-09'
    assert result['targets'][0]['areas'][0]['n'] == 20
    assert result['targets'][0]['areas'][0]['wilson95'] is not None


def test_mock_counts_remain_per_exam_and_institutions_conditions_are_explicit(tmp_path):
    service, target = setup_goal(tmp_path)
    mocks = MockExams(service.repository)
    for institution, conditions in [('Banca A', 'realista'), ('Banca A', 'nao_realista'), ('Banca B', 'realista')]:
        mocks.save(MockExam(DAY, 100, 60, institution=institution, conditions=conditions, unseen_questions=True))
    row = report(service)['targets'][0]
    assert len(row['mocks']) == 2
    assert all(m['n'] == 100 for m in row['mocks'])
    assert {m['conditions'] for m in row['mocks']} == {'realista', 'nao_realista'}
    assert all(m['label'] == 'Sem dados suficientes' for m in row['mocks'])
    assert all(m['wilson95'] is not None for m in row['mocks'])


def test_score_scales_are_never_assumed_equal_to_question_accuracy(tmp_path):
    service, target = setup_goal(tmp_path)
    MockExams(service.repository).save(MockExam(DAY, 100, 99, target_id=target['target_id'],
        institution='Banca A', conditions='realista', unseen_questions=True, score=6, max_score=10))
    row = report(service)['targets'][0]
    assert row['label'] == 'Sem dados suficientes'
    assert row['mocks'][0]['score'] == 6
    assert 'escala' in row['mocks'][0]['comparison_reason'].lower()


def test_converted_mock_questions_are_not_counted_again_as_new_area_blocks(tmp_path, sample_pdf):
    from test_assessments import setup_assessment
    repo, *_, topic = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    ExamGoals(repo).save(ExamTarget('Banca A', '2026-11-15', 70, 100, 'Documento local'))
    saved = MockExams(repo).save(MockExam(DAY, 100, 60, institution='Banca A', unseen_questions=True,
        topics=[{'path': topic.qbank.path, 'questions': 20, 'correct': 10}]))
    convert_to_entries(service, saved['exam_key'], 1)
    row = report(service)['targets'][0]
    assert row['mocks'][0]['n'] == 100
    assert all(area['n'] == 0 for area in row['areas'])


@pytest.mark.parametrize('correct,n,cutoff,expected', [
    (1, 1, 70, 'Sem dados suficientes'), (28, 29, 70, 'Sem dados suficientes'),
    (20, 100, 70, 'Abaixo do corte de referência'), (70, 100, 70, 'Próximo'),
    (99, 100, 70, 'Acima'), (0, 0, 70, 'Sem dados suficientes'),
])
def test_interval_labels_require_sample_and_compare_whole_interval(correct, n, cutoff, expected):
    from osler.goal_risk import evidence_label
    assert evidence_label(correct, n, cutoff) == expected


def test_target_bank_incidence_orders_known_topic_gaps_without_inventing_unmeasured_performance(tmp_path, sample_pdf):
    from test_assessments import setup_assessment
    repo, *_, topic = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    ExamGoals(repo).save(ExamTarget('Banca A', '2026-11-15', 70, 100, 'Documento local'))
    path = topic.qbank.path
    service.store.save_batch([('exact', StudyEntry(path, DAY, 40, correct=20), 0)])
    topics, _ = service.catalog(DAY)
    other = next(t['path'] for t in topics if t['path'] != path)
    for institution, values in [('Banca A', [80, 20]), ('Banca B', [1, 99])]:
        service.guide.store.save_dataset({'institutions': [institution], 'observed_date': DAY, 'unit': 'questoes',
            'rows': [{'path': p, 'value': v, 'band': 'alta'} for p, v in zip([path, other], values)]})
    row = report(service)['targets'][0]
    known = next(t for a in row['areas'] for t in a['topics'] if t['path'] == path)
    unknown = next(t for a in row['areas'] for t in a['topics'] if t['path'] == other)
    assert known['incidence_weight'] == pytest.approx(.8)
    assert known['weighted_gap_pp'] == pytest.approx(32)
    assert known['gap_interval_pp'][0] > 20
    assert unknown['weighted_gap_pp'] is None and unknown['n'] == 0
    assert row['incidence_contexts'][0]['institutions'] == ['Banca A']


def test_joint_incidence_is_not_used_as_individual_bank_evidence(tmp_path, sample_pdf):
    from test_assessments import setup_assessment
    repo, *_, topic = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    ExamGoals(repo).save(ExamTarget('Banca A', '2026-11-15', 70, 100, 'Documento local'))
    service.store.save_batch([('exact', StudyEntry(topic.qbank.path, DAY, 40, correct=20), 0)])
    service.guide.store.save_dataset({'institutions': ['Banca A', 'Banca B'], 'observed_date': DAY, 'unit': 'questoes',
        'rows': [{'path': topic.qbank.path, 'value': 100, 'band': 'alta'}]})
    row = report(service)['targets'][0]
    assert not row['incidence_contexts']
    assert all(t['weighted_gap_pp'] is None for a in row['areas'] for t in a['topics'])
    assert any('conjunta' in w for w in row['warnings'])


def test_report_executes_no_mutating_sql(tmp_path, monkeypatch):
    from contextlib import contextmanager
    service, _ = setup_goal(tmp_path)
    original = service.repository._connection
    statements = []
    @contextmanager
    def traced_connection():
        with original() as db:
            db.set_trace_callback(statements.append)
            yield db
    monkeypatch.setattr(service.repository, '_connection', traced_connection)
    report(service)
    forbidden = ('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'BEGIN IMMEDIATE')
    assert not [sql for sql in statements if sql.lstrip().upper().startswith(forbidden)]


def test_measured_topic_missing_from_individual_incidence_keeps_gap_unknown(tmp_path, sample_pdf):
    from test_assessments import setup_assessment
    repo, *_, topic = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    ExamGoals(repo).save(ExamTarget('Banca A', '2026-11-15', 70, 100, 'Documento local'))
    other = next(t['path'] for t in service.catalog(DAY)[0] if t['path'] != topic.qbank.path)
    service.store.save_batch([(str(i), StudyEntry(path, DAY, 40, correct=20), 0)
                              for i, path in enumerate([topic.qbank.path, other])])
    service.guide.store.save_dataset({'institutions': ['Banca A'], 'observed_date': DAY, 'unit': 'questoes',
        'rows': [{'path': topic.qbank.path, 'value': 100, 'band': 'alta'}]})
    missing = next(t for a in report(service)['targets'][0]['areas'] for t in a['topics'] if t['path'] == other)
    assert missing['n'] == 40
    assert missing['incidence_weight'] is None
    assert missing['weighted_gap_pp'] is None and missing['gap_interval_pp'] is None
    measured = next(t for a in report(service)['targets'][0]['areas'] for t in a['topics'] if t['path'] == topic.qbank.path)
    assert measured['incidence_weight'] == pytest.approx(1)


def test_confirmed_objective_mock_can_be_compared_without_pooling(tmp_path):
    service, target = setup_goal(tmp_path)
    goals = ExamGoals(service.repository)
    goals.save(ExamTarget('Banca A', '2026-11-15', 70, 100, 'Documento local',
                         score_basis='percentual_objetivo'), target_id=target['target_id'], expected_version=target['version'])
    MockExams(service.repository).save(MockExam(DAY, 100, 99, target_id=target['target_id'],
        institution='Banca A', conditions='realista', unseen_questions=True))
    row = report(service)['targets'][0]
    assert row['label'] == 'Acima' and row['mocks'][0]['n'] == 100
