from ui_actions import confirm_action
from conftest import open_view
from datetime import date
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment
from osler.exam_goals import ExamGoals
from osler.study_storage import StudyStore


def test_exam_form_three_targets_edit_principal_void_and_sources(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Ajustes')
    app.radio(key='study_settings_section').set_value('Minhas provas').run()
    assert not app.exception
    app.text_input(key='exam_field_institution').set_value('Prova de teste')
    app.number_input(key='exam_field_cutoff').set_value(75.)
    confirm_action(app.button(key='save_exam').click().run())
    assert app.error and not ExamGoals(repo).active()
    for name,day in [('A',date(2027,10,1)),('B',date(2027,9,1)),('C',date(2027,11,1))]:
        app.text_input(key='exam_field_institution').set_value(name)
        app.date_input(key='exam_field_date').set_value(day)
        app.number_input(key='exam_field_cutoff').set_value(75.)
        app.text_input(key='exam_field_source').set_value('Fonte sintética de teste')
        confirm_action(app.button(key='save_exam').click().run())
        assert not app.exception and not app.error
    exams=ExamGoals(repo)
    assert len(exams.active())==3
    first=next(e for e in exams.active() if e['target']['institution']=='A')
    app.selectbox(key='exam_primary').set_value(first['target_id'])
    confirm_action(app.button(key='save_exam_primary').click().run())
    assert not app.exception and StudyStore(repo).profile()['profile']['exam_date']=='2027-10-01'
    app.selectbox(key='exam_selected').set_value(first['target_id']).run()
    app.button(key='edit_exam').click().run()
    app.number_input(key='exam_field_cutoff').set_value(80.)
    confirm_action(app.button(key='save_exam').click().run())
    assert not app.exception
    assert next(e for e in exams.active() if e['target_id']==first['target_id'])['version']==2
    app.selectbox(key='exam_selected').set_value(first['target_id']).run()
    confirm_action(app.button(key='void_exam').click().run())
    assert not app.exception and len(exams.active())==2
    assert StudyStore(repo).profile()['profile']['exam_date']=='2027-09-01'
    assert len(exams.events())==5


def test_empty_exam_date_shows_recoverable_error(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Ajustes')
    app.radio(key='study_settings_section').set_value('Minhas provas').run()
    app.text_input(key='exam_field_institution').set_value('Prova de teste')
    app.number_input(key='exam_field_cutoff').set_value(75.)
    app.text_input(key='exam_field_source').set_value('Documento de teste')
    app.date_input(key='exam_field_date').set_value(None)
    confirm_action(app.button(key='save_exam').click().run())
    assert not app.exception
    assert app.error and not ExamGoals(repo).active()


def test_principal_flow_has_no_legacy_and_no_new_required_registration_field(tmp_path,monkeypatch,project_root,sample_pdf):
    setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    for destination in ['Plano de questões','Diminuir revisões']:
        open_view(app,main=destination)
        assert not app.exception
        assert not any('lotes e avaliações detalhadas' in e.label.lower() for e in app.expander)
        assert not any(b.key and b.key.startswith('reduce_') for b in app.button)
    open_view(app,main='Plano de questões')
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    assert not app.exception and app.number_input(key='study_confident').value is None
    assert not any(n.key and n.key.startswith('exam_field_') for n in app.number_input)
