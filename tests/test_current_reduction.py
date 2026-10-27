from conftest import open_view
from copy import deepcopy

import pytest

from osler import practical_reduction
from osler.practical_reduction import PracticalReductionService
from test_assessments import setup_assessment


def state(name='Tema', **changes):
    return {'topic_id': name, 'path': ['Área', name], 'studied_cards': 100,
            'report_date': '2026-10-14', 'answered_pdf': 100, 'pdf_accuracy': {'value': 95},
            'incidence_known': True, 'incidence_strength': .1, 'priority': 'normal',
            'performance': {'exact_n': 0, 'exact_correct': 0, 'reported_n': 0, 'reported_percent': None},
            'planner_safety': {'observed_date': '2026-10-15', 'unique_questions': 25,
                               'confident_accuracy_pct': 90, 'pending_reviews': 0}, **changes}


def recommendations(states, sessions=(), day='2026-10-15'):
    from osler.reduction_recommendations import current_recommendations
    return current_recommendations(states, list(sessions), day)


def session(n=20, correct=19, day='2026-10-14', **extra):
    return {'entry': {'path': ['Área', 'Tema'], 'day': day, 'kind': 'bloco', 'mode': 'novas',
                      'questions': n, 'correct': correct, **extra}}


def test_current_policy_exists_independently_of_pdf_triage():
    assert callable(getattr(practical_reduction.PracticalReductionService, 'current_overview', None))


def test_indirect_safety_allows_only_short_selective_capacity_pause():
    result = recommendations([state()])
    candidate = result['suggestions'][0]
    assert candidate['recommendation'] == 'pausa_capacidade'
    assert candidate['review_on'] == '2026-10-22'
    assert candidate['evidence_kind'] == 'indireta'
    assert candidate['scope'] == 'seletiva'
    assert candidate['objective_accuracy'] is None


@pytest.mark.parametrize('change', [
    {'manual_context': {'data_observacao': '2026-10-14', 'acerto_primeira_tentativa': 82}},
    {'manual_context': {'data_observacao': '2026-10-14', 'erros_criticos': True}},
    {'registered_error': True}, {'open_error_count': 1}, {'linked_adverse': True},
    {'priority': 'alta'}, {'incidence_strength': .6},
])
def test_adverse_or_high_priority_state_protects_even_with_good_pdf(change):
    result = recommendations([state(**change)])
    assert result['suggestions'] == []
    assert result['protected'][0]['topic_id'] == 'Tema'


def test_new_error_cards_protect_the_topic_without_inventing_study():
    result = recommendations([state()], [session(cards_created=3)])
    assert result['suggestions'] == []
    assert result['protected'][0]['recent_cards_created'] == 3


def test_pending_review_in_current_safety_snapshot_protects_even_with_high_safety():
    safety = {**state()['planner_safety'], 'pending_reviews': 1}
    result = recommendations([state(planner_safety=safety)])
    assert result['suggestions'] == []
    assert result['protected']


def test_superseded_safety_snapshot_is_not_used_as_capacity_pause_evidence():
    entries = [session(n=20, correct=19)]
    result = recommendations([state(planner_snapshot_current=False)], entries)
    assert result['suggestions'] == []
    assert result['conditional']


def test_superseded_safety_warning_does_not_override_strong_current_exact_results():
    safety = {**state()['planner_safety'], 'confident_accuracy_pct': 50, 'pending_reviews': 4}
    entries = [session(), session(day='2026-10-15')]
    result = recommendations([state(planner_safety=safety, planner_snapshot_current=False)], entries)
    assert result['suggestions'][0]['evidence_kind'] == 'objetiva'


def test_recent_difficult_guide_feedback_protects_current_view(tmp_path, sample_pdf):
    repo, adaptive, service, _, _, row = ready_service(tmp_path, sample_pdf)
    adaptive.guide.save_day('2026-10-15', 'parcial', row.qbank.path, 'dificil')
    view = service.current_overview('2026-10-15')
    assert view['suggestions'] == []
    assert any(t['topic_id'] == row.qbank.topic_id for t in view['protected'])


