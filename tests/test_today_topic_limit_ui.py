from dataclasses import replace
from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.study_models import AdaptiveProfile
from test_assessments import setup_assessment
from ui_actions import confirm_action


def test_today_topic_limit_requires_confirmation_and_persists(tmp_path,sample_pdf,monkeypatch,project_root):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.store.save_profile(replace(AdaptiveProfile(),max_topics=4,max_questions=120),0)
    before=service.store.profile()['configured_profile'];events=service.store.events()
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    field=app.number_input(key='today_max_topics')
    assert field.value==4
    field.set_value(7)
    app.slider(key='today_minimum_new_share').set_value(25)
    app.button(key='save_today_distribution').click().run()
    assert service.store.profile()['configured_profile']==before
    confirm_action(app)
    assert not app.exception
    after=service.store.profile()['configured_profile']
    assert after=={**before,'max_topics':7,'minimum_new_share':.25}
    assert service.store.events()==events
    app.button(key='nav_calendar').click().run()
    app.button(key='nav_today').click().run()
    assert not app.exception and app.number_input(key='today_max_topics').value==7
