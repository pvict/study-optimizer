from streamlit.testing.v1 import AppTest
from test_return_deferral import configured,DAY


def test_preview_confirmation_and_undo_do_not_register_fake_study(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    topics,sources=service.catalog(DAY)
    app=AppTest.from_string(f'''
import streamlit as st
from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from osler.action_feedback import bind_actions
from osler.return_deferral_ui import render_return_deferral,render_return_deferral_history
service=AdaptiveService(Repository({str(tmp_path)!r}))
service.catalog=lambda *args,**kwargs:({topics!r},{sources!r})
bind_actions(service.repository)
view=service.overview({DAY!r})
for item in view['plan']['items']:
    st.write(item['path'][-1])
    render_return_deferral(service,view,item)
render_return_deferral_history(service,view)
''',default_timeout=30).run()
    assert not app.exception
    app.button(key='return_defer_open_A').click().run()
    assert not app.exception and app.button(key='return_defer_apply_A')
    assert not service.overview(DAY)['agenda']['rows']
    app.button(key='return_defer_apply_A').click().run()
    assert not app.exception and app.button(key='action_confirm')
    assert not service.overview(DAY)['agenda']['rows']
    app.button(key='action_confirm').click().run()
    assert not app.exception
    assert not any(b.key=='return_defer_open_A' for b in app.button)
    assert len(service.store.events())==1
    undo=next(b for b in app.button if b.label=='Desfazer adiamento')
    undo.click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and app.button(key='return_defer_open_A')
    assert len(service.store.events())==1


def test_feedback_names_old_return_without_requesting_new_same_day_review(tmp_path,monkeypatch):
    from osler.study_models import StudyEntry
    from osler.study_feedback import result_feedback
    service=configured(tmp_path,monkeypatch)
    service.save_entry(StudyEntry(['Área','A'],DAY,11,8,confident_correct=3,mode='mistas'),'today')
    view=service.overview(DAY)
    before=service.store.events()
    feedback=result_feedback(view,'today')
    assert feedback['outstanding_returns'][0]['session_id']=='source'
    assert feedback['theme_contact']>DAY
    topics,sources=service.catalog(DAY)
    app=AppTest.from_string(f'''
from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from osler.study_activity_ui import render_result_feedback
service=AdaptiveService(Repository({str(tmp_path)!r}))
service.catalog=lambda *args,**kwargs:({topics!r},{sources!r})
render_result_feedback(service.overview({DAY!r}),'today')
''',default_timeout=30).run()
    assert not app.exception
    assert any('Retorno anterior pendente' in s.value for s in app.subheader)
    assert not any('Próximo contato indicado: 15/10/2026' in m.value for m in app.markdown)
    assert any('22/10/2026' in m.value for m in app.markdown)
    assert service.store.events()==before