def test_manual_percentage_cannot_be_relabelled_as_exact_block_accuracy():
    manual = {'data_observacao': '2026-10-14', 'acerto_primeira_tentativa': 90}
    result = recommendations([state(manual_context=manual)], [session(), session(day='2026-10-15')])
    candidate = result['suggestions'][0]
    assert candidate['objective_accuracy'] == 90
    assert candidate['exact_accuracy_pct'] == 95
    assert candidate['objective_n'] == 40


def test_expired_created_cards_and_future_sessions_do_not_distort_current_reading():
    result = recommendations([state()], [session(day='2026-09-30', cards_created=3),
                                        session(day='2026-10-16', n=10, correct=0, cards_created=5)])
    assert result['suggestions'][0]['recent_cards_created'] == 0


def test_objective_failure_overrides_high_accumulated_safety():
    result = recommendations([state()], [session(n=20, correct=16)])
    assert result['suggestions'] == []
    assert result['protected'][0]['objective_accuracy'] == 80


@pytest.mark.parametrize('mode', ['novas', 'mistas', 'repetidas'])
def test_latest_objective_failure_is_not_diluted_by_successful_history(mode):
    entries = [session(n=100, correct=100, day='2026-10-12', mode=mode),
               session(n=40, correct=40, day='2026-10-14', mode=mode),
               session(n=10, correct=0, day='2026-10-15', mode=mode)]
    result = recommendations([state()], entries)
    assert result['suggestions'] == []
    assert result['protected'][0]['objective_accuracy'] == 0


def test_bad_block_on_latest_day_cannot_be_hidden_by_good_block_on_same_day():
    entries = [session(n=100, correct=100, day='2026-10-14'),
               session(n=100, correct=100, day='2026-10-15'),
               session(n=10, correct=0, day='2026-10-15')]
    assert recommendations([state()], entries)['suggestions'] == []


def test_reinforcement_state_protects_without_relabelling_conviction_as_accuracy():
    result = recommendations([state(dose_kind='reinforcement')])
    assert result['suggestions'] == []
    assert result['protected'][0]['objective_accuracy'] is None


def test_more_recent_objective_recovery_replaces_the_previous_day_signal():
    entries = [session(n=5, correct=0, day='2026-10-12'),
               session(n=100, correct=100, day='2026-10-14'),
               session(n=100, correct=100, day='2026-10-15')]
    assert recommendations([state()], entries)['suggestions']


def test_pdf_alone_or_missing_incidence_never_authorizes_pause():
    for change in ({'planner_safety': None}, {'incidence_known': False},
                   {'planner_safety': {'observed_date': '2026-01-01', 'unique_questions': 50, 'confident_accuracy_pct': 100}}):
        result = recommendations([state(**change)])
        assert result['suggestions'] == []
        assert len(result['conditional']) == 1


def test_exact_success_on_two_days_is_selective_maintenance_and_one_day_is_not():
    entries = [session(), session(day='2026-10-15')]
    result = recommendations([state(planner_safety=None)], entries)
    assert result['suggestions'][0]['recommendation'] == 'manutencao_seletiva'
    assert result['suggestions'][0]['evidence_kind'] == 'objetiva'
    assert result['suggestions'][0]['objective_n'] == 40
    assert result['suggestions'][0]['objective_accuracy'] == 95
    assert recommendations([state(planner_safety=None)], [session(n=40, correct=38)])['suggestions'] == []


def test_approximate_or_repeated_results_never_become_binomial_mastery():
    for entries in ([session(correct=None, percent=95), session(correct=None, percent=95, day='2026-10-15')],
                    [session(mode='repetidas'), session(mode='repetidas', day='2026-10-15')]):
        result = recommendations([state(planner_safety=None)], entries)
        assert result['suggestions'] == []


