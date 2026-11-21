from copy import deepcopy
from dataclasses import replace

import pytest

from osler.adaptive_planning import topic_states
from osler.balanced_reviews import balanced_spacing, daily_evidence
from osler.study_evolution import evolution_snapshot, evolution_attention
from osler.study_models import AdaptiveProfile, StudyEntry
from osler.topic_grouping import grouping_candidates, grouped_frontier, protect_group_evidence
from test_topic_grouping import fixture
from test_evolution import state


def grouped_states(child_events):
    topics, datasets, profile = fixture()
    profile = replace(profile, review_strategy='balanced_v2')
    for topic in topics:
        topic.update(answered_pdf=0, pdf_accuracy={'value': None, 'operator': None, 'raw': '-'},
                     report_date='2026-10-20', studied_cards=0, planner_snapshot=None)
    events = [{'session_id': day, 'entry': StudyEntry(topics[0]['path'], day, 20, correct=20).to_dict()}
              for day in ('2026-10-01', '2026-10-08', '2026-10-22')]
    events += child_events
    candidates = grouping_candidates(topics, datasets, profile, '2026-10-30')
    leaves = topic_states(topics[1:], events, datasets, profile.institution_weights, '2026-10-30', profile)
    groups = topic_states(grouped_frontier(topics, profile, candidates), events, datasets,
                          profile.institution_weights, '2026-10-30', profile)
    before = deepcopy(leaves)
    protect_group_evidence(groups, leaves)
    assert leaves == before
    return groups[0], leaves


@pytest.mark.parametrize('confident', [None, 0])
def test_recent_individual_failure_protects_committed_group_without_combining_samples(confident):
    topics, _, _ = fixture()
    failure = {'session_id': 'individual', 'entry': StudyEntry(topics[1]['path'], '2026-10-30',
                20, correct=0, confident_correct=confident).to_dict()}
    group, leaves = grouped_states([failure])
    assert group['priority'] == group['evidence_priority'] == 'urgente'
    assert group['learning_state'] == 'alerta' and group['dose_kind'] == 'reinforcement'
    assert group['theme_review_due'] == group['next_review'] == '2026-11-02'
    assert group['review_interval_days'] == 3
    assert group['performance']['exact_n'] == group['performance']['exact_correct'] == 60
    assert leaves[0]['performance']['exact_n'] == 20 and leaves[1]['performance']['exact_n'] == 0
    assert group['last_contact'] == '2026-10-22'


def test_converted_mock_failure_reaches_group_without_confidence(tmp_path, monkeypatch):
    from datetime import date
    import osler.planner_service as planner_service
    from osler.storage import Repository
    from osler.adaptive_service import AdaptiveService
    from osler.mock_exams import MockExams, MockExam, convert_to_entries
    topics, _, _ = fixture()
    monkeypatch.setattr(planner_service, 'today_local', lambda: date(2026, 10, 30))
    service = AdaptiveService(Repository(tmp_path))
    monkeypatch.setattr(service, 'catalog', lambda *args, **kwargs: (topics, {}))
    row = MockExams(service.repository).save(MockExam('2026-10-30', 20, 0, unseen_questions=True,
              topics=[{'path': topics[1]['path'], 'questions': 20, 'correct': 0}]))
    convert_to_entries(service, row['exam_key'], row['version'])
    entries = service.store.active('2026-10-30')
    assert entries[0]['entry']['confident_correct'] is None
    group, _ = grouped_states(entries)
    assert group['priority'] == 'urgente' and group['theme_review_due'] == '2026-11-02'


def test_group_practice_does_not_clear_unresolved_individual_failure():
    topics, _, _ = fixture()
    failure = {'session_id': 'individual', 'entry': StudyEntry(topics[1]['path'], '2026-10-20',
                20, correct=0).to_dict()}
    group, _ = grouped_states([failure])
    assert group['learning_state'] != 'dominado'
    assert group['priority'] == 'urgente'


