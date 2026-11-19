from streamlit.testing.v1 import AppTest
from osler.mock_exams import MockExams
from test_mock_schedule import configured

APP="""
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.mock_workflow_ui import render_mock_workflow
render_mock_workflow(AdaptiveService(Repository(os.environ['MOCK_FLOW_ROOT'])),'flow')
"""


def fill(app,correct=70):
    app.text_input(key='flow_form_name_completo').set_value('FMUSP 2025')
    app.number_input(key='flow_form_total_completo').set_value(100)
    app.number_input(key='flow_form_correct_completo').set_value(correct)
    next(b for b in app.button if b.label=='Salvar resultado e informar temas errados').click().run()
    assert not app.exception


def test_direct_result_then_topics_and_resume_without_schedule(tmp_path,sample_pdf,monkeypatch):
    service,topic=configured(tmp_path,sample_pdf)
    monkeypatch.setenv('MOCK_FLOW_ROOT',str(service.repository.root))
    app=AppTest.from_string(APP,default_timeout=60).run()
    fill(app)
    rows=MockExams(service.repository).active();assert len(rows)==1
    key=rows[0]['exam_key']
    assert rows[0]['exam']['name']=='FMUSP 2025'
    assert app.selectbox(key='flow_selected').value==key
    assert any('Temas errados' in x.value for x in app.subheader)
    app.text_input(key='flow_topic_'+key+'_search').set_value('Feridas').run()
    app.number_input(key='flow_count_'+key).set_value(3)
    app.button(key='flow_add').click().run()
    app.button(key='flow_save_errors').click().run()
    assert not app.exception and not app.error
    assert service.mock_errors(key)['errors'][0]['errors']==3
    assert app.button(key='flow_distribute')
    app.run()
    assert len(MockExams(service.repository).active())==1
    assert not service.store.events() and not service.correction_schedule(key)


def test_invalid_counts_keep_form_and_perfect_result_skips_errors(tmp_path,sample_pdf,monkeypatch):
    service,_=configured(tmp_path,sample_pdf)
    monkeypatch.setenv('MOCK_FLOW_ROOT',str(service.repository.root))
    app=AppTest.from_string(APP,default_timeout=60).run()
    fill(app,correct=101)
    assert app.error and not MockExams(service.repository).active()
    fill(app,correct=100)
    assert any('Todos os acertos' in x.value for x in app.success)
    assert len(MockExams(service.repository).active())==1


def test_home_renders_registration_even_without_schedule(tmp_path,sample_pdf,monkeypatch):
    service,_=configured(tmp_path,sample_pdf)
    monkeypatch.setenv('MOCK_FLOW_ROOT',str(service.repository.root))
    code=APP.replace('from osler.mock_workflow_ui import render_mock_workflow','from osler.bento_day_ui import render_today').replace("render_mock_workflow(AdaptiveService(Repository(os.environ['MOCK_FLOW_ROOT'])),'flow')", "render_today(AdaptiveService(Repository(os.environ['MOCK_FLOW_ROOT'])),lambda *a:None,lambda *a:None)")
    app=AppTest.from_string(code,default_timeout=60).run()
    assert not app.exception
    assert app.text_input(key='today_mock_flow_form_name_completo')