def test_shortlist_has_three_and_ranks_incidence_before_card_volume_without_mutation():
    states = [state(str(i), incidence_strength=i/100, studied_cards=i*100) for i in range(1, 6)]
    before = deepcopy(states)
    result = recommendations(states)
    assert [t['topic_id'] for t in result['suggestions']] == ['1', '2', '3']
    assert len(result['all_suggestions']) == 5
    assert states == before


def test_service_current_sources_and_manual_action_are_audited(tmp_path, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    service = PracticalReductionService(repo)
    view = service.current_overview('2026-10-15')
    assert view['suggestions'] == []
    assert view['conditional']
    assert view['sources']['reports']['qbank']['report_date'] == '2026-10-14'
    assert view['evidence_token']
    with pytest.raises(ValueError):
        service.record_current('aplicado', [view['conditional'][0]['topic_id']], '2026-10-15', view['signature'], view['event_id'])
    assert service.store.events() == []


def ready_service(tmp_path, sample_pdf):
    from osler.adaptive_service import AdaptiveService
    from osler.study_models import StudyEntry
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    adaptive = AdaptiveService(repo)
    topics, _ = adaptive.catalog('2026-10-15')
    other = next(t for t in topics if t['path'] != row.qbank.path)
    adaptive.guide.store.save_dataset({'institutions': ['X'], 'observed_date': '2026-10-15', 'unit': 'questoes',
                                      'rows': [{'path': row.qbank.path, 'value': 1, 'band': 'baixa'},
                                               {'path': other['path'], 'value': 100, 'band': 'alta'}]})
    for i, day in enumerate(['2026-10-14', '2026-10-15']):
        adaptive.save_entry(StudyEntry(row.qbank.path, day, 20, 19, confident_correct=19), 'good'+str(i))
    return repo, adaptive, PracticalReductionService(repo), assessment, matching, row


def test_actual_adaptive_reinforcement_blocks_reduction_after_large_good_history(tmp_path, sample_pdf):
    from osler.study_models import StudyEntry
    repo, adaptive, service, _, _, row = ready_service(tmp_path, sample_pdf)
    for i, day in enumerate(['2026-10-12', '2026-10-14']):
        adaptive.save_entry(StudyEntry(row.qbank.path, day, 70, 70, confident_correct=70), 'good'+str(i), 1)
    adaptive.save_entry(StudyEntry(row.qbank.path, '2026-10-15', 10, 0, confident_correct=0), 'latest-poor')
    adaptive_state = next(t for t in adaptive.overview('2026-10-15')['states'] if t['topic_id'] == row.qbank.topic_id)
    assert adaptive_state['dose_kind'] == 'reinforcement'
    view = service.current_overview('2026-10-15')
    assert view['suggestions'] == []
    assert any(t['topic_id'] == row.qbank.topic_id for t in view['protected'])


@pytest.mark.parametrize('other_pair', [False, True])
def test_corrected_observation_replaces_prior_adverse_version_for_each_source(tmp_path, sample_pdf, other_pair):
    from osler.matching_service import load_matching
    from osler.service import import_bytes
    from test_classification import known
    repo, adaptive, service, assessment, matching, row = ready_service(tmp_path, sample_pdf)
    if other_pair:
        old = import_bytes(repo, sample_pdf(kind='flashcards', date='13/10/2026'), 'old.pdf').report
        matching = load_matching(repo, matching.qbank_report_id, old.file_sha256)
        row = next(r for r in matching.rows if r.qbank and r.qbank.path == row.qbank.path)
    adverse = known(acerto_primeira_tentativa=95, acerto_ultima_tentativa=95,
                    erros_criticos=True, erros_recorrentes=False)
    assessment.save_observation(matching, row.row_id, adverse, 0)
    assert service.current_overview('2026-10-15')['suggestions'] == []
    from dataclasses import replace
    assessment.save_observation(matching, row.row_id, replace(adverse, erros_criticos=False), 1)
    view = service.current_overview('2026-10-15')
    assert any(t['topic_id'] == row.qbank.topic_id for t in view['suggestions'])
    assert len(assessment.store.history(row.row_id)) == 2


@pytest.mark.parametrize('adverse,clear', [({'risco_perda': 'alto'}, {'risco_perda': 'baixo'}),
                                       ({'cobertura_suficiente': False}, {'cobertura_suficiente': True})])
def test_explicit_current_risk_or_coverage_gap_protects_until_corrected(tmp_path, sample_pdf, adverse, clear):
    from test_classification import known
    repo, adaptive, service, assessment, matching, row = ready_service(tmp_path, sample_pdf)
    base = dict(acerto_primeira_tentativa=95, acerto_ultima_tentativa=95,
                erros_criticos=False, erros_recorrentes=False)
    assessment.save_observation(matching, row.row_id, known(**base, **adverse), 0)
    assert service.current_overview('2026-10-15')['suggestions'] == []
    assessment.save_observation(matching, row.row_id, known(**base, **clear), 1)
    assert service.current_overview('2026-10-15')['suggestions']


def test_legacy_manual_application_stays_out_of_current_suggestions_and_can_reopen_locally(tmp_path, sample_pdf, monkeypatch):
    from datetime import date
    from osler.planner_service import PlannerService
    from test_classification import known
    repo, adaptive, service, assessment, matching, row = ready_service(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=95, acerto_ultima_tentativa=95,
                                                         erros_criticos=False, erros_recorrentes=False), 0)
    planner = PlannerService(repo)
    bid = planner.create_batch(matching, [row.row_id], 'Lote real anterior', 'Aplicação declarada', '2026-10-14')
    for status in ('aguardando_validacao', 'aprovado_usuario', 'aplicado_manualmente'):
        item = planner.get_batch(bid)['items'][0]
        planner.transition(item['id'], status, 'Ação manual declarada', item['revision'], '2026-10-14',
                           confirmed=True, reevaluation_date='2026-10-21')
    view = service.current_overview('2026-10-15')
    assert view['suggestions'] == []
    assert service.store.events() == []
    assert view['legacy_history'][0]['planner_item_id'] == item['id']
    assert view['legacy_history'][0]['review_on'] == '2026-10-21'
    due = service.current_overview('2026-10-21')
    assert due['reevaluate'][0]['topic_id'] == row.qbank.topic_id
    assert due['reevaluate'][0]['review_on'] == '2026-10-21'
    monkeypatch.setattr('osler.planner_service.today_local', lambda: date(2026, 10, 21))
    service.record_current('reabrir', [row.qbank.topic_id], '2026-10-21', due['signature'], due['event_id'])
    assert planner.get_batch(bid)['items'][0]['status'] == 'aplicado_manualmente'
    assert service.current_overview('2026-10-21')['latest'][row.qbank.topic_id]['kind'] == 'reabrir'
    assert service.current_overview('2026-10-21')['reevaluate'] == []


