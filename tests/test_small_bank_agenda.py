from dataclasses import replace

import pytest

from osler.adaptive_planning import allocate_day, topic_states
from osler.algorithm_parameters import V1
from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile
from osler.study_replanning import collect_backlog, preview_replan
from test_adaptive_planning import session, topic


DAY = '2026-10-15'


def test_saved_plan_requires_contact_and_a_bank_that_fits_the_minimum():
    profile = AdaptiveProfile()
    themes = [topic('Fragmento', total=1), topic('Novo'), topic('Estudado')]
    events = [session(name, day='2026-10-01', n=10, correct=8)
              for name in ('Fragmento', 'Estudado')]
    states = topic_states(themes, events, [], {}, DAY, profile)
    history = [{'plan': {'date': '2026-10-14', 'items': [
        {'path': row['path'], 'questions': min(row['total'], 20)} for row in themes
    ]}}]

    backlog = collect_backlog(states, events, history, DAY)

    assert [row['topic_id'] for row in backlog] == ['Estudado']
    assert backlog[0]['source_days'] == ['2026-10-14']


def test_older_guide_contact_keeps_a_proven_missed_plan_after_a_short_block():
    theme=topic('Medido')
    events=[session('Medido',day='2026-10-13',n=1,correct=1)]
    states=topic_states([theme],events,[],{},DAY,AdaptiveProfile(),
                       contacts=[(theme['path'],'2026-10-01'),(theme['path'],'2026-10-12')])
    history=[{'plan':{'date':'2026-10-11','items':[{'path':theme['path'],'questions':20}]}}]
    row,=collect_backlog(states,events,history,DAY)
    assert row['source_days']==['2026-10-11'] and row['missed_questions']==20


@pytest.mark.parametrize('strategy', ['legacy_v1', 'balanced_v2'])
@pytest.mark.parametrize('mode', ['fixed', 'adaptive'])
def test_saved_fragment_reservation_never_consumes_a_planning_slot(strategy, mode):
    profile = AdaptiveProfile(max_topics=4, new_share=1, review_strategy=strategy, workload_mode=mode)
    themes = [topic('Fragmento', total=1), *(topic(name) for name in ('A', 'B', 'C', 'D'))]
    states = topic_states(themes, [], [], {}, DAY, profile)
    booking = {'topic_id': 'Fragmento', 'date': DAY, 'original_due': '2026-10-10',
               'remaining': 1, 'automatic_replan': True}
    args = (states, profile, None, 'normal', [], DAY)
    target = 100
    expected = allocate_day([r for r in states if r['topic_id']!='Fragmento'], profile, None, 'normal',
                            [], DAY, question_target=target)
    actual = allocate_day(*args, question_target=target, reservations=[booking])
    assert [(r['topic_id'], r['questions']) for r in actual['items']] == [
        (r['topic_id'], r['questions']) for r in expected['items']
    ]
    assert {row['topic_id'] for row in actual['items']} == {'A', 'B', 'C', 'D'}
    future = forecast_calendar(states, profile, DAY, 1, [],
                               {DAY: {'questions': target, 'kind': 'normal'}},
                               agenda={'rows': [booking], 'overrides': {}})
    assert {r['topic_id'] for r in future[0]['items']} == {'A', 'B', 'C', 'D'}


@pytest.mark.parametrize('automatic', [False, True])
def test_short_ordinary_recovery_balance_never_uses_a_full_slot(automatic):
    profile = AdaptiveProfile(max_topics=1, new_share=.5)
    states = topic_states([topic('A'), topic('B')], [], [], {}, DAY, profile)
    next(r for r in states if r['topic_id']=='A').update(reschedule_date=DAY)
    booking = {'topic_id': 'A', 'date': DAY, 'original_due': '2026-10-10',
               'remaining': 1, 'automatic_replan': automatic}
    actual = allocate_day(states, profile, None, 'normal', [], DAY,
                          question_target=60, reservations=[booking])
    assert [r['topic_id'] for r in actual['items']] == ['B']


