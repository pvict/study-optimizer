from ui_actions import confirm_action
from conftest import open_view
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService


def test_share_can_be_changed_from_today_and_settings(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=45).run()
    app.slider(key='today_new_share').set_value(50)
    confirm_action(app.button(key='save_today_distribution').click().run())
    assert not app.exception
    assert not app.error,[e.value for e in app.error]
    assert AdaptiveService(repo).store.profile()['profile']['new_share']==.5
    open_view(app,adaptive='Ajustes')
    assert not app.exception
    assert app.slider(key='settings_new_share').value==50
