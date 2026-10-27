from conftest import open_view
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment


def test_action_picker_never_offers_parent_as_a_study_topic():
    app=AppTest.from_string("""
import streamlit as st
from osler.topic_picker_ui import pick_topic
topics=[{'topic_id':'parent','path':['Area','Grupo'],'is_leaf':False},
        {'topic_id':'leaf','path':['Area','Grupo','Tema específico'],'is_leaf':True}]
chosen=pick_topic(topics,'test')
st.write('SELECTED:'+chosen['topic_id'])
""").run()
    assert not app.exception
    assert any(m.value=='SELECTED:leaf' for m in app.markdown)
    app.text_input(key='test_search').set_value('Grupo').run()
    assert not app.exception
    assert all('parent' not in r.options for r in app.radio)
    assert any(m.value=='SELECTED:leaf' for m in app.markdown)


def test_trajectory_before_first_import_shows_next_step_instead_of_crashing():
    app=AppTest.from_string("""
import streamlit as st
from osler.study_trajectory_ui import render_trajectories
from osler.study_models import AdaptiveProfile
class Store:
    def days(self): return {}
class Service: store=Store()
render_trajectories(Service(),{'profile':AdaptiveProfile().to_dict(),'planning_states':[],'date':'2026-10-15','plan':{}})
""").run()
    app.toggle(key='show_trajectories').set_value(True).run()
    assert not app.exception
    assert any('import' in i.value.lower() for i in app.info)


def test_topic_trajectory_is_accessible_without_prescribing_a_lifetime_total(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    open_view(app,adaptive='Temas e estatísticas')
    app.toggle(key='show_trajectories').set_value(True).run()
    assert not app.exception
    assert any('Próximo bloco' in str(frame.value.columns) for frame in app.dataframe)
    assert any('Revisão 1' in str(frame.value.values) for frame in app.dataframe)
    assert any('A recalcular' in str(frame.value.values) for frame in app.dataframe)
    assert not any('até a prova' in m.label for m in app.metric)


def test_today_displays_specific_stage_and_recurrent_review_details(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    assert not app.exception
    assert any('Ver próximas revisões' in e.label for e in app.expander)
    visible=[*app.markdown,*app.get('html')]
    assert any('Diagnóstico' in str(m.value) or 'Primeiro contato' in str(m.value) for m in visible)


def test_editing_legacy_aggregate_never_silently_moves_results_to_leaf(tmp_path,monkeypatch,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    from osler.study_models import StudyEntry
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    topics,_=service.catalog('2026-10-15',include_parents=True)
    parent=next(t for t in topics if not t['is_leaf'])
    service.save_entry(StudyEntry(parent['path'],'2026-10-15',40,30),'old')
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_string("""
import os
from pathlib import Path
import streamlit as st
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.adaptive_ui import _register,_edit
s=AdaptiveService(Repository(Path(os.environ['OSLER_DATA_DIR'])))
if 'loaded' not in st.session_state:
    _edit(s.store.active('2026-10-15')[0])
    st.session_state['loaded']=True
_register(s)
""").run()
    assert not app.exception
    assert any('agregado' in c.value.lower() for c in app.caption)
    next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run()
    assert not app.exception
    assert service.store.active('2026-10-15')[0]['entry']['path']==parent['path']