def test_high_priority_without_measurement_protects_deadline_without_inventing_deficit():
    group, leaves = grouped_states([])
    leaves[0].update(priority='alta', evidence_priority='alta', next_review='2026-11-01',
                     theme_review_due='2026-11-01', allocation_due='2026-11-01')
    assert leaves[0]['performance']['exact_n'] == 0
    assert not any(leaves[0].get(field) for field in ('low_accuracy', 'alert_signal', 'manual_adverse',
                                                     'registered_error', 'linked_adverse', 'reported_difficulty'))
    before = deepcopy(leaves)
    protect_group_evidence([group], leaves)
    assert group['priority'] == 'alta' and group['theme_review_due'] == '2026-11-01'
    assert group['learning_state'] == 'dominado' and group['dose_kind'] == 'maintenance'
    assert group['group_member_adverse'] == []
    assert group['performance']['exact_n'] == 60 and leaves == before


def test_tiny_new_block_does_not_erase_sufficient_mixed_spacing_evidence():
    profile = AdaptiveProfile(review_strategy='balanced_v2')
    entries = [StudyEntry(['Área', 'Tema'], '2026-10-01', 20, correct=20).to_dict(),
               StudyEntry(['Área', 'Tema'], '2026-10-08', 20, correct=20, mode='mistas').to_dict(),
               StudyEntry(['Área', 'Tema'], '2026-10-08', 1, correct=1).to_dict()]
    result = balanced_spacing(entries, profile, '2026-10-08')
    assert result['interval'] == 14 and result['streak'] == 2
    assert result['last_evidence_day'] == '2026-10-08'
    assert daily_evidence(entries, '2026-10-08')[-1]['mode'] == 'mistas'
    assert daily_evidence(entries, '2026-10-08')[-1]['n'] == 20


def test_separate_insufficient_modalities_do_not_manufacture_sufficient_sample():
    profile = AdaptiveProfile(review_strategy='balanced_v2')
    entries = [StudyEntry(['Área', 'Tema'], '2026-10-08', 6, correct=6, mode=mode).to_dict()
               for mode in ('novas', 'mistas')]
    result = balanced_spacing(entries, profile, '2026-10-08')
    assert result['last_evidence_day'] is None and result['streak'] == 0


def test_early_practice_keeps_contact_separate_from_valid_spaced_assessment():
    profile = AdaptiveProfile(review_strategy='balanced_v2')
    entries = [StudyEntry(['Área', 'Tema'], day, 20, correct=20).to_dict()
               for day in ('2026-10-01', '2026-10-02', '2026-10-08')]
    result = balanced_spacing(entries, profile, '2026-10-08')
    assert result['streak'] == 2 and result['interval'] == 14
    early = balanced_spacing(entries[:2], profile, '2026-10-02')
    assert early['last_evidence_day'] == '2026-10-02'
    assert early['last_spaced_evidence_day'] == '2026-10-01'


def test_joint_exposure_is_visible_without_assigning_questions_or_coverage_to_children():
    topics = [state('A'), state('B')]
    for topic in topics:
        topic['path'] = ['Área', 'Grupo', topic['topic_id']]
        topic['planner_safety']['confident_accuracy_pct'] = None
    group = {'topic_id': 'parent', 'path': ['Área', 'Grupo'], 'group_members': ['A', 'B']}
    events = [{'session_id': 'joint', 'entry': StudyEntry(group['path'], '2026-10-14', 20, correct=20).to_dict()}]
    calendar = [{'date': '2026-10-16', 'questions': 20, 'items': [{'topic_id': 'parent', 'questions': 20}]}]
    original = deepcopy((topics, events, calendar))
    result = evolution_snapshot(topics, events, calendar, '2026-10-15', planning_states=[group])
    assert result['actual_attempts'] == 20 and result['points'][-1]['attempts'] == 40
    assert result['covered_now'] == result['points'][-1]['covered'] == 0
    assert result['planned_contacts'] == {}
    assert result['joint_contacts']['parent'] == ['2026-10-14']
    assert result['planned_joint_contacts']['parent'] == ['2026-10-16']
    assert result['points'][-1]['included_jointly'] == result['points'][-1]['joint_only'] == 2
    attention = evolution_attention(result, '2026-10-16')
    assert len(attention) == 2 and all(item['kind'] == 'Medir subtema' for item in attention)
    assert all(item['last_contact_in_scenario'] is None and item['rate'] is None for item in attention)
    assert (topics, events, calendar) == original
