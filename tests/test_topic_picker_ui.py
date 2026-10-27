from conftest import open_view
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment


def test_theme_picker_supports_hierarchy_and_typing_without_flat_dropdown(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    assert not app.exception
    assert any(t.key=='extra_search' for t in app.text_input)
    assert any(s.key=='extra_area' for s in app.selectbox)
    app.text_input(key='extra_search').set_value('Feridas').run()
    assert not app.exception
    assert any('Feridas' in str(m.value) for m in app.markdown)


def test_calendar_and_confidence_registration_are_visible(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    open_view(app,adaptive='Calendário')
    assert not app.exception
    assert any('previsão' in c.value.lower() for c in app.caption)
    open_view(app,adaptive='Registrar resultados')
    assert not app.exception
    assert app.number_input(key='study_confident').value is None


def test_explicit_shortcut_changes_an_already_mounted_picker():
    app=AppTest.from_string("""
import streamlit as st
from osler.topic_picker_ui import pick_topic
from osler.adaptive_ui import _go_record
topics=[{'topic_id':'a','path':['Área','A']},{'topic_id':'b','path':['Área','B']}]
chosen=pick_topic(topics,'record',st.session_state.get('adaptive_topic'))
st.write('RESULT:'+chosen['topic_id'])
st.button('Escolher B',on_click=_go_record,args=('b',10))
""").run()
    next(b for b in app.button if b.label=='Escolher B').click().run()
    assert not app.exception
    assert any(m.value=='RESULT:b' for m in app.markdown)
