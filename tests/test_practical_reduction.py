from copy import deepcopy
import sqlite3

import pytest
from streamlit.testing.v1 import AppTest

from osler.triage import build_triage
from osler.practical_reduction import PracticalReductionService
from osler.models import parse_percentage, stable_topic_id
from test_assessments import setup_assessment
from test_classification import known


def triage_fixture(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    analysis = assessment.analyze(matching, '2026-10-15')
    return repo, assessment, matching, row, analysis


def test_documentary_triage_uses_all_studied_topics_without_manual_forms(tmp_path, sample_pdf):
    _, _, matching, row, analysis = triage_fixture(tmp_path, sample_pdf)
    extra = deepcopy(row)
    extra.row_id = 'another'
    for source in [extra.qbank, extra.flashcards]:
        source.path[-1] = 'Segundo tema'
        source.topic_id = stable_topic_id(source.path)
    matching.rows.append(extra)
    result = build_triage(matching, analysis, [], [], '2026-10-15')
    assert len(result) == 2
    assert all(i['evidence'] == 'pdf' for i in result)
    assert all(i['accuracy_label'] == 'Acerto no PDF · tentativa não identificada' for i in result)
    assert all(i['studied_cards'] == 146 for i in result)
    assert all(i['distinct_questions'] is None for i in result)
    assert all(i['applied'] is False for i in result)


def test_native_incidence_distinguishes_high_from_very_high_and_missing(tmp_path, sample_pdf):
    _, _, matching, row, analysis = triage_fixture(tmp_path, sample_pdf)
    for name in ['Segundo', 'Sem tabela']:
        extra = deepcopy(row)
        extra.row_id = name
        for source in [extra.qbank, extra.flashcards]:
            source.path[-1] = name
            source.topic_id = stable_topic_id(source.path)
        extra.flashcards.studied = 20
        matching.rows.append(extra)
    datasets = [{'id': 1, 'observed_date': '2026-10-15', 'institutions': ['A'], 'unit': 'questoes', 'rows': [
        {'path': row.qbank.path, 'value': 20, 'band': 'alta', 'native_incidence': 'Incidência altíssima'},
        {'path': matching.rows[-2].qbank.path, 'value': 10, 'band': 'alta', 'native_incidence': 'Incidência alta'}]}]
    result = build_triage(matching, analysis, datasets, ['A'], '2026-10-15')
    assert [t['path'][-1] for t in result] == ['Segundo', row.qbank.name, 'Sem tabela']


@pytest.mark.parametrize('field,value', [('answers', 29), ('accuracy', '<85%'), ('accuracy', '84%'), ('cards', 19), ('ambiguous', True), ('old', True)])
def test_weak_or_incompatible_documentary_data_is_not_selected(tmp_path, sample_pdf, field, value):
    _, _, matching, row, analysis = triage_fixture(tmp_path, sample_pdf)
    if field == 'answers': row.qbank.studied = value
    if field == 'accuracy': row.qbank.acerto_pdf = parse_percentage(value)
    if field == 'cards': row.flashcards.studied = value
    if field == 'ambiguous': row.association = 'bloqueada'
    if field == 'old': matching.qbank_date = '2026-01-01'
    assert build_triage(matching, analysis, [], [], '2026-10-15') == []


def test_adverse_manual_evidence_overrides_good_pdf(tmp_path, sample_pdf):
    repo, assessment, matching, row, _ = triage_fixture(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(erros_recorrentes=True), 0)
    analysis = assessment.analyze(matching, '2026-10-15')
    assert build_triage(matching, analysis, [], [], '2026-10-15') == []


def test_manual_first_attempt_is_not_replaced_by_higher_pdf(tmp_path, sample_pdf):
    _, assessment, matching, row, _ = triage_fixture(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=60), 0)
    assert build_triage(matching, assessment.analyze(matching, '2026-10-15'), [], [], '2026-10-15') == []


def test_low_last_attempt_is_not_replaced_by_higher_pdf_when_initial_missing(tmp_path, sample_pdf):
    _, assessment, matching, row, _ = triage_fixture(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=None, acerto_ultima_tentativa=30), 0)
    assert build_triage(matching, assessment.analyze(matching, '2026-10-15'), [], [], '2026-10-15') == []


def test_one_declaration_records_selection_and_can_be_reopened_with_history(tmp_path, sample_pdf):
    repo, *_ = triage_fixture(tmp_path, sample_pdf)
    service = PracticalReductionService(repo)
    view = service.overview('2026-10-15')
    assert len(view['triage']) == 1
    topic_id = view['triage'][0]['topic_id']
    event = service.record('aplicado', [topic_id], '2026-10-15', view['signature'], view['event_id'])
    after = service.overview('2026-10-15')
    assert after['triage'] == []
    assert after['applied_topics'] == 1
    assert after['measured_reduction'] is None
    assert service.record('aplicado', [topic_id], '2026-10-15', view['signature'], view['event_id']) == event
    service.record('reabrir', [topic_id], '2026-10-15', after['signature'], after['event_id'])
    again = service.overview('2026-10-15')
    assert len(again['triage']) == 1 and again['applied_topics'] == 0
    assert len(service.store.events()) == 2
    with repo._connection() as db:
        assert db.execute('SELECT COUNT(*) FROM observations').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM planner_items').fetchone()[0] == 0
    from osler.backups import create_backup, inspect_backup, restore_backup
    from osler.storage import Repository
    backup = create_backup(repo)
    assert inspect_backup(backup.read_bytes())['schema_version'] == 7
    restored = Repository(restore_backup(backup.read_bytes(), tmp_path/'restored'))
    assert PracticalReductionService(restored).store.events() == service.store.events()


