from conftest import open_view
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService
import pytest


def test_comparison_is_read_only_and_activation_is_one_versioned_action(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    before=service.store.profile()
    token=service.agenda.token()
    result=service.workload_comparison('2026-10-15',14)
    assert result['fixed']['planned_questions']>=0
    assert result['adaptive']['new_topics']>=0
    assert service.agenda.token()==token
    service.configure_workload('adaptive',before['id'])
    after=service.store.profile()
    assert after['profile']['workload_mode']=='adaptive'
    assert {k:v for k,v in after['profile'].items() if k!='workload_mode'}=={k:v for k,v in before['profile'].items() if k!='workload_mode'}
    with pytest.raises(ValueError): service.configure_workload('fixed',before['id'])
    assert not service.store.active('2026-10-15')


def test_calendar_global_summary_activation_and_fixed_mode_control(tmp_path,sample_pdf,monkeypatch,project_root):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=90).run()
    open_view(app,adaptive='Calendário')
    assert not app.exception
    assert any('Equilíbrio dos próximos' in e.value for e in app.subheader)
    app.button(key='activate_capacity').click().run()
    assert not app.exception
    assert AdaptiveService(repo).store.profile()['profile']['workload_mode']=='adaptive'
    assert any('Ajuste automático ativo' in e.value for e in app.caption)
    open_view(app,adaptive='Ajustes')
    assert app.radio(key='settings_workload_mode').value=='adaptive'


def test_future_review_is_not_counted_as_a_new_theme_in_selected_window(tmp_path,sample_pdf,monkeypatch):
    from osler.adaptive_planning import topic_states
    from osler.study_models import AdaptiveProfile
    from test_initial_review_policy import imported
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    p=AdaptiveProfile(max_questions=40,max_topics=2,new_share=.5)
    states=topic_states([imported('N',n=0,contact=None)],[],[],{},'2026-10-15',p)
    view={'profile':p.to_dict(),'planning_states':states,'sessions':[],
          'agenda':{'rows':[],'overrides':{},'policies':[]},'profile_id':0}
    monkeypatch.setattr(service,'overview',lambda day:view)
    result=service.workload_comparison('2026-10-22',1)
    assert result['fixed']['new_questions']==result['adaptive']['new_questions']==0
    assert result['fixed']['new_topics']==result['adaptive']['new_topics']==0


def test_lot_block_opens_a_linked_review_registration(tmp_path,sample_pdf,monkeypatch,project_root):
    from osler.study_models import StudyEntry,AdaptiveProfile
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    t=next(t for t in service.catalog('2026-10-15')[0] if t['total']>=20)
    service.store.save_profile(AdaptiveProfile(max_questions=60,new_share=0,workload_mode='adaptive'),0)
    service.save_entry(StudyEntry(t['path'],'2026-10-01',20,20,confident_correct=18),'first')
    service.save_entry(StudyEntry(t['path'],'2026-10-08',20,20,confident_correct=20),'good')
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=90).run()
    assert not app.exception
    app.button(key='study_lot_first').click().run()
    assert not app.exception
    assert app.session_state['study_review_of']=='first'
    assert app.number_input(key='study_n').value==2
