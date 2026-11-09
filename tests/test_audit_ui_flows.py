from streamlit.testing.v1 import AppTest

from test_assessments import setup_assessment
from test_error_cards_service import setup


def test_hidden_flashcard_forecast_is_not_executed(tmp_path, monkeypatch):
    from osler.error_cards_service import ErrorCardsService
    service, day, html = setup(tmp_path)
    service.import_html(html, 'cards.html', day, 'pending', service.token())
    monkeypatch.setenv('AUDIT_UI_ROOT', str(tmp_path))
    def unavailable(*args, **kwargs):
        raise RuntimeError('forecast must run only when requested')
    monkeypatch.setattr(ErrorCardsService, 'forecast', unavailable)
    app = AppTest.from_string('''
import os
from osler.storage import Repository
from osler.error_cards_ui import render_error_cards
render_error_cards(Repository(os.environ['AUDIT_UI_ROOT']))
''', default_timeout=60).run()
    assert not app.exception
    assert not app.file_uploader
    app.session_state['ec_tabs'] = 'Próximos dias'
    app.run()
    assert app.exception and 'forecast must run only' in app.exception[0].message


def test_invalid_study_result_is_rejected_before_confirmation(tmp_path, monkeypatch, sample_pdf, project_root):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR', str(repo.root))
    app = AppTest.from_file(str(project_root/'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Registrar este bloco').click().run()
    app.number_input(key='study_n').set_value(10)
    app.number_input(key='study_correct').set_value(11)
    next(b for b in app.button if b.label == 'Salvar resultado e atualizar meu plano').click().run()
    assert not app.exception
    assert any('Acertos não podem passar de 10' in e.value for e in app.error)
    assert not any(b.key == 'action_confirm' for b in app.button)


def test_mock_tabs_render_only_selected_content_and_preserve_draft(tmp_path, monkeypatch):
    monkeypatch.setenv('AUDIT_UI_ROOT', str(tmp_path))
    app = AppTest.from_string('''
import os
import streamlit as st
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.mock_exams_ui import render_mock_exams
render_mock_exams(AdaptiveService(Repository(os.environ['AUDIT_UI_ROOT'])))
''', default_timeout=60).run()
    assert not app.exception
    assert not any(b.key == 'mock_save' for b in app.button)
    app.session_state['mock_sections'] = 'Resultados'
    app.run()
    app.text_input(key='mock_field_name').set_value('Rascunho pessoal').run()
    app.number_input(key='mock_field_questions').set_value(30).run()
    app.session_state['mock_sections'] = 'Programação'
    app.run()
    app.session_state['mock_sections'] = 'Resultados'
    app.run()
    assert not app.exception
    assert app.text_input(key='mock_field_name').value == 'Rascunho pessoal'
    assert app.number_input(key='mock_field_questions').value == 30


def test_calendar_closed_management_does_not_execute_tools(tmp_path, monkeypatch, sample_pdf):
    from osler import study_calendar_ui
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    monkeypatch.setenv('AUDIT_UI_ROOT', str(repo.root))
    def unavailable(*args, **kwargs):
        raise RuntimeError('closed calendar tool executed')
    for name in ('render_mock_schedule', 'render_prevention', 'render_capacity_summary', 'render_final_review', 'render_mock_days'):
        monkeypatch.setattr(study_calendar_ui, name, unavailable)
    app = AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_calendar_ui import render_calendar
render_calendar(AdaptiveService(Repository(os.environ['AUDIT_UI_ROOT'])),lambda *args:None)
''', default_timeout=60).run()
    assert not app.exception


def test_today_opens_exact_area_occurrence(tmp_path,monkeypatch,sample_pdf,project_root):
    from test_mock_schedule import configured
    service,_=configured(tmp_path,sample_pdf)
    service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-26',2,20,['UNESP']))
    task=service.overview('2026-10-15')['plan']['area_tasks'][0]
    monkeypatch.setenv('OSLER_DATA_DIR',str(service.repository.root))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    app.button(key='area_today_'+task['id']).click().run()
    assert not app.exception
    assert app.session_state['mock_sections']=='Treinos por área'
    assert app.selectbox(key='area_result_id').value==task['id']


def test_plan_download_marks_old_export_and_keeps_file(tmp_path,monkeypatch,sample_pdf,project_root):
    from osler.adaptive_service import AdaptiveService
    from pathlib import Path
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    monkeypatch.setenv('OSLER_DATA_DIR',str(repo.root))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    next(b for b in app.button if b.label=='Preparar plano para download').click().run()
    old=Path(app.session_state['study_download_path']);data=old.read_bytes()
    before=service.store.day('2026-10-15',60)
    service.configure_day('2026-10-15',80,'normal',before['revision'])
    app.run()
    assert not app.exception
    assert any('exportação anterior' in c.value.lower() for c in app.caption)
    assert old.is_file() and old.read_bytes()==data
    assert not any(b.label=='Baixar plano de questões' for b in app.get('download_button'))