def test_local_reopening_only_overrides_the_legacy_item_revision_it_reopened(tmp_path, sample_pdf):
    from osler.planner_service import PlannerService
    from test_classification import known
    repo, adaptive, service, assessment, matching, row = ready_service(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=95, acerto_ultima_tentativa=95,
                                                         erros_criticos=False, erros_recorrentes=False), 0)
    planner = PlannerService(repo)
    def apply(day):
        bid = planner.create_batch(matching, [row.row_id], 'Lote '+day, 'Ação manual', day)
        for status in ('aguardando_validacao', 'aprovado_usuario', 'aplicado_manualmente'):
            item = planner.get_batch(bid)['items'][0]
            planner.transition(item['id'], status, 'Ação manual declarada', item['revision'], day,
                               confirmed=True, reevaluation_date='2026-10-22')
        return planner.get_batch(bid)['items'][0]
    first = apply('2026-10-14')
    view = service.current_overview('2026-10-15')
    service.record_current('reabrir', [row.qbank.topic_id], '2026-10-15', view['signature'], view['event_id'])
    reopened = service.current_overview('2026-10-15')
    assert reopened['latest'][row.qbank.topic_id]['kind'] == 'reabrir'
    assert reopened['suggestions']
    assert service.store.events()[0]['topics'][0]['planner_item_id'] == first['id']
    assert service.store.events()[0]['topics'][0]['revision'] == first['revision']
    service.record_current('manter', [row.qbank.topic_id], '2026-10-15', reopened['signature'], reopened['event_id'])
    kept = service.current_overview('2026-10-15')
    assert kept['latest'][row.qbank.topic_id]['kind'] == 'manter'
    service.record_current('reabrir', [row.qbank.topic_id], '2026-10-15', kept['signature'], kept['event_id'])
    assert service.current_overview('2026-10-15')['suggestions']
    planner.transition(first['id'], 'reativado', 'Reativação manual', first['revision'], '2026-10-15', confirmed=True)
    second = apply('2026-10-15')  # Mesmo dia da reabertura local, outro lote.
    after = service.current_overview('2026-10-15')
    assert after['latest'][row.qbank.topic_id]['kind'] == 'aplicado'
    assert after['latest'][row.qbank.topic_id]['topic']['planner_item_id'] == second['id']
    assert after['suggestions'] == []
    assert len(service.store.events()) == 3
    assert len(after['legacy_history']) == 1


