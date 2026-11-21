from osler.study_models import AdaptiveProfile
from osler.study_replanning import effective_routine


def test_external_day_reserves_capacity_without_inventing_topic_results():
    p=AdaptiveProfile(max_questions=120)
    config={'questions':108,'kind':'normal'}
    same,q=effective_routine(p,config,{'mode':'external_day','external_target':108,'external_done':62})
    assert q==0 and same==p
    assert effective_routine(p,config,{})[1]==108


def test_external_day_shows_manual_volume_and_no_extra_question_blocks(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from test_return_deferral import configured,DAY
    s=configured(tmp_path,monkeypatch)
    s.configure_day(DAY,108,'normal',0)
    s.agenda.append({'kind':'reschedule.apply','scope':'external_day','created_day':DAY,'selected':[],'rows':[],'cutoff':0,
                    'overrides':{DAY:{'mode':'external_day','external_target':108,'external_done':62}}},s.agenda.token())
    before=s.store.events()
    app=AppTest.from_string('''
import streamlit as st
from osler.study_day_ui import render_study_day
render_study_day(st.session_state.service,lambda *a:None,lambda *a:None)
''',default_timeout=30)
    app.session_state['service']=s;app.run()
    assert not app.exception
    assert any('62 questões feitas. Restam 46' in m.value for m in app.markdown)
    assert not any(b.label=='Registrar este bloco' for b in app.button)
    assert s.store.events()==before
