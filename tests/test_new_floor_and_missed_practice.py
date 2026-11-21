from copy import deepcopy
from dataclasses import replace
from osler.study_models import AdaptiveProfile
from osler.adaptive_planning import topic_states,allocate_day
from osler.exam_practice import recover_area_occurrences,practice_context
from test_initial_review_policy import imported


def test_due_load_and_future_pressure_do_not_zero_new_floor():
    p=AdaptiveProfile(max_questions=120,max_topics=6,new_share=.5,workload_mode='adaptive',review_strategy='balanced_v2')
    states=topic_states([imported('R'+str(i),57) for i in range(8)]+[imported('N'+str(i),n=0,contact=None) for i in range(5)],[],[],{},'2026-10-28',p)
    for t in states:
        if not t['is_new_for_day']:t.update(review_committed=True,next_review='2026-10-28',theme_review_due='2026-10-28',recommended_questions=20,theme_recommended_questions=20)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=120,capacity_limits=[(120,6)]+[(0,0)]*13)
    assert sum(t['questions'] for t in plan['items'] if t['is_new_for_day'])>=24
    assert plan['questions']<=120 and len(plan['items'])<=6
    assert allocate_day(states,p,None,'descanso',[],'2026-10-28',question_target=120)['questions']==0
    paused=allocate_day(states,replace(p,new_share=0),None,'normal',[],'2026-10-28',question_target=120)
    assert not any(t['is_new_for_day'] for t in paused['items'])


def test_recovery_is_read_only_single_reservation_and_keeps_completed():
    rows=[{'id':'late','date':'2026-10-29','original_date':'2026-10-29','questions':20},
          {'id':'future','date':'2026-10-31','original_date':'2026-10-31','questions':20}]
    before=deepcopy(rows);p=AdaptiveProfile(max_questions=120)
    recovered=recover_area_occurrences(rows,[],'2026-10-30','2026-11-03',p,{}, {})
    assert rows==before and recovered[0]['date']=='2026-10-30' and recovered[0]['missed_date']=='2026-10-29'
    agenda={'area_practice':recovered,'area_results':[]}
    assert practice_context(agenda,'2026-10-30')['reserved']==20
    assert not practice_context(agenda,'2026-11-02')['tasks']
    result=[{'exam':{'practice_id':'late','day':'2026-10-29','questions':20}}]
    assert recover_area_occurrences(rows,result,'2026-10-30','2026-11-03',p,{}, {})==rows


def test_recovery_skips_protected_days_existing_train_and_capacity():
    rows=[{'id':'late','date':'2026-10-29','original_date':'2026-10-29','questions':20},
          {'id':'future','date':'2026-10-31','original_date':'2026-10-31','questions':20}]
    cfg={'2026-10-30':{'questions':120,'kind':'descanso'},'2026-11-02':{'questions':10,'kind':'normal'}}
    overrides={'2026-11-01':{'mode':'mock_reserved'}}
    p=AdaptiveProfile(max_questions=120)
    recovered=recover_area_occurrences(rows,[],'2026-10-30','2026-11-04',p,cfg,overrides,exam_dates={'2026-11-03'})
    assert recovered[0]['date']=='2026-11-04'
    waiting=recover_area_occurrences(rows,[],'2026-10-30','2026-11-03',p,cfg,overrides,exam_dates={'2026-11-03'})
    assert waiting[0]['status']=='waiting' and waiting[0]['date']=='2026-10-29'


def test_missed_train_can_be_moved_in_preview_without_losing_identity(tmp_path,sample_pdf,monkeypatch):
    from datetime import date
    from test_mock_schedule import configured
    import osler.exam_practice_service as module
    import osler.planner_service as clock
    service,_=configured(tmp_path,sample_pdf)
    p=service.preview_area_schedule('2026-10-15','2026-11-20',1,20,['UNESP'])
    service.apply_area_schedule(p)
    monkeypatch.setattr(module,'today_local',lambda:date(2026,10,16))
    monkeypatch.setattr(clock,'today_local',lambda:date(2026,10,16))
    token=service.agenda.token()
    agenda=service.overview('2026-10-16')
    assert agenda['plan']['area_tasks'][0]['recovery']
    assert agenda['plan']['target_questions']==40
    preview=service.preview_area_schedule(**{**p['request'],'exceptions':{'area-2026-10-15':'2026-10-17'}})
    assert service.agenda.token()==token
    assert preview['occurrences'][0]['date']=='2026-10-17'
    service.apply_area_schedule(preview)
    assert not service.overview('2026-10-16')['plan'].get('area_tasks')
    tasks=service.overview('2026-10-17')['plan']['area_tasks']
    assert len(tasks)==1 and tasks[0]['id']=='area-2026-10-15'
