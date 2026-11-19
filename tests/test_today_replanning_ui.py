from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from test_assessments import setup_assessment
from ui_actions import confirm_action


def test_today_outside_plan_distinguishes_due_future_and_dispensed_reviews():
    from osler.today_replanning_ui import reviews_outside_today

    day='2026-10-15'
    states=[{'topic_id':name,'path':['Área',name],'total':20,'next_review':day,'last_contact':None}
            for name in ['Com bloco','Sem bloco','Atraso remanejado','Previsto depois','Dispensado','Adiado na Osler']]
    states[-1]['return_not_before']='2026-10-16'
    states[2]['reschedule_date']=states[3]['next_review']='2026-10-16'
    view={'date':day,'planning_states':states,'plan':{'kind':'normal','items':[states[0]],
          'planner_completions':[{'topic_id':'Dispensado'}]},
          'agenda':{'rows':[{'topic_id':'Atraso remanejado','date':date,'remaining':12}
                           for date in ['2026-10-13','2026-10-16']]}}
    backlog=[{'topic_id':'Atraso remanejado','original_due':'2026-10-12'}]
    assert reviews_outside_today(view,backlog)==[
        {'Tema':'Área › Sem bloco','Data indicada':'15/10/2026','Reserva':'Sem reserva'},
        {'Tema':'Área › Atraso remanejado','Data indicada':'12/10/2026','Reserva':'16/10/2026'},
    ]


def test_today_finds_dates_applies_and_undoes_without_recording_study(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    topic=max(service.catalog('2026-10-15')[0],key=lambda t:t['total'])
    service.save_entry(StudyEntry(topic['path'],'2026-10-01',20,10,confident_correct=10),'old')
    before=service.store.events()
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert any(e.label.startswith('Atrasos e próximas datas') and not e.proto.expanded for e in app.expander)
    buttons=list(app.button)
    assert next(i for i,b in enumerate(buttons) if b.label=='Registrar este bloco') < buttons.index(app.button(key='today_replan_preview'))
    app.button(key='today_replan_preview').click().run()
    assert not app.exception and not app.error
    assert service.store.events()==before
    assert not service.replanning()['rows']
    assert any('Nova data' in f.value.columns for f in app.dataframe)
    confirm_action(app.button(key='today_replan_apply').click().run())
    assert not app.exception and not app.error
    assert service.replanning()['rows']
    assert service.store.events()==before
    confirm_action(app.button(key='today_replan_undo').click().run())
    assert not app.exception and not app.error
    assert not service.replanning()['rows']
    assert service.store.events()==before
    app.button(key='today_replan_advanced').click().run()
    assert not app.exception
    assert app.session_state['adaptive_view']=='Calendário'
    assert next(e for e in app.expander if e.label=='Reorganizar atrasos').proto.expanded


def test_undo_keeps_the_plan_shown_when_another_session_replans(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    topic=max(s.catalog('2026-10-15')[0],key=lambda t:t['total'])
    s.save_entry(StudyEntry(topic['path'],'2026-10-01',20,10,confident_correct=10),'old')
    s.apply_replan(s.preview_replan('2026-10-17',7,'reviews'))
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    second=s.apply_replan(s.preview_replan('2026-10-19',7,'reviews'))
    records=[r for r in s.agenda.records() if r.get('kind','').startswith('reschedule.')]
    results=s.store.events()
    confirm_action(app.button(key='today_replan_undo').click().run())
    assert not app.exception
    assert [r for r in s.agenda.records() if r.get('kind','').startswith('reschedule.')]==records
    assert s.store.events()==results
    assert second in {r['id'] for r in s.replanning()['active']}

