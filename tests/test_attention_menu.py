from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment


def test_attention_has_own_sidebar_page_and_today_is_unchanged(tmp_path,sample_pdf,project_root,monkeypatch):
 setup_assessment(tmp_path,sample_pdf)
 monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
 app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
 assert not app.exception
 assert not any(h.value=='Temas que merecem atenção' for h in app.subheader)
 assert not any('carga e os próximos ajustes' in h.value for h in app.subheader)
 app.button(key='nav_attention').click().run()
 assert not app.exception and app.title[0].value=='Temas em atenção'
 assert app.get('segmented_control') and app.text_input(key='attention_search')
 app.button(key='nav_today').click().run()
 assert not app.exception and app.title[0].value=='Olá'
 assert not any(w.key=='attention_search' for w in app.text_input)
