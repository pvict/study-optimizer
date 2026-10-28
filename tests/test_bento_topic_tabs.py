"""Contratos das abas secundárias de Temas, somente em dados temporários."""
from dataclasses import replace

import pytest
from streamlit.testing.v1 import AppTest

from osler.adaptive_service import AdaptiveService
from osler.exam_goals import ExamGoals, ExamTarget
from osler.storage import Repository
from osler.study_errors import ErrorStore, StudyError
from osler.study_models import StudyEntry


DAY = '2026-10-15'


def tab_app(tmp_path, monkeypatch, module, function):
    monkeypatch.setenv('BENTO_TOPIC_TABS_ROOT', str(tmp_path))
    return AppTest.from_string(f'''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.{module} import {function}
{function}(AdaptiveService(Repository(os.environ['BENTO_TOPIC_TABS_ROOT'])))
''', default_timeout=60).run()


def error_buttons(app, prefix='resolve_error_'):
    return [b for b in app.button if b.key and b.key.startswith(prefix)]


def seed_errors(tmp_path, count=25):
    service = AdaptiveService(Repository(tmp_path))
    store = ErrorStore(service.repository)
    errors = [store.save(StudyError(['Área ausente', 'Tema ' + str(i % 2)], DAY,
                                   'chute', 'Conceito ' + str(i))) for i in range(count)]
    return service, store, errors


def test_errors_show_twelve_per_page_and_reset_page_with_filter(tmp_path, monkeypatch):
    _, store, errors = seed_errors(tmp_path)
    app = tab_app(tmp_path, monkeypatch, 'study_errors_ui', 'render_errors')
    assert not app.exception
    assert len(error_buttons(app)) == 12
    first = {b.key for b in error_buttons(app)}
    assert any('25 erros · página 1 de 3' in c.value for c in app.caption)
    app.number_input(key='study_errors_page').set_value(3).run()
    assert not app.exception and len(error_buttons(app)) == 1
    assert first.isdisjoint({b.key for b in error_buttons(app)})
    app.selectbox(key='study_errors_topic').set_value(tuple(errors[0]['path'])).run()
    assert not app.exception
    assert app.number_input(key='study_errors_page').value == 1
    assert len(error_buttons(app)) == 12
    assert any('area ausente' in m.value for m in app.markdown)
    assert len(store.events()) == 25


def test_errors_resolve_and_void_preserve_source_and_corrected_history(tmp_path, monkeypatch):
    service, store, _ = seed_errors(tmp_path, 12)
    service.store.save_batch([('original-block', StudyEntry(['Área ausente', 'Tema vinculado'], DAY,
                                                         5, correct=2), 0)])
    linked = store.save(StudyError(['Área ausente', 'Tema vinculado'], DAY, 'chute',
                                  'Conceito original', 'original-block'))
    corrected = store.save(replace(StudyError(linked['path'], DAY, 'chute'),
                                   note='Conceito corrigido', source_session_id='original-block'),
                           error_key=linked['error_key'], expected_version=1)
    app = tab_app(tmp_path, monkeypatch, 'study_errors_ui', 'render_errors')
    assert len(error_buttons(app)) == 12
    app.button(key='resolve_error_' + corrected['error_key']).click().run()
    assert not app.exception
    closed = next(e for e in store.events() if e['error_key'] == linked['error_key'] and e['action'] == 'resolve')
    assert closed['version'] == 3 and closed['source_session_id'] == 'original-block'
    assert closed['note'] == 'Conceito corrigido'
    assert store.events()[-3]['note'] == 'Conceito original'
    app.button(key=error_buttons(app, 'void_error_')[0].key).click().run()
    assert not app.exception and store.events()[-1]['action'] == 'void'
    assert len(service.store.events()) == 1


def test_errors_page_clamps_when_last_item_disappears(tmp_path, monkeypatch):
    _, _, _ = seed_errors(tmp_path, 25)
    app = tab_app(tmp_path, monkeypatch, 'study_errors_ui', 'render_errors')
    app.number_input(key='study_errors_page').set_value(3).run()
    error_buttons(app)[0].click().run()
    assert not app.exception
    assert app.number_input(key='study_errors_page').value == 2
    assert len(error_buttons(app)) == 12


@pytest.mark.parametrize('confidence,label', [
    ('informado', 'Informada'), ('conferido', 'Conferida'), ('estimado', 'Estimada'),
    (None, 'Não informada'), ('desconhecida', 'Não informada'),
])
def test_goal_confidence_joins_by_id_and_unknown_is_not_invented(tmp_path, monkeypatch, confidence, label):
    service = AdaptiveService(Repository(tmp_path))
    goals = ExamGoals(service.repository)
    a = goals.save(ExamTarget('Mesma banca', '2026-11-15', 70, 100, 'Fonte A'))
    b = goals.save(ExamTarget('Mesma banca', '2026-11-15', 80, 100, 'Fonte B', cutoff_confidence='conferido'))
    # A ordem é deliberadamente diferente do relatório. Metadado antigo ausente
    # ou desconhecido nunca deve virar um grau de confiança presumido.
    metadata = [b, {**a, 'target': {**a['target'], 'cutoff_confidence': confidence}}]
    monkeypatch.setattr(ExamGoals, 'active', lambda self: metadata)
    before = goals.events()
    app = tab_app(tmp_path, monkeypatch, 'goal_risk_ui', 'render_goal_risk')
    assert not app.exception
    captions = [c.value for c in app.caption]
    source_a = next(c for c in captions if 'Fonte A' in c)
    source_b = next(c for c in captions if 'Fonte B' in c)
    assert 'Confiança da fonte: ' + label in source_a
    assert 'Confiança da fonte: Conferida' in source_b
    assert goals.events() == before
    assert any('Não é uma previsão de aprovação.' in i.value for i in app.info)


def test_goal_preserves_zero_accuracy_sample_range_and_insufficient_label(tmp_path, monkeypatch):
    service = AdaptiveService(Repository(tmp_path))
    ExamGoals(service.repository).save(ExamTarget('Banca', '2026-11-15', 70, 100, 'Documento'))
    service.store.save_batch([('zero', StudyEntry(['Área', 'Tema'], DAY, 40, correct=0), 0)])
    app = tab_app(tmp_path, monkeypatch, 'goal_risk_ui', 'render_goal_risk')
    assert not app.exception
    area = next(f.value for f in app.dataframe if 'Área' in f.value.columns)
    assert area.iloc[0]['Acertos'] == 0 and area.iloc[0]['Questões'] == 40
    assert area.iloc[0]['Faixa observada (95%)'] == '0.0% a 8.8%'
    assert any('Sem dados suficientes' in m.value for m in app.markdown)


def test_triage_empty_preview_never_applies_or_changes_history(tmp_path, monkeypatch):
    service = AdaptiveService(Repository(tmp_path))
    before = service.store.events()
    app = tab_app(tmp_path, monkeypatch, 'study_triage_ui', 'render_triage')
    app.button(key='triage_preview').click().run()
    assert not app.exception
    assert app.button(key='triage_apply').disabled
    assert any('Não há redução segura' in i.value for i in app.info)
    assert service.store.events() == before