def test_short_bank_still_allows_explicit_additions_today_and_in_the_forecast():
    profile = AdaptiveProfile()
    states = topic_states([topic('Fragmento', total=1)], [], [], {}, DAY, profile)
    extra = {'topic_id': 'Fragmento', 'extra_id': 'manual-1', 'questions': 1, 'after_event_id': 0}
    actual = allocate_day(states, profile, None, 'normal', [], DAY, question_target=60,
                          extra_topics=[{**states[0], **extra, 'requested': 1}])
    assert [(r['questions'], r['added_by_user']) for r in actual['items']] == [(1, True)]
    calendar = forecast_calendar(states, profile, DAY, 2, [],
                                 {DAY: {'questions': 60, 'kind': 'normal', 'extra_topics': [extra]}})
    assert [(r['questions'], r['added_by_user']) for r in calendar[0]['items']] == [(1, True)]
    assert not calendar[1]['items'] and not calendar[1]['backlog_items']


def test_backlog_preview_does_not_offer_or_charge_old_small_bank_reservations():
    profile = AdaptiveProfile(max_topics=1, new_share=0)
    required = {'topic_id': 'B', 'path': ['Área', 'B'], 'questions': 20, 'total': 100,
                'original_due': '2026-10-10', 'days_late': 5}
    fragment = {**required, 'topic_id': 'A', 'path': ['Área', 'A'], 'questions': 1,
                'total': 1, 'date': DAY, 'remaining': 1}
    actual = preview_replan([fragment, required], profile, DAY, 1, 'balanced', {}, [fragment])
    assert [r['topic_id'] for r in actual['rows']] == ['B']
    assert not actual['unassigned']


def test_linked_return_on_ordinary_bank_keeps_its_real_dose_despite_old_short_reservation():
    profile = AdaptiveProfile(max_questions=20, new_share=0, review_strategy='balanced_v2',target_accuracy=95,
                              parameter_values=replace(V1,version=2,first_interval=14).to_dict())
    recorded = {**session('A', day='2026-10-08', n=19, correct=17),
                'id':8,'session_id':'recorded','version':1}
    recorded['entry']['confident_correct']=15
    states = topic_states([topic('A')], [recorded], [], {}, DAY, profile)
    booking = {'topic_id':'A','date':DAY,'original_due':'2026-10-14','remaining':1,'automatic_replan':True}
    plan = allocate_day(states, profile, None, 'normal', [recorded], DAY,
                        question_target=20, reservations=[booking])
    assert [(r['questions'],r['review_kind'],r.get('rescheduled',False))
            for r in plan['items']]==[(4,'lot_only',False)]


def test_old_invalid_reservations_are_only_hidden_from_the_operational_view(tmp_path,monkeypatch):
    from osler.adaptive_service import AdaptiveService
    from osler.storage import Repository
    from osler.study_models import StudyEntry

    service=AdaptiveService(Repository(tmp_path))
    themes=[{**topic('Fragmento',total=1),'is_leaf':True},{**topic('Outro'),'is_leaf':True}]
    monkeypatch.setattr(service,'catalog',lambda *a,**k:(themes,{'qbank':None,'flashcards':None}))
    service.save_entry(StudyEntry(themes[0]['path'],'2026-10-03',1,0),'recorded')
    service.agenda.append({'kind':'reschedule.apply','mode':'balanced','cutoff':1,
                           'created_day':'2026-10-14','selected':['Fragmento','Outro'],'rows':[
        {'topic_id':t['topic_id'],'path':t['path'],'date':DAY,'original_due':'2026-10-10',
         'questions':q,'new_topic':new} for t,q,new in zip(themes,[1,20],[False,True])]},service.agenda.token())
    raw=service.agenda.records()
    view=service.overview(DAY)
    assert not view['agenda']['rows']
    assert not service.replanning(DAY,view=view)['backlog']
    assert [i['topic_id'] for i in view['plan']['items']]==['Outro']
    assert not view['plan']['items'][0].get('rescheduled')
    assert len(view['sessions'])==1 and service.agenda.records()==raw