def test_changed_evidence_prevents_stale_declaration(tmp_path, sample_pdf):
    repo, assessment, matching, row, _ = triage_fixture(tmp_path, sample_pdf)
    service = PracticalReductionService(repo)
    view = service.overview('2026-10-15')
    assessment.save_observation(matching, row.row_id, known(erros_criticos=True), 0)
    with pytest.raises(ValueError, match='[Aa]tualiz'):
        service.record('aplicado', [view['triage'][0]['topic_id']], '2026-10-15', view['signature'], view['event_id'])
    assert service.store.events() == []


def test_applied_legacy_item_stays_out_of_new_action_list(tmp_path, sample_pdf):
    from test_planner import setup_plan, move
    repo, _, _, _, planner, bid = setup_plan(tmp_path, sample_pdf)
    for state in ['aguardando_validacao', 'aprovado_usuario', 'aplicado_manualmente']:
        move(planner, planner.get_batch(bid)['items'][0], state, confirmed=True)
    view = PracticalReductionService(repo).overview('2026-10-15')
    assert view['triage'] == []
    assert view['applied_topics'] == 1


def test_difficulty_recorded_in_daily_guide_blocks_documentary_reduction(tmp_path, sample_pdf):
    from osler.guide_service import GuideService
    repo, _, _, row, _ = triage_fixture(tmp_path, sample_pdf)
    GuideService(repo).save_day('2026-10-15', 'parcial', row.qbank.path, 'dificil')
    assert PracticalReductionService(repo).overview('2026-10-15')['triage'] == []


def test_adverse_observation_in_other_report_pair_still_blocks_same_path(tmp_path, sample_pdf):
    from osler.service import import_bytes
    from osler.matching_service import load_matching
    repo, assessment, matching, row, _ = triage_fixture(tmp_path, sample_pdf)
    older = import_bytes(repo, sample_pdf(kind='flashcards', date='13/10/2026'), 'older.pdf').report
    other = load_matching(repo, matching.qbank_report_id, older.file_sha256)
    other_row = next(r for r in other.rows if r.qbank and r.qbank.path == row.qbank.path)
    assessment.save_observation(other, other_row.row_id, known(erros_criticos=True), 0)
    assert PracticalReductionService(repo).overview('2026-10-15')['triage'] == []


def test_documentary_minimum_is_separate_from_distinct_question_policy(tmp_path, sample_pdf):
    from osler.classification import ClassifierConfig
    repo, *_ = triage_fixture(tmp_path, sample_pdf)
    view = PracticalReductionService(repo).overview('2026-10-15', config=ClassifierConfig(min_questions=100), min_answers=30)
    assert len(view['triage']) == 1
    assert view['candidates'] == []


def test_concurrent_adverse_evidence_is_rejected_inside_record_transaction(tmp_path, sample_pdf, monkeypatch):
    repo, assessment, matching, row, _ = triage_fixture(tmp_path, sample_pdf)
    service = PracticalReductionService(repo)
    view = service.overview('2026-10-15')
    original_append = service.store.append
    def concurrent_change(payload, expected_id, evidence_token=None):
        assessment.save_observation(matching, row.row_id, known(erros_criticos=True), 0)
        if evidence_token is None:
            return original_append(payload, expected_id)
        return original_append(payload, expected_id, evidence_token)
    monkeypatch.setattr(service.store, 'append', concurrent_change)
    with pytest.raises(ValueError, match='[Aa]tualiz'):
        service.record('aplicado', [view['triage'][0]['topic_id']], '2026-10-15', view['signature'], view['event_id'])
    assert service.store.events() == []


def test_practical_ui_has_ready_list_and_single_optional_declaration(tmp_path, monkeypatch, project_root, sample_pdf):
    repo, *_ = triage_fixture(tmp_path, sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(project_root/'app.py'), default_timeout=30).run()
    app.radio(key='main_view').set_value('Diminuir revisões').run()
    assert not app.exception
    assert len(app.dataframe) >= 1
    assert any(b.label == 'Já fiz uma redução seletiva nesses temas' for b in app.button)
    assert not any('aprovar' in b.label.lower() for b in app.button)
    topic_id = PracticalReductionService(repo).overview('2026-10-15')['triage'][0]['topic_id']
    app.multiselect(key='practical_selection').set_value([topic_id]).run()
    next(b for b in app.button if b.label == 'Já fiz uma redução seletiva nesses temas').click().run()
    assert not app.exception
    assert PracticalReductionService(repo).overview('2026-10-15')['applied_topics'] == 1
