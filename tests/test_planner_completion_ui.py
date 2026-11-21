from ui_actions import confirm_action
from copy import deepcopy
from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from test_planner_completion import setup_plan,DAY
from conftest import open_view


def test_day_can_close_documented_planner_and_restore_complement(tmp_path,monkeypatch,project_root):
    service,topics=setup_plan(tmp_path,monkeypatch)
    monkeypatch.setattr(AdaptiveService,'catalog',lambda *a,**kw:(deepcopy(topics),{'qbank':None,'flashcards':None}))
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert app.button(key='skip_complement_A').label=='Encerrar tema hoje'
    before=service.store.events()
    confirm_action(app.button(key='skip_complement_A').click().run())
    assert not app.exception
    assert not any(b.label=='Registrar complemento' for b in app.button)
    assert any('não contam como respondidas' in c.value for c in app.caption)
    assert service.store.events()==before
    app.run()
    assert not app.exception and not any(b.key=='skip_complement_A' for b in app.button)
    restore=next(b for b in app.button if b.key.startswith('restore_complement_'))
    confirm_action(restore.click().run())
    assert not app.exception and app.button(key='skip_complement_A')
    assert service.store.events()==before
    open_view(app,adaptive='Calendário')
    confirm_action(app.button(key='calendar_skip_complement_A').click().run())
    assert not app.exception
    assert not any(i['topic_id']=='A' for i in service.overview(DAY)['plan']['items'])
    assert any(b.label=='Desfazer dispensa' for b in app.button)
