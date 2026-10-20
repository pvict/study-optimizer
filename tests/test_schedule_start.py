from dataclasses import replace
import pytest
from osler.study_models import AdaptiveProfile
from osler.study_calendar import forecast_calendar
from osler.study_replanning import collect_backlog
from osler.adaptive_planning import topic_states
from test_adaptive_planning import topic


def test_start_date_compatible_validated_and_pre_start_plans_have_no_work(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    old=AdaptiveProfile(**service.store.profile()['profile'])
    assert old.start_date is None
    with pytest.raises(ValueError): replace(old,start_date='2026-02-30').validate()
    service.store.save_profile(replace(old,start_date='2026-10-22'),0)
    for day in ['2026-10-20','2026-10-21']:
        view=service.overview(day)
        assert view['plan']['not_started'] and not view['plan']['items'] and view['plan']['questions']==0
        assert view['plan']['target_questions']==0
        service.agenda.remember(view)
    assert not service.agenda.daily_plans()
    assert service.overview('2026-10-22')['plan']['items']


def test_calendar_and_backlog_do_not_charge_days_before_start():
    p=AdaptiveProfile(start_date='2026-10-22')
    t={**topic(answered=30),'planner_snapshot':{'observed_date':'2026-10-15','unique_questions':30,
        'available_questions':100,'confident_accuracy_pct':50.,'pending_reviews':None,'last_contact':'2026-09-01'}}
    states=topic_states([t],[],[],{},'2026-10-20',p)
    days=forecast_calendar(states,p,'2026-10-20',4,[],{})
    assert [d['date'] for d in days]==['2026-10-20','2026-10-21','2026-10-22','2026-10-23']
    assert all(d['not_started'] and not d['items'] and not d['backlog_items'] for d in days[:2])
    assert days[2]['items']
    assert states[0]['last_contact']=='2026-09-01'
    assert states[0]['next_review']=='2026-10-22'
    from osler.topic_trajectory import topic_trajectory
    assert topic_trajectory(states[0],p,'2026-10-20')['steps'][0]['date']=='2026-10-22'
    saved=[{'plan':{'date':'2026-10-20','items':[{'path':t['path'],'questions':20}]}}]
    assert collect_backlog(states,[],saved,'2026-10-21',start_date=p.start_date)==[]
    backlog=collect_backlog(states,[],saved,'2026-10-23',start_date=p.start_date)
    assert backlog==[]  # histórico importado não cria obrigação não agendada
    states[0]['review_committed']=True
    backlog=collect_backlog(states,[],saved,'2026-10-23',start_date=p.start_date)
    assert backlog[0]['original_due']=='2026-10-22' and backlog[0]['days_late']==1
    assert backlog[0]['missed_questions']==0


def test_ui_shows_start_without_study_debt_and_calendar_opens_on_start(tmp_path,monkeypatch,project_root,sample_pdf):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    from streamlit.testing.v1 import AppTest
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.store.save_profile(AdaptiveProfile(start_date='2026-10-22'),0)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert any('22/10/2026' in x.value for x in app.info)
    assert not any('Descanse hoje' in x.value for x in app.info)
    assert not any(b.label=='Registrar este bloco' for b in app.button)
    assert service.agenda.daily_plans()==[]
    app.radio(key='adaptive_view').set_value('Calendário').run()
    assert not app.exception
    assert app.date_input(key='calendar_reference').value.isoformat()=='2026-10-22'
    assert service.replanning('2026-10-21')['backlog']==[]
    app.radio(key='adaptive_view').set_value('Ajustes').run()
    assert app.date_input(key='settings_start_date').value.isoformat()=='2026-10-22'


def test_old_recovery_dates_are_clamped_in_operational_view_only(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.store.save_profile(AdaptiveProfile(start_date='2026-10-22'),0)
    t=next(t for t in service.catalog('2026-10-22')[0] if t['total']>=10)
    agenda={'rows':[{'topic_id':t['topic_id'],'path':t['path'],'date':'2026-10-21',
        'original_due':'2026-09-08','remaining':10,'questions':10}], 'overrides':{},'policies':[]}
    view=service.overview('2026-10-22',_agenda_override=agenda)
    assert view['agenda']['rows'][0]['date']=='2026-10-22'
    assert view['agenda']['rows'][0]['original_due']=='2026-10-22'
    assert agenda['rows'][0]['original_due']=='2026-09-08'


def test_far_future_start_does_not_crash_calendar(tmp_path,monkeypatch,project_root,sample_pdf):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    from streamlit.testing.v1 import AppTest
    from osler.planner_service import today_local
    from datetime import timedelta
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.store.save_profile(AdaptiveProfile(start_date='2030-10-22'),0)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    app.radio(key='adaptive_view').set_value('Calendário').run()
    assert not app.exception
    assert app.date_input(key='calendar_reference').value<=today_local()+timedelta(days=547)


def test_history_labels_pdf_without_date_without_inventing_conviction():
    from osler.study_statistics import topic_statistics
    t={**topic(answered=34),'report_date':None}
    state=topic_states([t],[],[],{},'2026-10-20',AdaptiveProfile())[0]
    row=topic_statistics([state],[],'Todo o período','2026-10-20')[0]
    assert row['Questões realizadas']==34 and row['Convicção (%)'] is None
    assert row['Fonte do histórico']=='PDF · sem data'
