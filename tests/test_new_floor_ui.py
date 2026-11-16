from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from osler.study_models import AdaptiveProfile


def floor_service(tmp_path,monkeypatch):
    service=AdaptiveService(Repository(tmp_path))
    topics=[{'topic_id':n,'path':['Area',n],'total':100,'answered_pdf':40 if n.startswith('R') else 0,
             'pdf_accuracy':{'value':80 if n.startswith('R') else None,'operator':'=','raw':'-'},
             'report_date':'2026-10-14','studied_cards':0,'is_leaf':True} for n in ['R1','R2','N']]
    monkeypatch.setattr(service,'catalog',lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None}))
    service.store.save_profile(AdaptiveProfile(max_questions=60,max_topics=2,new_share=.5,
                                              minimum_new_share=.2,min_block=10,workload_mode='adaptive'),0)
    rows=[{'topic_id':n,'path':['Area',n],'date':'2026-10-15','original_due':'2026-10-01',
           'questions':20,'new_topic':False,'manual_date':True} for n in ['R1','R2']]
    service.agenda.append({'kind':'reschedule.apply','mode':'custom','created_day':'2026-10-15',
                          'cutoff':0,'selected':['R1','R2'],'rows':rows},service.agenda.token())
    return service


def test_floor_notice_shows_counts_and_exact_settings_without_writing(tmp_path,monkeypatch):
    service=floor_service(tmp_path,monkeypatch)
    before=(service.store.events(),service.agenda.records(),service.store.profile())
    app=AppTest.from_string('''
import streamlit as st
from osler.new_floor_ui import render_new_floor_notice
service=st.session_state.service
render_new_floor_notice(service,service.overview('2026-10-15'))
''',default_timeout=60)
    app.session_state['service']=service
    app.session_state['new_floor_details']=True
    app.run()
    assert not app.exception
    assert any('12 questões' in e.label for e in app.expander)
    text='\n'.join(m.value for m in app.markdown)
    assert 'Mínimo de hoje: **12**' in text
    assert 'No plano: **0**' in text
    assert 'Máximo de temas por dia: **2 → 3**' in text
    assert (service.store.events(),service.agenda.records(),service.store.profile())==before


def test_service_diagnostic_options_reproduce_in_the_real_overview(tmp_path,monkeypatch):
    from dataclasses import replace
    service=floor_service(tmp_path,monkeypatch)
    view=service.overview('2026-10-15',diagnose_new_floor=True)
    options=view['plan']['capacity']['new_floor']['options']
    assert options
    for option in options:
        p=replace(AdaptiveProfile(**view['profile']),max_topics=option['max_topics'],new_share=option['control_new_share'])
        trial=service.overview('2026-10-15',_profile_override=p.to_dict())['plan']
        assert trial['capacity']['new_floor']['missing']==0
        assert trial['target_questions']==view['plan']['target_questions']
        assert {r['topic_id']:r['questions'] for r in trial['items'] if r.get('rescheduled')}=={'R1':20,'R2':20}


def test_partial_completion_is_respected_by_service_counts_and_suggestions(tmp_path,monkeypatch):
    from dataclasses import replace
    from osler.study_models import StudyEntry
    from osler.planner_completion import complete_partial_block
    service=floor_service(tmp_path,monkeypatch)
    record=service.store.profile()
    service.store.save_profile(replace(AdaptiveProfile(**record['profile']),max_topics=3),record['id'])
    service.agenda.append({'kind':'reschedule.apply','mode':'custom','created_day':'2026-10-15',
        'cutoff':0,'selected':['N'],'rows':[{'topic_id':'N','path':['Area','N'],'date':'2026-10-15',
        'original_due':'2026-10-01','questions':20,'new_topic':True,'manual_date':True}]},service.agenda.token())
    service.remember_day(service.overview('2026-10-15'))
    service.save_entry(StudyEntry(['Area','N'],'2026-10-15',5,4,confident_correct=4),'actual-new')
    complete_partial_block(service,'2026-10-15','N',service.agenda.token())
    before=(service.store.events(),service.agenda.records())
    plan=service.overview('2026-10-15',diagnose_new_floor=True)['plan']
    assert 'N' not in {r['topic_id'] for r in plan['items']}
    assert plan['capacity']['new_floor']['done']==5
    assert plan['capacity']['new_floor']['planned']==0
    assert plan['capacity']['new_floor']['missing']==7
    assert plan['capacity']['new_floor']['options']==[]
    assert (service.store.events(),service.agenda.records())==before
