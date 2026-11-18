"""Regressões da cobertura: portabilidade, exposição e reservas automáticas."""
from dataclasses import replace
from copy import deepcopy

import pytest

from osler.adaptive_planning import allocate_day, topic_states
from osler.study_models import AdaptiveProfile
from test_adaptive_planning import topic, session
from test_new_floor_guidance import scenario


def test_export_paths_are_portable_and_confined(tmp_path):
    from osler.files import export_folder
    from types import SimpleNamespace
    repo = SimpleNamespace(root=tmp_path, exports=tmp_path / 'exports')
    folder = repo.exports / 'planner' / 'test'
    folder.mkdir(parents=True)
    for stored in ['exports/planner/test', r'exports\planner\test']:
        assert export_folder(repo, stored) == folder.resolve()
    for stored in ['../outside', 'exports/../outside', r'exports\..\outside',
                   '/exports/test', r'C:\exports\test', r'\\server\exports',
                   'exports/planner:stream', 'elsewhere/test']:
        with pytest.raises(ValueError):
            export_folder(repo, stored)


def test_limited_question_practice_does_not_merge_overlapping_evidence():
    p = AdaptiveProfile(workload_mode='adaptive', review_strategy='balanced_v2')
    t = {**topic(answered=2), 'studied_cards':200, 'planner_snapshot':{
        'observed_date':'2026-10-15', 'unique_questions':5,
        'confident_accuracy_pct':80, 'pending_reviews':0,
        'last_contact':'2026-10-10', 'available_questions':100, 'dataset_id':1}}
    states = topic_states([t], [session(n=8, correct=7, day='2026-10-16')], [], {}, '2026-10-17', p)
    s = states[0]
    assert s['question_exposure'] == 8  # Não soma 2 PDF + 5 Planner + 8 app.
    assert s['limited_practice'] and not s['is_new_for_day']
    assert s['performance']['exact_n'] == 8
    cards_only = topic_states([{**topic(), 'studied_cards':200}], [], [], {}, '2026-10-17', p)[0]
    assert cards_only['question_exposure'] == 0 and cards_only['limited_practice']
    assert not cards_only['is_new_for_day']
    practiced = topic_states([topic(answered=35)], [], [], {}, '2026-10-17', p)[0]
    assert not practiced['limited_practice']


def test_automatic_backlog_cannot_consume_the_new_topic_floor():
    states, p, args = scenario(questions=30, slots=4, minimum=.4)
    p = replace(p, review_strategy='balanced_v2')
    args['reservations'] = [{**r, 'manual_date':False, 'automatic_replan':True}
                            for r in args['reservations']]
    before = deepcopy((states, args))
    plan = allocate_day(states, p, **args)
    assert plan['capacity']['new_floor']['missing'] == 0
    assert plan['distribution']['planned_new'] >= 12
    assert plan['questions'] <= 30
    assert len(plan['items']) <= 4
    recovered = [i for i in plan['items'] if i['topic_id'].startswith('R')]
    assert recovered and all(i['rescheduled'] and i['original_due']=='2026-11-01' for i in recovered)
    assert (states, args) == before


def test_low_exposure_initial_theme_can_enter_despite_projected_review_pressure():
    from osler.study_capacity import capacity_policy
    states, p, _ = scenario(questions=30, slots=4, minimum=.4)
    p = replace(p, review_strategy='balanced_v2')
    little = {**next(t for t in states if t['topic_id']=='R1'),
              'limited_practice':True, 'question_exposure':2,
              'initial_contact_deadline':'2027-01-01', 'review_committed':False,
              'next_review':'2026-11-16', 'recommended_questions':10}
    due = {**next(t for t in states if t['topic_id']=='R2'),
           'review_committed':True, 'next_review':'2026-11-16',
           'theme_review_due':'2026-11-16', 'theme_recommended_questions':20}
    new = next(t for t in states if t['topic_id']=='N')
    kept, _, meta = capacity_policy([little, due, new],p,'2026-11-16',30,30)
    assert little['topic_id'] in {s['topic_id'] for s in kept}
    assert meta['protected_intake_topic'] == little['topic_id']


