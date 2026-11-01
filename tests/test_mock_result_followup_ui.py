from streamlit.testing.v1 import AppTest
from osler.mock_exams import MockExams
from test_mock_schedule import configured
from test_mock_exams_ui import APP


def test_result_immediately_requests_errors_and_reuses_correction_annotations(tmp_path,sample_pdf,monkeypatch):
    service,topic=configured(tmp_path,sample_pdf)
    monkeypatch.setenv('MOCK_TEST_ROOT',str(service.repository.root))
    app=AppTest.from_string(APP,default_timeout=60).run()
    app.number_input(key='mock_field_questions').set_value(20)
    app.number_input(key='mock_field_correct').set_value(11)
    app.button(key='mock_save').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception
    record=MockExams(service.repository).active()[0];eid=record['exam_key']
    assert app.session_state['mock_error_prompt']['exam_key']==eid
    app.text_input(key='mock_error_picker_'+eid+'_search').set_value('Feridas').run()
    app.number_input(key='mock_error_count_'+eid).set_value(3)
    app.button(key='mock_error_add').click().run()
    assert not app.exception
    app.button(key='mock_error_save').click().run()
    assert not app.exception and not app.error
    assert service.mock_errors(eid)['errors']==[{'topic_id':topic.qbank.topic_id,'path':topic.qbank.path,'errors':3}]
    assert app.session_state['mock_sections']=='Correção'
    assert len(MockExams(service.repository).active())==1
    assert not service.store.events() and service.correction_schedule(eid) is None


def test_area_result_requests_topics_and_allows_postponing_without_losing_result(tmp_path,sample_pdf,monkeypatch):
    service,_=configured(tmp_path,sample_pdf)
    service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-20',1,20,['FMUSP']))
    monkeypatch.setenv('MOCK_TEST_ROOT',str(service.repository.root))
    app=AppTest.from_string(APP,default_timeout=60).run()
    app.number_input(key='area_result_correct').set_value(11)
    app.button(key='area_result_save').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and app.button(key='mock_error_later')
    app.button(key='mock_error_later').click().run()
    rows=MockExams(service.repository).active()
    assert not app.exception and len(rows)==1 and rows[0]['exam']['correct']==11
    assert not service.mock_errors(rows[0]['exam_key'])['errors']


def test_perfect_result_does_not_request_errors(tmp_path,sample_pdf,monkeypatch):
    service,_=configured(tmp_path,sample_pdf)
    monkeypatch.setenv('MOCK_TEST_ROOT',str(service.repository.root))
    app=AppTest.from_string(APP,default_timeout=60).run()
    app.number_input(key='mock_field_questions').set_value(20)
    app.number_input(key='mock_field_correct').set_value(20)
    app.button(key='mock_save').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and not any(b.key=='mock_error_later' for b in app.button)
