from ui_actions import confirm_action
from conftest import open_view
from streamlit.testing.v1 import AppTest
from test_final_review import configured


def test_calendar_with_applied_final_review_can_render_and_undo(tmp_path,sample_pdf,monkeypatch,project_root):
    service,topic,exam=configured(tmp_path,sample_pdf)
    preview=service.preview_final_review(exam['target_id'],'2026-10-15',30)
    service.apply_final_review(preview)
    monkeypatch.setenv('OSLER_DATA_DIR',str(service.repository.root))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Calendário')
    app.session_state['calendar_management_open']=True;app.run()
    assert not app.exception
    from datetime import date
    app.date_input(key='calendar_reference').set_value(date(2026,10,29)).run()
    assert any('Prova' in str(t.value) for t in app.dataframe)
    undo=next(b for b in app.button if b.key and b.key.startswith('final_undo_'))
    confirm_action(undo.click().run())
    assert not app.exception
    assert service.overview('2026-10-28')['plan']['kind']=='normal'


def test_calendar_mock_day_undo_survives_new_browser_session(tmp_path,sample_pdf,monkeypatch,project_root):
    from osler.mock_exams import MockExamStore,MockExam
    service,topic,exam=configured(tmp_path,sample_pdf)
    mock=MockExamStore(service.repository).save(MockExam('2026-10-15',50,40))
    p=service.preview_mock_day(mock['exam_key'],1)
    service.mark_mock_day(mock['exam_key'],1,p)
    monkeypatch.setenv('OSLER_DATA_DIR',str(service.repository.root))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Calendário')
    app.session_state['calendar_management_open']=True;app.run()
    assert not app.exception
    undo=next(b for b in app.button if b.key and b.key.startswith('calendar_undo_mock_'))
    confirm_action(undo.click().run())
    assert not app.exception
    assert service.overview('2026-10-15')['plan']['kind']=='normal'


def test_final_review_undo_remains_available_after_exam_is_void(tmp_path,sample_pdf,monkeypatch,project_root):
    from osler.exam_goals import ExamGoals
    service,topic,exam=configured(tmp_path,sample_pdf)
    service.apply_final_review(service.preview_final_review(exam['target_id'],'2026-10-15',30))
    ExamGoals(service.repository).void(exam['target_id'],1)
    monkeypatch.setenv('OSLER_DATA_DIR',str(service.repository.root))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Calendário')
    app.session_state['calendar_management_open']=True;app.run()
    assert not app.exception
    assert any(b.key and b.key.startswith('final_undo_') for b in app.button)
