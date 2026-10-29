from conftest import open_view
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService


def test_evolution_projection_does_not_write_or_change_routine(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo); before=service.agenda.token(); profile=service.store.profile()
    result=service.evolution_context()
    assert result['end']<=profile['profile']['exam_date']
    assert result['snapshot']['total_topics']>0
    assert result['performance']['questions']==0
    assert service.evolution_context(questions=30)['scenario_questions']==30
    assert service.store.profile()==profile and service.agenda.token()==before
    assert not service.store.active('2026-10-15')


def test_evolution_spacing_assumption_is_explicit_and_read_only(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo); token=service.agenda.token(); profile=service.store.profile()
    advancing=service.evolution_context()
    current=service.evolution_context(spacing_scenario='unchanged')
    assert advancing['spacing_scenario']=='progressive'
    assert current['spacing_scenario']=='unchanged'
    assert advancing['assumptions']['max_contact_gap']==profile['profile']['max_contact_gap']
    assert service.agenda.token()==token and service.store.profile()==profile
    assert not service.store.active('2026-10-15')


def test_switching_spacing_scenario_recalculates_but_period_uses_cache(tmp_path,sample_pdf,monkeypatch,project_root):
    setup_assessment(tmp_path,sample_pdf); calls=[]
    original=AdaptiveService.evolution_context
    def tracked(self,*args,**kwargs):
        calls.append(kwargs.get('spacing_scenario','progressive'))
        return original(self,*args,**kwargs)
    monkeypatch.setattr(AdaptiveService,'evolution_context',tracked)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=120)
    app.session_state['adaptive_view']='Evolução'; app.run()
    app.segmented_control(key='evolution_section').set_value('Cenários').run()
    assert app.radio(key='evolution_spacing').value=='progressive'
    assert len(calls)==1
    app.radio(key='evolution_period').set_value('3 meses').run()
    assert len(calls)==1
    app.radio(key='evolution_spacing').set_value('unchanged').run()
    assert not app.exception and calls==['progressive','unchanged']
    assert any('intervalos atuais' in c.value for c in app.caption)


def test_evolution_navigation_dates_charts_and_empty_performance(tmp_path,sample_pdf,monkeypatch,project_root):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=120).run()
    open_view(app,adaptive='Evolução')
    app.segmented_control(key='evolution_section').set_value('Cenários').run()
    assert not app.exception
    assert app.radio(key='evolution_period').value=='1 mês'
    assert any('previsto' in e.value.lower() for e in app.caption)
    assert any('evo-journey' in e.value for e in app.get('html'))
    app.radio(key='evolution_chart').set_value('Rendimento').run()
    assert not app.exception and any('blocos' in e.value.lower() for e in app.info)
    app.radio(key='evolution_period').set_value('3 meses').run()
    assert not app.exception
    app.radio(key='evolution_period').set_value('Escolher data').run()
    assert app.date_input(key='evolution_date')
    assert not AdaptiveService(repo).store.active('2026-10-15')


def test_past_exam_and_far_future_start_do_not_generate_fake_progress(tmp_path,sample_pdf):
    from dataclasses import replace
    from osler.study_models import AdaptiveProfile
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    first=service.store.save_profile(AdaptiveProfile(exam_date='2026-10-10'),0)
    context=service.evolution_context()
    assert context['end']=='2026-10-15'
    assert context['snapshot']['points'][-1]['future_attempts']==0
    service.store.save_profile(AdaptiveProfile(exam_date='2031-11-30',start_date='2030-10-22'),first)
    context=service.evolution_context()
    assert not context['exam_in_horizon']
    assert len(context['snapshot']['points'])<=549
    assert context['snapshot']['points'][-1]['future_attempts']==0


def test_evolution_custom_date_is_clamped_after_exam_setting_changes(tmp_path,sample_pdf,monkeypatch,project_root):
    from dataclasses import replace
    from osler.study_models import AdaptiveProfile
    from datetime import date
    repo,*_=setup_assessment(tmp_path,sample_pdf); service=AdaptiveService(repo)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=120)
    app.session_state['adaptive_view']='Evolução'; app.run()
    app.segmented_control(key='evolution_section').set_value('Cenários').run()
    app.radio(key='evolution_period').set_value('Escolher data').run()
    app.date_input(key='evolution_date').set_value(date(2027,11,30)).run()
    service.store.save_profile(AdaptiveProfile(exam_date='2026-10-20'),0)
    app.run()
    assert not app.exception and not app.error
    assert app.date_input(key='evolution_date').value<=date(2026,10,20)


def test_performance_curve_renders_a_supported_conditional_trend():
    from datetime import date,timedelta
    from test_evolution_performance import measured
    from osler.evolution_performance import performance_history
    events=[]
    for i in range(8):
        e=measured((date(2026,8,25)+timedelta(days=i*7)).isoformat(),100,40+5*i,confident=35+5*i)
        e['entry']['path']=['Área',str(i%3)]; events.append(e)
    context={'as_of':'2026-10-15','performance':performance_history(events,'2026-10-15'),'snapshot':{}}
    app=AppTest.from_string('from osler.study_evolution_ui import _performance\n_performance('+repr(context)+',"2026-10-29")').run()
    assert not app.exception
    assert app.get('vega_lite_chart')
    assert any('Tendência exploratória' in e.value for e in app.markdown)
