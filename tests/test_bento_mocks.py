import pytest
from streamlit.testing.v1 import AppTest

from osler.mock_exams import MockExam, MockExams
from osler.storage import Repository


def test_summary_keeps_missing_duration_and_score_unknown():
    from osler.mock_exams_ui import _summary
    summary = _summary(MockExam('2026-10-14', 80, 60).to_dict())
    assert summary['date'] == '14/10/2026'
    assert summary['duration'] == '—'
    assert summary['score'] == '—'
    assert summary['accuracy'] == '60 / 80 · 75,0% · n=80'


def test_summary_preserves_informed_score_scale_and_zero():
    from osler.mock_exams_ui import _summary
    exam = MockExam('2026-10-14', 80, 60, minutes_used=135.5, score=0, max_score=20).to_dict()
    summary = _summary(exam)
    assert summary['duration'] == '135,5 min'
    assert summary['score'] == '0 / 20'
    assert summary['accuracy'] == '60 / 80 · 75,0% · n=80'


def test_summary_html_and_area_bars_escape_external_text_and_show_wilson():
    from osler.mock_exams_ui import _summary_html, _area_results_html
    exam = MockExam('2026-10-14', 20, 14, name='<img src=x>',
                    areas=[{'area': 'Clínica Médica', 'questions': 10, 'correct': 7},
                           {'area': '<script>área</script>', 'questions': 10, 'correct': 7}]).to_dict()
    html = _summary_html(exam) + _area_results_html(exam['areas'])
    assert '<img' not in html and '<script>' not in html
    assert '&lt;img src=x&gt;' in html and '&lt;script&gt;área&lt;/script&gt;' in html
    assert 'o-bar-fill--clinica' in html and 'o-bar-fill--neutral' in html
    assert 'n=10' in html and '39,7–89,2%' in html


APP = '''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.mock_exams_ui import render_mock_exams
render_mock_exams(AdaptiveService(Repository(os.environ['BENTO_MOCK_ROOT'])))
'''


def test_results_summary_precedes_form_and_render_does_not_create_study(tmp_path, monkeypatch):
    from osler.study_storage import StudyStore
    from osler.study_agenda import StudyAgenda
    repo = Repository(tmp_path)
    mocks = MockExams(repo)
    mocks.save(MockExam('2026-10-13', 40, 30, name='Anterior'))
    saved = mocks.save(MockExam('2026-10-14', 50, 35, name='Último registrado',
                               areas=[{'area': 'Pediatria', 'questions': 20, 'correct': 12}]))
    before = mocks.events()
    monkeypatch.setenv('BENTO_MOCK_ROOT', str(tmp_path))
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ['Programação', 'Resultados', 'Treinos por área', 'Correção']
    assert [s.value for s in app.subheader].index('Último simulado') < [s.value for s in app.subheader].index('Registrar simulado')
    assert app.number_input(key='mock_field_questions').value is None
    assert app.button(key='mock_save') and app.button(key='mock_edit') and app.button(key='mock_void')
    app.selectbox(key='mock_selected').set_value(saved['exam_key']).run()
    assert not app.exception and not StudyStore(repo).events() and not StudyAgenda(repo).records()
    assert mocks.events() == before


def test_latest_summary_does_not_compare_accuracy_with_cutoff(tmp_path, monkeypatch):
    from osler.exam_goals import ExamGoals, ExamTarget
    repo = Repository(tmp_path)
    target = ExamGoals(repo).save(ExamTarget('Banca A', '2027-10-01', 12, 20, 'Referência fornecida'))
    MockExams(repo).save(MockExam('2026-10-14', 100, 90, institution='Banca A', target_id=target['target_id']))
    monkeypatch.setenv('BENTO_MOCK_ROOT', str(tmp_path))
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert not app.exception
    assert any('Corte informado: 60.0%' in item.value for item in app.info)
    assert not any('o acerto das questões não é comparado' in item.value for item in app.caption)
    app.session_state['show_explanations']=True
    app.run()
    assert any('o acerto das questões não é comparado' in item.value for item in app.caption)
    assert not any('Diferença para a referência' in item.value for item in app.caption)


@pytest.mark.parametrize('target_id,institution,expected', [
    (None, 'Banca A', False), ('alvo', None, False),
    ('alvo', 'Banca B', False), ('alvo', 'banca a', True),
])
def test_comparison_requires_linked_same_institution_and_keeps_informed_scales(target_id, institution, expected):
    exam = MockExam('2026-10-14', 100, 90, institution=institution, target_id=target_id,
                    score=14, max_score=20).to_dict()
    targets = [{'target_id': 'alvo', 'target': {'institution': 'Banca A', 'cutoff_score': 120,
                'max_score': 200, 'cutoff_source': 'Referência fornecida'}}]
    app = AppTest.from_string('from osler.mock_exams_ui import _comparison\n'
                              f'_comparison({exam!r}, {targets!r})').run()
    assert not app.exception
    assert any('Corte informado: 60.0%' in item.value for item in app.info) == expected
    assert any('Nota informada no simulado: 70.0%. Diferença para a referência: +10.0' in item.value for item in app.caption) == expected


def test_schedule_preview_is_separate_from_apply_and_keeps_study_unchanged(tmp_path, monkeypatch):
    from datetime import date
    from osler.adaptive_service import AdaptiveService
    monkeypatch.setenv('BENTO_MOCK_ROOT', str(tmp_path))
    service = AdaptiveService(Repository(tmp_path))
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert not app.exception
    app.date_input(key='mock_schedule_first').set_value(date(2026, 10, 18))
    app.button(key='mock_schedule_preview').click().run()
    assert not app.exception and app.button(key='mock_schedule_apply')
    assert any('os blocos normais são dispensados' in item.value for item in app.caption)
    assert service.mock_schedule() is None and not service.agenda.records() and not service.store.events()
    assert not MockExams(service.repository).active()
