from copy import deepcopy
from datetime import datetime,timezone
import pytest
from osler.study_dashboard import hero_state,week_summary,date_label,entry_clock,pause_remaining


def view():
    return {'date':'2026-10-15','plan':{'kind':'normal','items':[{'topic_id':'A'}],
        'done_questions':20,'target_questions':60},'states':[{'learning_state':'aprendendo'}],
        'sessions':[],'profile':{'max_questions':60}}


def event(day,n=20,correct=16,mode='novas',kind='bloco'):
    return {'entry':{'day':day,'questions':n,'correct':correct,'mode':mode,'kind':kind}}


def test_hero_states_use_actual_plan_not_a_generated_goal():
    v=view();assert hero_state(v)=='study'
    v['plan']['kind']='descanso';assert hero_state(v)=='rest'
    v['plan']['kind']='normal';v['plan']['done_questions']=60
    assert hero_state(v)=='study'  # Volume extra não esconde blocos preservados.
    v['plan']['items']=[];assert hero_state(v)=='complete'
    v['states']=[];assert hero_state(v)=='empty'
    v['states']=[{}];v['plan']['not_started']=True;assert hero_state(v)=='not_started'


def test_week_rest_does_not_become_missing_and_future_has_no_fabricated_work():
    v=view();v['sessions']=[event('2026-10-12',60),event('2026-10-14',10),event('2026-10-15',20)]
    settings={'2026-10-13':{'kind':'descanso','questions':60},'2026-10-14':{'kind':'normal','questions':60}}
    before=deepcopy(v);s=week_summary(v,settings)
    assert [r['status'] for r in s['days']]==['done','rest','partial','partial','future','future','future']
    assert s['study_days']==3 and s['rest_days']==1 and s['questions']==90
    assert v==before


def test_week_accuracy_keeps_new_exact_counts_separate_from_all_other_sources():
    v=view();v['sessions']=[event('2026-10-12',20,18),event('2026-10-13',10,5,'repetidas'),
        event('2026-10-14',10,8,'mistas'),event('2026-10-15',100,90,kind='acumulado'),event('2026-10-15',5,None)]
    s=week_summary(v,{})
    assert s['questions']==45 and s['new_n']==20 and s['new_correct']==18
    assert s['new_accuracy']==.9 and s['new_unknown']==5
    assert s['exam_days'] is None


def test_absent_sources_and_guide_contacts_do_not_invent_question_mastery():
    v=view();v['states']=[]
    s=week_summary(v,{},[{'day':'2026-10-13','status':'feito','path':['A']}])
    assert s['new_accuracy'] is None and s['mastered'] is None and s['questions']==0
    assert s['study_days']==1
    s=week_summary(v,{},exam={'exam_date':'2026-10-20'})
    assert s['exam_days']==5


def test_timestamp_is_entry_time_in_brasilia_not_study_completion():
    assert entry_clock({'created_at':'2026-10-16T01:30:00+00:00'})=='22:30'
    assert entry_clock({}) is None
    assert entry_clock({'created_at':'2026-10-16T01:30:00'}) is None
    assert date_label('2026-10-15')=='Quinta, 15 de outubro'


def test_pause_is_nonblocking_and_unknown_deadline_is_not_a_timer_zero():
    assert pause_remaining(None,100) is None
    assert pause_remaining(700,100)==600
    assert pause_remaining(700,699.3)==1
    assert pause_remaining(700,701)==0


def test_mock_day_counts_as_study_without_adding_mock_questions_to_blocks():
    v=view()
    s=week_summary(v,{'2026-10-13':{'kind':'normal','questions':60}},mock_days={'2026-10-13'})
    assert s['study_days']==1 and s['days'][1]['status']=='done'
    assert s['questions']==0 and s['new_accuracy'] is None