def test_current_action_preserves_history_and_returns_for_review_after_seven_days(tmp_path, sample_pdf, monkeypatch):
    repo, adaptive, service, *_ = ready_service(tmp_path, sample_pdf)
    view = service.current_overview('2026-10-15')
    topic = view['suggestions'][0]
    before = adaptive.store.events()
    event = service.record_current('aplicado', [topic['topic_id']], '2026-10-15', view['signature'], view['event_id'])
    assert service.record_current('aplicado', [topic['topic_id']], '2026-10-15', view['signature'], view['event_id']) == event
    assert service.current_overview('2026-10-15')['suggestions'] == []
    due = service.current_overview('2026-10-22')
    assert due['reevaluate'][0]['topic_id'] == topic['topic_id']
    assert service.store.events()[0]['sources']['incidence'][0]['observed_date'] == '2026-10-15'
    from datetime import date
    monkeypatch.setattr('osler.planner_service.today_local', lambda: date(2026, 10, 22))
    service.record_current('reabrir', [topic['topic_id']], '2026-10-22', due['signature'], due['event_id'])
    assert len(service.store.events()) == 2
    assert adaptive.store.events() == before


@pytest.mark.parametrize('mutation', ['profile', 'day', 'study', 'direct_observation'])
def test_current_changed_source_prevents_stale_action(tmp_path, sample_pdf, mutation):
    from dataclasses import replace
    from osler.study_models import AdaptiveProfile, StudyEntry, StudyDay
    from test_classification import known
    repo, adaptive, service, assessment, matching, row = ready_service(tmp_path, sample_pdf)
    if mutation == 'direct_observation':
        assessment.save_observation(matching, row.row_id, known(acerto_primeira_tentativa=95, acerto_ultima_tentativa=95), 0)
    view = service.current_overview('2026-10-15')
    topic = view['suggestions'][0]
    if mutation == 'profile': adaptive.store.save_profile(replace(AdaptiveProfile(), recent_days=30), 0)
    if mutation == 'day': adaptive.store.save_day('2026-10-15', StudyDay(questions=10), 0)
    if mutation == 'study': adaptive.save_entry(StudyEntry(row.qbank.path, '2026-10-15', 10, 2), 'poor')
    if mutation == 'direct_observation':
        import json
        with repo._connection() as db:
            record = db.execute('SELECT id,payload FROM observations WHERE active=1').fetchone()
            payload = json.loads(record['payload']); payload['erros_criticos'] = True
            db.execute('UPDATE observations SET payload=? WHERE id=?', (json.dumps(payload), record['id']))
    with pytest.raises(ValueError, match='[Aa]tualiz'):
        service.record_current('aplicado', [topic['topic_id']], '2026-10-15', view['signature'], view['event_id'])
    assert service.store.events() == []


