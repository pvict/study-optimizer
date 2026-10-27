from streamlit.testing.v1 import AppTest
from dataclasses import replace
import pytest
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry,AdaptiveProfile
from test_assessments import setup_assessment


def test_single_navigation_and_empty_import_action(tmp_path,monkeypatch,project_root):
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert not any(r.key in {'main_view','adaptive_view'} for r in app.radio)
    assert app.title[0].value=='Olá'
    app.button(key='nav_calendar').click().run()
    assert not app.exception and app.session_state['adaptive_view']=='Calendário'
    app.button(key='nav_today').click().run()
    app.button(key='bento_import').click().run()
    assert not app.exception and app.session_state['main_view']=='Ferramentas'
    app.button(key='nav_register').click().run()
    assert app.session_state['adaptive_view']=='Registrar resultados'


def test_hero_registration_and_optional_pause_keep_real_records(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception and not any(b.key=='bento_pause_start' for b in app.button)
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    app.number_input(key='study_n').set_value(20);app.number_input(key='study_correct').set_value(17)
    next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run()
    app.button(key='study_back_to_plan').click().run()
    assert not app.exception
    app.button(key='bento_pause_start').click().run()
    deadline=app.session_state['bento_pause_until']
    app.run();assert app.session_state['bento_pause_until']==deadline
    app.button(key='bento_pause_dismiss').click().run()
    assert not app.exception and not any(b.key=='bento_pause_start' for b in app.button)
    assert len(AdaptiveService(repo).store.active('2026-10-15'))==1


@pytest.mark.parametrize('state,label',[
    ('rest','Hoje é descanso'),('complete','Meta registrada'),
    ('not_started','Tudo pronto para começar'),('mock','Hoje é dia de simulado')])
def test_today_states_do_not_change_study_records(tmp_path,monkeypatch,project_root,sample_pdf,state,label):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo);day='2026-10-15'
    if state=='rest':service.configure_day(day,60,'descanso',0)
    elif state=='complete':
        topic=service.catalog(day)[0][0]
        service.save_entry(StudyEntry(topic['path'],day,60,correct=50),session_id='completed')
    elif state=='not_started':
        record=service.store.profile()
        service.store.save_profile(replace(AdaptiveProfile(**record['configured_profile']),start_date='2026-10-22'),record['id'])
    else:service.apply_mock_schedule(service.preview_mock_schedule(day,7))
    before=service.store.events()
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception and label in [h.value for h in app.subheader]
    assert service.store.events()==before
    if state in {'rest','mock','not_started'}:
        assert any('questões registradas · sem meta de blocos hoje' in h.value for h in app.get('html'))
    if state=='complete':
        app.button(key='bento_advance').click().run()
        assert next(e for e in app.expander if e.label=='Adiantar revisões').proto.expanded
    if state=='rest':assert not any(b.key and b.key.startswith('study_') for b in app.button)


def test_today_overview_failure_keeps_navigation_and_recovery_message(tmp_path,monkeypatch,project_root):
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    def fail(*args):raise ValueError('Não foi possível carregar o plano de teste.')
    monkeypatch.setattr(AdaptiveService,'overview',fail)
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert any('Não foi possível carregar' in e.value for e in app.error)
    assert app.button(key='nav_files')


def test_hero_linked_review_highlights_only_first_action_and_preserves_link():
    app=AppTest.from_string('''
import streamlit as st
from osler.review_parts_ui import render_review_parts
item={'questions':12,'topic_id':'theme','pending_reviews':[
    {'session_id':'original','due_date':'2026-10-15','questions':5}]}
def review(lot):st.session_state['selected_lot']=lot
render_review_parts(item,'2026-10-15',lambda *args:None,review,'study',primary=True)
''',default_timeout=30).run()
    assert not app.exception
    assert [b.proto.type for b in app.button]==['primary','secondary']
    app.button(key='study_lot_original').click().run()
    assert app.session_state['selected_lot']['session_id']=='original'
    assert app.session_state['selected_lot']['questions']==5
