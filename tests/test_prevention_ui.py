from datetime import date
from streamlit.testing.v1 import AppTest
from test_study_prevention import prevention_service


def test_open_orange_day_compare_apply_and_undo_prevention(tmp_path,monkeypatch,project_root,sample_pdf):
    service,t=prevention_service(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    app.radio(key='adaptive_view').set_value('Calendário').run()
    app.date_input(key='calendar_reference').set_value(date(2026,10,21)).run()
    assert not app.exception
    app.button(key='calendar_risks_2026-10-21').click().run()
    assert not app.exception
    assert app.toggle(key='prevention_enabled').value
    assert any('Sem vaga a partir de' in str(f.value.columns) for f in app.get('dataframe')) or any('prevention_topics_' in str(e.key) for e in app.get('data_editor'))
    app.button(key='compare_prevention').click().run()
    assert not app.exception and not app.error,[e.value for e in app.error]
    assert any('Após redistribuir' in str(f.value.columns) for f in app.dataframe)
    app.button(key='apply_prevention').click().run()
    assert not app.exception and not app.error,[e.value for e in app.error]
    assert service.replanning()['policies']
    app.button(key='undo_prevention').click().run()
    assert not app.exception and not app.error,[e.value for e in app.error]
    assert not service.replanning()['policies']
    assert len(service.store.active('2026-10-15'))==1


def test_preventive_panel_handles_no_forecast_risk(tmp_path,monkeypatch,project_root,sample_pdf):
    service,t=prevention_service(tmp_path,sample_pdf)
    service.configure_day('2026-10-21',20,'normal',1)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    app.radio(key='adaptive_view').set_value('Calendário').run()
    app.toggle(key='prevention_enabled').set_value(True).run()
    assert not app.exception
    assert any('nenhuma pendência prevista' in i.value.lower() for i in app.info)