def test_current_append_transaction_rejects_day_change_after_read(tmp_path, sample_pdf, monkeypatch):
    from osler.study_models import StudyDay
    repo, adaptive, service, *_ = ready_service(tmp_path, sample_pdf)
    view = service.current_overview('2026-10-15')
    original = service.store.append
    def concurrent(payload, expected_id, evidence_token):
        adaptive.store.save_day('2026-10-15', StudyDay(questions=10), 0)
        return original(payload, expected_id, evidence_token)
    monkeypatch.setattr(service.store, 'append', concurrent)
    with pytest.raises(ValueError, match='[Aa]tualiz'):
        service.record_current('aplicado', [view['suggestions'][0]['topic_id']], '2026-10-15', view['signature'], view['event_id'])
    assert service.store.events() == []


def test_current_snapshot_does_not_mix_old_states_with_new_action_history(tmp_path, sample_pdf, monkeypatch):
    from osler.adaptive_service import AdaptiveService
    repo, adaptive, service, *_ = ready_service(tmp_path, sample_pdf)
    initial = service.current_overview('2026-10-15')
    original = AdaptiveService.overview
    changed = False
    def concurrent(self, *args, **kwargs):
        nonlocal changed
        view = original(self, *args, **kwargs)
        if not changed:
            changed = True
            topic = initial['suggestions'][0]
            # Ação em outra tela após os estados serem lidos.
            service.store.append({'kind': 'aplicado', 'day': '2026-10-15', 'topics': [topic], 'sources': {}},
                                 0, service.store.evidence_token())
        return view
    monkeypatch.setattr(AdaptiveService, 'overview', concurrent)
    current = service.current_overview('2026-10-15')
    assert current['signature'] != initial['signature']
    assert current['suggestions'] == []
    assert current['event_id'] == 1


def test_adverse_source_in_another_report_pair_also_protects_current_view(tmp_path, sample_pdf):
    from osler.matching_service import load_matching
    from osler.service import import_bytes
    from test_classification import known
    repo, adaptive, service, assessment, matching, row = ready_service(tmp_path, sample_pdf)
    old = import_bytes(repo, sample_pdf(kind='flashcards', date='13/10/2026'), 'old.pdf').report
    other = load_matching(repo, matching.qbank_report_id, old.file_sha256)
    other_row = next(r for r in other.rows if r.qbank and r.qbank.path == row.qbank.path)
    assessment.save_observation(other, other_row.row_id, known(erros_criticos=True), 0)
    view = service.current_overview('2026-10-15')
    assert view['suggestions'] == []
    assert any(t['topic_id'] == row.qbank.topic_id for t in view['protected'])


def test_current_ui_shows_selective_evidence_and_records_real_manual_action(tmp_path, sample_pdf, monkeypatch, project_root):
    from streamlit.testing.v1 import AppTest
    repo, adaptive, service, *_ = ready_service(tmp_path, sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(project_root/'app.py'), default_timeout=30).run()
    open_view(app,main='Diminuir revisões')
    app.radio(key='ec_mode').set_value('Reduzir outras revisões').run()
    assert not app.exception
    assert any('Sugestões com os dados atuais' == s.value for s in app.subheader)
    assert any('High Yield' in c.value for c in app.caption)
    view = service.current_overview('2026-10-15')
    app.multiselect(key='current_reduction_selection').set_value([view['suggestions'][0]['topic_id']]).run()
    next(b for b in app.button if b.label == 'Já fiz essa redução seletiva na Osler').click().run()
    assert not app.exception
    assert service.store.events()[0]['kind'] == 'aplicado'
    assert service.store.events()[0]['policy_version'] == 'current-reduction-v1'