def test_automatic_recovery_never_creates_questions_beyond_the_pending_balance():
    from osler.study_calendar import forecast_calendar
    states, p, args = scenario(questions=30, slots=4, minimum=.4)
    p = replace(p, review_strategy='balanced_v2')
    args['reservations'] = [{**args['reservations'][0], 'remaining':3, 'questions':3,
                            'manual_date':False, 'automatic_replan':True}]
    plan = allocate_day(states,p,**args)
    row = next(i for i in plan['items'] if i['topic_id']=='R1')
    assert row['questions'] <= 3
    assert plan['capacity']['new_floor']['missing'] == 0
    agenda = {'rows':args['reservations'], 'overrides':{}}
    future = forecast_calendar(states,p,args['as_of'],8,[],{},plan,agenda,next_contact_only=True)
    recovered = [i for d in future for i in d['items'] if i['topic_id']=='R1' and i.get('rescheduled')]
    assert sum(i['questions'] for i in recovered) == 3


def test_partial_automatic_booking_stays_available_without_resetting_next_review():
    states,p,args = scenario(questions=30,slots=4,minimum=.4)
    original_due = '2026-11-23'
    states = [{**s,'next_review':original_due} if s['topic_id']=='R1' else s for s in states]
    args['reservations'] = [{**args['reservations'][0], 'manual_date':False,
                            'automatic_replan':True,'remaining':10}]
    plan = allocate_day(states,p,**args)
    r = next(i for i in plan['items'] if i['topic_id']=='R1')
    assert r['questions']==10 and r['rescheduled']
    assert r['next_review']==original_due


@pytest.mark.parametrize('flag',['manual_date','daily_proposal','swap_return','return_unavailable','final_review','correction'])
def test_special_commitments_remain_protected_even_when_tagged_automatic(flag):
    states,p,args = scenario(questions=30,slots=4,minimum=.4)
    args['reservations'] = [{**args['reservations'][0], 'manual_date':False,
                            'automatic_replan':True,flag:True,'remaining':30,'questions':30}]
    plan = allocate_day(states,p,**args)
    assert plan['items'][0]['topic_id']=='R1'
    assert plan['items'][0]['questions']==30
    assert plan['distribution']['planned_new']==0


def test_floor_guidance_can_replace_an_automatic_booking_but_not_a_manual_one():
    states,p,args = scenario(questions=30,slots=1,share=.05,minimum=.4)
    args['reservations'] = [{**args['reservations'][0], 'manual_date':False, 'automatic_replan':True}]
    plan = allocate_day(states,p,**args,diagnose_new_floor=True)
    info = plan['capacity']['new_floor']
    assert info['missing']>0
    assert info['protected_questions']==0
    assert any(o['max_topics']==1 for o in info['options'])


@pytest.mark.parametrize('mode,scope,automatic,manual',[
    ('balanced',None,True,False), ('custom',None,False,True),
    ('balanced','mock_correction',False,False)])
def test_agenda_derives_booking_provenance_without_rewriting_history(tmp_path,mode,scope,automatic,manual):
    from osler.storage import Repository
    from osler.study_agenda import StudyAgenda
    agenda = StudyAgenda(Repository(tmp_path))
    payload = {'kind':'reschedule.apply','mode':mode,'scope':scope,'created_day':'2026-11-16',
        'cutoff':0,'selected':['R1'],'rows':[{'topic_id':'R1','path':['Area','R1'],
        'date':'2026-11-16','original_due':'2026-11-01','questions':20}]}
    agenda.append(payload,agenda.token())
    before = agenda.records()
    row = agenda.active([],'2026-11-16')['rows'][0]
    assert row['automatic_replan'] is automatic
    assert row['manual_date'] is manual
    assert agenda.records()==before
