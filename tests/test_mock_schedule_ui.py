from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.storage import Repository

APP='''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.mock_schedule_ui import render_mock_schedule
render_mock_schedule(AdaptiveService(Repository(os.environ['MOCK_SCHEDULE_ROOT'])))
'''


def test_schedule_ui_previews_applies_and_moves_one_occurrence(tmp_path,monkeypatch):
    from datetime import date
    monkeypatch.setenv('MOCK_SCHEDULE_ROOT',str(tmp_path))
    app=AppTest.from_string(APP,default_timeout=60).run()
    assert not app.exception
    app.date_input(key='mock_schedule_first').set_value(date(2026,10,18))
    app.button(key='mock_schedule_preview').click().run()
    assert not app.exception
    app.button(key='mock_schedule_apply').click().run()
    assert not app.exception
    service=AdaptiveService(Repository(tmp_path))
    assert service.mock_schedule()['occurrences'][0]['date']=='2026-10-18'
    app.date_input(key='mock_occurrence_date').set_value(date(2026,10,20))
    app.button(key='mock_occurrence_preview').click().run()
    app.button(key='mock_schedule_apply').click().run()
    assert not app.exception
    assert service.overview('2026-10-20')['plan']['routine_override']['mode']=='mock_reserved'
    assert service.overview('2026-10-25')['plan']['routine_override']['mode']=='mock_reserved'
    assert not service.store.events()
