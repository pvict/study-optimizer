from conftest import open_view
from datetime import date
from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from test_assessments import setup_assessment


def test_calendar_has_real_delay_and_preview_apply_undo_without_fake_results(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    t=max(service.catalog('2026-10-15')[0],key=lambda t:t['total'])
    service.save_entry(StudyEntry(t['path'],'2026-10-01',20,10,confident_correct=10),'old')
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Calendário')
    assert not app.exception
    assert any('atrasad' in str(m.value).lower() for m in app.caption) or any('atrasad' in str(h.value).lower() for h in app.get('html'))
    app.radio(key='replan_mode').set_value('reviews').run()
    app.button(key='generate_replan_preview').click().run()
    assert not app.exception and not app.error,[e.value for e in app.error]
    assert any('Reagendado para' in str(f.value.columns) for f in app.dataframe)
    for mode in ['extra','custom','balanced','reviews']:
        app.radio(key='replan_mode').set_value(mode).run()
        app.button(key='generate_replan_preview').click().run()
        assert not app.exception and not app.error,[e.value for e in app.error]
    app.button(key='apply_replan_preview').click().run()
    assert not app.exception and not app.error,[e.value for e in app.error]
    assert service.replanning()['active']
    app.button(key='undo_last_replan').click().run()
    assert not app.exception and not app.error,[e.value for e in app.error]
    assert not service.replanning()['active']
    assert len(service.store.active('2026-10-15'))==1


def test_past_calendar_does_not_invent_study_when_no_plan_exists(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Calendário')
    app.date_input(key='calendar_reference').set_value(date(2026,10,10)).run()
    assert not app.exception
    app.button(key='calendar_cell_2026-10-10').click().run()
    assert not app.exception
    assert any('sem plano' in c.value.lower() for c in app.info)
