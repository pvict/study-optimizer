from streamlit.testing.v1 import AppTest

from osler.mock_exams import MockExams, MockExam
from osler.storage import Repository


APP = '''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.mock_exams_ui import render_mock_exams, render_mock_settings
service = AdaptiveService(Repository(os.environ['MOCK_TEST_ROOT']))
render_mock_exams(service)
render_mock_settings(service)
'''


def test_mock_short_form_save_edit_void_preserves_versions(tmp_path, monkeypatch):
    monkeypatch.setenv('MOCK_TEST_ROOT', str(tmp_path))
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert not app.exception
    app.number_input(key='mock_field_questions').set_value(100)
    app.number_input(key='mock_field_correct').set_value(70)
    app.button(key='mock_save').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not app.error
    mocks = MockExams(Repository(tmp_path))
    assert len(mocks.active()) == 1
    app.button(key='mock_error_later').click().run()
    app.button(key='mock_edit').click().run()
    app.number_input(key='mock_field_correct').set_value(80)
    app.button(key='mock_save').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not app.error
    assert mocks.active()[0]['exam']['correct'] == 80
    app.button(key='mock_error_later').click().run()
    app.button(key='mock_void').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not mocks.active()
    assert len(mocks.events()) == 3
    assert any(e.label == 'Histórico de versões dos simulados' for e in app.expander)


def test_mock_form_validation_and_optional_cadence(tmp_path, monkeypatch):
    monkeypatch.setenv('MOCK_TEST_ROOT', str(tmp_path))
    app = AppTest.from_string(APP, default_timeout=30).run()
    app.button(key='mock_save').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and app.error
    assert not MockExams(Repository(tmp_path)).active()
    app.number_input(key='mock_cadence').set_value(14)
    app.button(key='mock_save_settings').click().run()
    app.button(key='action_confirm').click().run()
    from osler.study_storage import StudyStore
    assert not app.exception and StudyStore(Repository(tmp_path)).profile()['profile']['mock_cadence_days'] == 14


def test_mock_cutoff_only_same_institution_and_no_automatic_entries(tmp_path, monkeypatch):
    from osler.exam_goals import ExamGoals, ExamTarget
    from osler.study_storage import StudyStore
    repo = Repository(tmp_path)
    target = ExamGoals(repo).save(ExamTarget('Banca A', '2027-10-01', 75, 100, 'Documento teste'))
    MockExams(repo).save(MockExam('2026-10-15', 100, 80, institution='Banca B'))
    monkeypatch.setenv('MOCK_TEST_ROOT', str(tmp_path))
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert not app.exception and not StudyStore(repo).events()
    assert not any('bancas diferem' in c.value.lower() for c in app.caption)
    app.session_state['show_explanations']=True
    app.run()
    assert any('bancas diferem' in c.value.lower() for c in app.caption)
    assert not any('Corte informado:' in c.value for c in app.info)
    MockExams(repo).save(MockExam('2026-10-15', 100, 80, institution='Banca A', target_id=target['target_id'], score=80, max_score=100))
    app.run()
    app.selectbox(key='mock_selected').set_value(MockExams(repo).active()[-1]['exam_key']).run()
    assert not app.exception
    assert any('Corte informado:' in c.value for c in app.info)


def test_mock_ui_conversion_retraction_and_day_preview_apply_undo(tmp_path, monkeypatch, sample_pdf):
    from test_assessments import setup_assessment
    from osler.study_storage import StudyStore
    from osler.study_agenda import StudyAgenda
    repo, *_, row = setup_assessment(tmp_path, sample_pdf)
    saved = MockExams(repo).save(MockExam('2026-10-15', 100, 80, unseen_questions=True,
                                        topics=[{'path': row.qbank.path, 'questions': 20, 'correct': 14}]))
    monkeypatch.setenv('MOCK_TEST_ROOT', str(tmp_path))
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert not app.exception and not StudyStore(repo).events()
    app.button(key='mock_convert').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not app.error
    app.button(key='mock_convert').click().run()
    app.button(key='action_confirm').click().run()
    assert len(StudyStore(repo).events()) == 1
    app.button(key='mock_void').click().run()
    app.button(key='action_confirm').click().run()
    assert app.error and len(MockExams(repo).active()) == 1
    app.button(key='mock_retract').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not StudyStore(repo).active('2026-10-15')
    app.button(key='mock_day_preview').click().run()
    assert not app.exception and not app.error
    assert not StudyAgenda(repo).records()
    app.button(key='mock_day_apply').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not app.error
    assert len(StudyAgenda(repo).records()) == 1
    app.button(key='mock_day_undo_button').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not app.error
    assert len(StudyAgenda(repo).records()) == 2
