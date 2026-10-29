from datetime import date
from streamlit.testing.v1 import AppTest

from test_mock_schedule import configured
from test_mock_exams_ui import APP
from osler.mock_exams import MockExams,MockExam


def test_native_area_flow_preview_apply_register_and_correction_later(tmp_path,sample_pdf,monkeypatch):
    service,topic=configured(tmp_path,sample_pdf)
    monkeypatch.setenv('MOCK_TEST_ROOT',str(service.repository.root))
    app=AppTest.from_string(APP,default_timeout=40).run()
    assert not app.exception
    app.date_input(key='area_first').set_value(date(2026,10,15))
    app.date_input(key='area_end').set_value(date(2026,11,26))
    app.text_area(key='area_institutions').set_value('UNESP\nSUS-SP')
    app.button(key='area_preview').click().run()
    assert not app.exception and not app.error
    assert service.area_schedule() is None
    app.button(key='area_apply').click().run()
    assert not app.exception and service.area_schedule()
    app.number_input(key='area_result_correct').set_value(15)
    app.button(key='area_result_save').click().run()
    assert not app.exception and not app.error
    assert len(MockExams(service.repository).active())==1
    assert app.selectbox(key='correction_exam').value==MockExams(service.repository).active()[0]['exam_key']
    app.text_input(key='correction_picker_'+app.selectbox(key='correction_exam').value+'_search').set_value('Cicatrização').run()
    app.number_input(key='correction_error_count').set_value(3)
    app.button(key='correction_add_topic').click().run()
    app.button(key='correction_save_errors').click().run()
    assert not app.exception and not app.error
    record=MockExams(service.repository).active()[0]
    assert service.mock_errors(record['exam_key'])['errors'][0]['errors']==3
    app.button(key='correction_distribution_preview').click().run()
    assert not app.exception and not app.error
    app.button(key='correction_apply').click().run()
    assert not app.exception and service.correction_schedule(record['exam_key'])


def test_calendar_supports_new_agenda_scopes(tmp_path,sample_pdf,monkeypatch):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_area_schedule(service.preview_area_schedule('2026-10-15','2026-11-26',1,20,['UNESP']))
    row=MockExams(service.repository).save(MockExam('2026-10-15',20,15,
        topics=[{'path':topic.qbank.path,'questions':20,'correct':15}]))
    service.apply_mock_correction(service.preview_mock_correction(row['exam_key'],'2026-10-16',40))
    monkeypatch.setenv('MOCK_TEST_ROOT',str(service.repository.root))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_calendar_ui import render_calendar
render_calendar(AdaptiveService(Repository(os.environ['MOCK_TEST_ROOT'])),lambda *args:None)
''',default_timeout=40).run()
    assert not app.exception


def test_preview_allows_train_and_topic_date_edits_without_saving(tmp_path,sample_pdf,monkeypatch):
    service,topic=configured(tmp_path,sample_pdf)
    service.apply_mock_schedule(service.preview_mock_schedule('2026-10-18',7))
    monkeypatch.setenv('MOCK_TEST_ROOT',str(service.repository.root))
    app=AppTest.from_string(APP,default_timeout=40).run()
    app.date_input(key='area_first').set_value(date(2026,10,18))
    app.date_input(key='area_end').set_value(date(2026,11,26))
    app.button(key='area_preview').click().run()
    assert not app.exception and not app.error
    preview=app.session_state['area_apply_preview']
    assert preview['occurrences'][0]['status']=='moved'
    train=app.selectbox(key='area_preview_train').value
    app.date_input(key='area_preview_date_'+train).set_value(date(2026,10,20))
    app.button(key='area_preview_move').click().run()
    assert not app.exception and not app.error
    topic_id=app.selectbox(key='area_preview_topic').value
    app.date_input(key='area_preview_topic_date_'+topic_id).set_value(date(2026,10,23))
    app.button(key='area_preview_topic_move').click().run()
    assert not app.exception and not app.error
    assert service.area_schedule() is None
    assert app.session_state['area_apply_preview']['rows'][0]['date']=='2026-10-23'
    app.button(key='area_apply').click().run()
    assert not app.exception and not app.error
    assert service.area_schedule()['request']['topic_dates'][topic_id]=='2026-10-23'
