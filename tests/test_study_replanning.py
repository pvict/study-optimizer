from dataclasses import replace
import pytest
from osler.study_models import AdaptiveProfile,StudyEntry
from osler.adaptive_planning import topic_states
from test_adaptive_planning import topic,session
from test_assessments import setup_assessment


def test_backlog_requires_actual_due_or_saved_missed_plan_and_keeps_original_date():
    from osler.study_replanning import collect_backlog
    p=AdaptiveProfile()
    e=session(day='2026-10-01',n=20,correct=20)
    e['entry']['confident_correct']=20
    states=topic_states([topic(),topic('Unknown',answered=50)],[e],[],{},'2026-10-15',p)
    rows=collect_backlog(states,[e],[],'2026-10-15')
    assert len(rows)==1 and rows[0]['original_due']=='2026-10-08'
    assert rows[0]['days_late']==7


def test_missed_plan_is_net_of_actual_work_and_only_latest_day_plan_counts():
    from osler.study_replanning import collect_backlog
    states=topic_states([topic('A'),topic('B')],[],[],{},'2026-10-15',AdaptiveProfile())
    saved=[{'id':1,'plan':{'date':'2026-10-14','items':[{'path':['Área','A'],'questions':20}]}},
           {'id':2,'plan':{'date':'2026-10-14','items':[{'path':['Área','B'],'questions':20}]}}]
    rows=collect_backlog(states,[session('B',day='2026-10-14',n=8)],saved,'2026-10-15')
    assert len(rows)==1 and rows[0]['path'][-1]=='B' and rows[0]['missed_questions']==12


def test_preview_respects_capacity_rest_and_risk_order_without_changing_evidence():
    from osler.study_replanning import collect_backlog,preview_replan
    p=AdaptiveProfile(max_questions=60,max_topics=2,new_share=.5)
    events=[session('A',day='2026-09-01',n=20,correct=2),session('B',day='2026-10-01',n=20,correct=18)]
    states=topic_states([topic('A'),topic('B')],events,[],{},'2026-10-15',p)
    rows=collect_backlog(states,events,[],'2026-10-15')
    before=repr(states)
    preview=preview_replan(rows,p,'2026-10-15',3,'balanced',{'2026-10-15':{'questions':40,'kind':'descanso','extra_topics':[]}},[])
    assert not any(r['date']=='2026-10-15' for r in preview['rows'])
    assert preview['rows'][0]['topic_id']=='A'
    assert all(r['original_due']<r['date'] for r in preview['rows'])
    assert repr(states)==before


