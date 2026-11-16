from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from test_assessments import setup_assessment
from ui_actions import confirm_action


def test_today_finds_dates_applies_and_undoes_without_recording_study(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    topic=max(service.catalog('2026-10-15')[0],key=lambda t:t['total'])
    service.save_entry(StudyEntry(topic['path'],'2026-10-01',20,10,confident_correct=10),'old')
    before=service.store.events()
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert any('Atrasos e próximas datas'==h.value for h in app.subheader)
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


def test_quick_replan_preserves_another_topics_future_date(tmp_path,sample_pdf):
    from osler.study_replanning import backlog_schedule
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    topics=s.catalog('2026-10-15')[0]
    large=max(topics,key=lambda t:t['total'])
    s.save_entry(StudyEntry(large['path'],'2026-10-01',20,10,confident_correct=10),'old')
    s.apply_replan(s.preview_replan('2026-10-20',7,'reviews',selected=[large['topic_id']]))
    # A saved missed new-topic block creates a separate real backlog item.
    small=min(topics,key=lambda t:t['total'])
    s.agenda.append({'kind':'daily_schedule','plan':{'date':'2026-10-14','items':[
        {'topic_id':small['topic_id'],'path':small['path'],'questions':1}]}},s.agenda.token())
    context=s.replanning()
    missing=[r['topic_id'] for r in backlog_schedule(context['backlog'],context['rows'],'2026-10-15') if not r['recovery_current']]
    assert small['topic_id'] in missing and large['topic_id'] not in missing
    prior=[dict(r) for r in context['rows']]
    preview=s.preview_replan('2026-10-15',90,'balanced',selected=missing)
    assert large['topic_id'] not in preview['selected']
    assert s.replanning()['rows']==prior
    if preview['rows']:
        s.apply_replan(preview)
        assert [r for r in s.replanning()['rows'] if r['topic_id']==large['topic_id']]==prior
