from ui_actions import confirm_action
"""Contratos de tarefas e fontes da fase5, somente repositórios descartáveis."""
import pytest
from streamlit.testing.v1 import AppTest
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.practical_reduction import PracticalReductionService
from conftest import open_view
from test_assessments import setup_assessment


@pytest.mark.parametrize('value',[None,0,146])
def test_reduction_summary_preserves_unknown_zero_and_source(tmp_path,sample_pdf,value):
    from osler.practical_reduction_ui import reduction_summary
    from osler.planning_service import PlanningService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    view=PracticalReductionService(repo).current_overview('2026-10-15')
    source=view['sources']['reports']['flashcards']
    report=repo.get_report(source['sha256']);report.summary['estudados']=value
    # Leitura da fonte exata; não aproximar pelo somatório de pais e filhos.
    original=repo.get_report
    repo.get_report=lambda sha:report if sha==source['sha256'] else original(sha)
    result=reduction_summary(repo,view,'2026-10-15')
    assert result['studied']==value
    assert result['studied_date']==source['report_date']
    assert result['review_cards'] is None
    assert result['reviews_per_day'] is None
    assert not PlanningService(repo).measurements()


def test_reduction_summary_without_report_never_implies_zero(tmp_path):
    from osler.practical_reduction_ui import reduction_summary
    repo=Repository(tmp_path)
    view={'sources':{'reports':{'flashcards':None}},'suggestions':[]}
    result=reduction_summary(repo,view,'2026-10-15')
    assert result['studied'] is None and result['review_cards'] is None


def test_optional_name_survives_navigation_without_changing_profile(tmp_path,monkeypatch,project_root):
    repo=Repository(tmp_path);service=AdaptiveService(repo);before=service.store.profile()
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Ajustes')
    app.text_input(key='settings_display_name').set_value('  Paulo  ').run()
    open_view(app,adaptive='Meu dia')
    assert not app.exception
    assert app.title[0].value=='Olá, Paulo'
    assert service.store.profile()==before
    open_view(app,adaptive='Ajustes')
    assert app.text_input(key='settings_display_name').value=='Paulo'
    app.text_input(key='settings_display_name').set_value('**Paulo**').run()
    open_view(app,adaptive='Meu dia')
    assert app.title[0].value==r'Olá, \*\*Paulo\*\*'
    open_view(app,adaptive='Ajustes')
    app.text_input(key='settings_display_name').set_value('').run()
    open_view(app,adaptive='Meu dia')
    assert app.title[0].value=='Olá'


def test_files_entry_and_backup_keep_library_accessible(tmp_path,monkeypatch,project_root):
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    app.button(key='nav_files').click().run()
    assert not app.exception
    assert any(t.label=='Biblioteca' for t in app.tabs)
    assert any(e.label.startswith('Avançado') and not e.proto.expanded for e in app.expander)
    assert any(b.key=='open_backup' for b in app.button)
    app.button(key='open_backup').click().run()
    assert not app.exception
    assert app.session_state['advanced_view']=='Backup e restauração'
    app.button(key='files_library').click().run()
    assert app.session_state['advanced_view']=='Dados e classificação'
    assert any(t.label=='Biblioteca' for t in app.tabs)


def test_institutions_form_preserves_legacy_time_and_study_capacity(tmp_path,monkeypatch,project_root):
    from osler.guide_service import GuideService
    repo=Repository(tmp_path);service=AdaptiveService(repo)
    guide=GuideService(repo);before=guide.settings()['settings'];profile=service.store.profile()
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    open_view(app,adaptive='Ajustes')
    app.radio(key='study_settings_section').set_value('Instituições e incidências').run()
    assert not app.exception and not app.select_slider
    app.text_area(key='guide_institutions').set_value('Instituição A\nInstituição B')
    confirm_action(next(b for b in app.button if b.label=='Salvar instituições').click().run())
    after=guide.settings()['settings']
    assert after['institutions']==['Instituição A','Instituição B']
    assert {k:v for k,v in after.items() if k!='institutions'}=={k:v for k,v in before.items() if k!='institutions'}
    assert service.store.profile()['configured_profile']==profile['configured_profile']


def test_review_average_uses_latest_reported_period_without_future_measurement(tmp_path):
    from osler.practical_reduction_ui import reduction_summary
    from osler.planning_service import PlanningService
    from osler.planning import Measurement
    repo=Repository(tmp_path);planning=PlanningService(repo)
    planning.save_measurement(Measurement('revisoes_periodo',650,'2026-10-15','Consulta manual',2,True))
    planning.save_measurement(Measurement('revisoes_periodo',900,'2026-10-17','Consulta futura',1))
    view={'sources':{'reports':{'flashcards':None}},'all_suggestions':[{'studied_cards':10},{'studied_cards':20}]}
    summary=reduction_summary(repo,view,'2026-10-16')
    assert summary['reviews_per_day']==325 and summary['workload']['approximate'] is True
    assert summary['review_cards']==30 and summary['studied'] is None