def test_apply_cancel_and_new_results_are_audited_and_stale_preview_is_rejected(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    t=max(s.catalog('2026-10-15')[0],key=lambda t:t['total'])
    s.save_entry(StudyEntry(t['path'],'2026-10-01',20,10,confident_correct=10),'old')
    preview=s.preview_replan('2026-10-15',7,'reviews')
    assert preview['rows']
    s.configure_day('2026-10-16',20,'descanso',0)
    with pytest.raises(ValueError,match='mud|atualiz'): s.apply_replan(preview)
    preview=s.preview_replan('2026-10-15',7,'reviews')
    event=s.apply_replan(preview)
    assert s.replanning()['active']
    assert len(s.store.active('2026-10-15'))==1
    s.cancel_replan(event)
    assert not s.replanning()['active']
    assert len(s.store.active('2026-10-15'))==1


def test_completed_today_has_no_recovery_capacity_and_all_modes_preserve_rest():
    from osler.study_replanning import collect_backlog,preview_replan
    p=AdaptiveProfile(max_questions=60,new_share=.5)
    events=[session(day='2026-10-01',n=20,correct=10)]
    states=topic_states([topic()],events,[],{},'2026-10-15',p)
    backlog=collect_backlog(states,events,[],'2026-10-15')
    used={'2026-10-15':{'new':30,'reviews':30,'total':60}}
    preview=preview_replan(backlog,p,'2026-10-15',1,'balanced',{},[],usage=used)
    assert preview['rows']==[] and preview['unassigned']
    for mode in ['balanced','reviews','extra','custom']:
        preview=preview_replan(backlog,p,'2026-10-16',3,mode,{'2026-10-16':{'questions':60,'kind':'descanso','extra_topics':[]}},[],dates={backlog[0]['topic_id']:'2026-10-17'})
        assert preview['rows'] and preview['rows'][0]['date']=='2026-10-17'


def test_applied_reservation_moves_schedule_without_erasing_delay_or_faking_contact(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    t=max(s.catalog('2026-10-15')[0],key=lambda t:t['total'])
    s.save_entry(StudyEntry(t['path'],'2026-10-01',20,10,confident_correct=10),'original')
    preview=s.preview_replan('2026-10-17',7,'reviews')
    event=s.apply_replan(preview)
    current=s.overview('2026-10-15')
    assert t['topic_id'] not in [i['topic_id'] for i in current['plan']['items']]
    state=next(r for r in current['states'] if r['topic_id']==t['topic_id'])
    assert state['last_contact']=='2026-10-01' and state['next_review']<'2026-10-15'
    plans=s.calendar(4)
    assert next(d for d in plans if d['date']=='2026-10-17')['items'][0]['rescheduled']
    s.save_entry(StudyEntry(t['path'],'2026-10-15',20,20,confident_correct=20),'new-real')
    assert not s.replanning()['rows']
    assert len(s.store.active('2026-10-15'))==2
    s.cancel_replan(event)
    assert len(s.store.active('2026-10-15'))==2


def test_returning_to_prior_daily_proposal_remains_latest_in_history(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    from osler.study_replanning import collect_backlog
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    original=s.overview('2026-10-15')
    first=s.remember_day(original)
    s.configure_day('2026-10-15',60,'descanso',0)
    rest=s.remember_day(s.overview('2026-10-15'))
    s.configure_day('2026-10-15',60,'normal',1)
    latest=s.remember_day(s.overview('2026-10-15'))
    assert first<rest<latest
    assert s.remember_day(s.overview('2026-10-15'))==latest


def test_partial_recovery_replanning_keeps_only_remaining_questions(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    t=max(s.catalog('2026-10-15')[0],key=lambda t:t['total'])
    s.save_entry(StudyEntry(t['path'],'2026-10-01',20,10,confident_correct=10),'old')
    p=s.preview_replan('2026-10-16',7,'reviews')
    s.apply_replan(p)
    n=p['rows'][0]['questions']
    s.save_entry(StudyEntry(t['path'],'2026-10-15',5,4),'partial')
    remaining=s.replanning()['rows'][0]['remaining']
    assert remaining==n-5
    fresh=s.preview_replan('2026-10-17',7,'reviews')
    assert fresh['rows'][0]['questions']==remaining


def test_expired_existing_reservation_uses_capacity_before_new_recovery():
    from osler.study_replanning import preview_replan
    p=AdaptiveProfile(max_questions=60,max_topics=1,new_share=0)
    old={'topic_id':'A','path':['Area','A'],'date':'2026-10-14','remaining':60,'new_topic':False}
    new={'topic_id':'B','path':['Area','B'],'questions':60,'original_due':'2026-10-01','days_late':14,'is_new_for_day':False}
    preview=preview_replan([new],p,'2026-10-15',2,'balanced',{},[old])
    assert preview['rows'][0]['date']=='2026-10-16'


def test_reserved_recovery_still_respects_today_split_after_temporary_mode_ends():
    from osler.adaptive_planning import allocate_day
    p=AdaptiveProfile(max_questions=120,max_topics=5,new_share=.5)
    states=topic_states([topic('A',answered=50),topic('N0'),topic('N1'),topic('N2')],[],[],{},'2026-10-15',p)
    row={'topic_id':'A','date':'2026-10-14','original_due':'2026-10-01','remaining':100}
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=120,reservations=[row])
    assert plan['distribution']['planned_reviews']==60
    assert plan['distribution']['planned_new']==60
    assert plan['items'][0].get('rescheduled')


def test_unassigned_selected_reservations_are_released_auditably_and_undo_restores(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    def row(name,day): return {'topic_id':name,'path':['Area',name],'date':day,'original_due':'2026-10-01','questions':20,'new_topic':False}
    first=s.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-15','cutoff':0,'selected':['A','B'],'rows':[row('A','2026-10-16'),row('B','2026-10-17')]},s.agenda.token())
    second=s.agenda.append({'kind':'reschedule.apply','created_day':'2026-10-15','cutoff':0,'selected':['A','B'],'rows':[row('A','2026-10-17')]},s.agenda.token())
    active=s.agenda.active([],'2026-10-15')
    assert [r['topic_id'] for r in active['rows']]==['A']
    s.agenda.append({'kind':'reschedule.cancel','plan_id':second,'created_day':'2026-10-15'},s.agenda.token())
    assert {r['topic_id'] for r in s.agenda.active([],'2026-10-15')['rows']}=={'A','B'}


def test_balance_preview_uses_prior_overrides_without_owning_them():
    from osler.study_replanning import preview_replan
    p=AdaptiveProfile(max_questions=60,new_share=.5)
    item={'topic_id':'A','path':['Area','A'],'questions':60,'original_due':'2026-10-01','days_late':14,'is_new_for_day':False}
    preview=preview_replan([item],p,'2026-10-15',1,'balanced',{},[],previous_overrides={'2026-10-15':{'mode':'reviews'}})
    assert preview['rows'] and not preview['overrides']


def test_agenda_roundtrip_backup_keeps_schedule_history_and_originals(tmp_path,sample_pdf):
    from osler.adaptive_service import AdaptiveService
    from osler.backups import create_backup,restore_backup,inspect_backup
    from osler.storage import Repository
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo)
    t=max(s.catalog('2026-10-15')[0],key=lambda t:t['total'])
    s.save_entry(StudyEntry(t['path'],'2026-10-01',20,10,confident_correct=10),'old')
    s.remember_day(s.overview('2026-10-15'))
    s.apply_replan(s.preview_replan('2026-10-17',7,'extra',extra_questions=30))
    backup=create_backup(repo)
    assert inspect_backup(backup.read_bytes())['schema_version']==12
    restored=AdaptiveService(Repository(restore_backup(backup.read_bytes(),tmp_path/'restored')))
    assert restored.replanning()['rows']==s.replanning()['rows']
    assert restored.replanning()['history']==s.replanning()['history']
    assert len(restored.store.active('2026-10-15'))==1


def test_expired_reservations_execute_in_the_same_date_order_as_preview():
    from osler.adaptive_planning import allocate_day
    p=AdaptiveProfile(max_questions=60,new_share=0,max_topics=1)
    states=topic_states([topic('A',answered=20),topic('B',answered=20)],[],[],{},'2026-10-15',p)
    rows=[{'topic_id':n,'date':d,'original_due':'2026-10-01','remaining':60} for n,d in [('B','2026-10-15'),('A','2026-10-14')]]
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=60,reservations=rows)
    assert plan['items'][0]['topic_id']=='A'
