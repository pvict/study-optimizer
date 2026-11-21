from dataclasses import asdict
from datetime import date, timedelta

import pytest

from osler.adaptive_planning import topic_states
from osler.study_allocation import category_allocation
from osler.study_feedback import result_feedback
from osler.study_models import AdaptiveProfile
from osler.topic_trajectory import topic_trajectory, trajectory_summary
from test_adaptive_planning import session, topic


DAY = '2026-11-20'


@pytest.mark.parametrize('strategy', ['legacy_v1', 'balanced_v2'])
def test_five_questions_do_not_force_urgent_review(strategy):
    profile = AdaptiveProfile(review_strategy=strategy, return_mode='theme')
    event = session(day=DAY, n=5, correct=3)
    event['entry']['confident_correct'] = 2
    state, = topic_states([topic()], [event], [], {}, DAY, profile)
    assert state['review_interval_days'] == 7
    assert state['evidence_priority'] != 'urgente'
    assert not state['low_accuracy'] and state['learning_state'] == 'aprendendo'
    assert 'Amostra pequena' in state['reason']


@pytest.mark.parametrize('strategy,correct', [('legacy_v1',6), ('balanced_v2',5)])
def test_supported_failure_still_returns_in_three_days(strategy, correct):
    profile = AdaptiveProfile(review_strategy=strategy, return_mode='theme')
    event = session(day=DAY, n=10, correct=correct)
    event['entry']['confident_correct'] = 4
    state, = topic_states([topic()], [event], [], {}, DAY, profile)
    assert state['review_interval_days'] == 3
    assert state['evidence_priority'] == 'urgente'


@pytest.mark.parametrize('strategy', ['legacy_v1', 'balanced_v2'])
def test_unstudied_leaf_under_started_theme_is_continuation(strategy):
    from osler.algorithm_parameters import AlgorithmParameters
    profile = AdaptiveProfile(review_strategy=strategy, parameter_values=AlgorithmParameters(version=2,diagnostic_dose=40).to_dict())
    studied_parent = {**topic('A'), 'path':['Área','Pai','A'], 'theme_started': True, 'theme_path': ['Área', 'Pai']}
    new = {**topic('B'), 'theme_started': False}
    states = {t['topic_id']:t for t in topic_states([studied_parent,new], [], [], {}, DAY, profile)}
    a, b = states['A'], states['B']
    assert a['status'] == 'sem_registro' and a['last_contact'] is None
    assert not a['is_new_for_day'] and a['stage'] == 'Continuação do tema'
    assert a['theme_recommended_questions'] < 40
    assert b['is_new_for_day'] and b['stage'] == 'Primeiro contato'
    assert b['theme_recommended_questions'] >= 40


def test_new_pool_prefers_institutional_node_then_bank_and_feasible_minimum():
    profile = AdaptiveProfile(max_topics=1, new_share=1)
    values=[('baixa',90,.1),('médio',20,.2),('micro',1,1),('alto',40,.2)]
    states = [{**topic(name,total), 'status':'sem_registro', 'theme_incidence':weight,
               'recommended_questions':10, 'allocation_capacity':total, 'score':5 if name=='baixa' else 1}
              for name,total,weight in values]
    selected, _, _ = category_allocation(states, states, profile, 20, 20, [])
    assert [row['topic_id'] for row in selected] == ['alto']


def test_small_bank_receipt_and_trajectory_show_complement_without_near_booking():
    profile = AdaptiveProfile(return_mode='theme')
    event = {**session(day=DAY,n=5,correct=3), 'session_id':'result'}
    event['entry']['confident_correct'] = 2
    state, = topic_states([topic(total=1)], [event], [], {}, DAY, profile)
    feedback = result_feedback({'sessions':[event],'states':[state], 'profile':asdict(profile),
                                'date':DAY, 'review_queue':[]}, 'result')
    assert feedback['next_contact'] is None and feedback['next_questions'] is None
    assert 'Falta complemento' in feedback['next_action']
    roadmap = topic_trajectory(state,profile,DAY)
    assert 1 <= len(roadmap['steps']) <= 3
    assert max(step['cumulative_questions'] or 0 for step in roadmap['steps']) <= 3
    assert 'repetir o mesmo conjunto' in roadmap['assumption']


def test_trajectory_capacity_exposes_only_three_small_bank_cycles():
    profile = AdaptiveProfile()
    small, large = topic_states([topic('A',total=12),topic('B',total=40)],[],[],{},DAY,profile)
    slots=[{'date':(date.fromisoformat(DAY)+timedelta(days=i)).isoformat(),
            'items':[{'topic_id':'A','questions':12},{'topic_id':'B','questions':20}]} for i in range(7)]
    slots.append({'date':'2026-11-27','items':[{'topic_id':'A','questions':5,'added_by_user':True,'extra_pending':5}]})
    summary = trajectory_summary([small,large],profile,DAY,slots)
    a,b=summary['rows']
    assert (a['Questões com vaga prevista'],a['Encontros com vaga prevista']) == (41,4)
    assert (b['Questões com vaga prevista'],b['Encontros com vaga prevista']) == (140,7)


def test_conditional_calendar_stops_small_bank_cycles_and_keeps_manual_extra():
    from osler.study_calendar import forecast_calendar

    profile=AdaptiveProfile(max_questions=20, max_topics=2, new_share=.5)
    states=topic_states([topic('A',total=12),topic('B',total=60)],[],[],{},DAY,profile)
    settings={'2027-01-18':{'questions':20,'kind':'normal',
              'extra_topics':[{'topic_id':'A','extra_id':'manual','questions':5,'after_event_id':0}]}}
    days=forecast_calendar(states,profile,DAY,70,[],settings)
    smaller=[item for day in days for item in day['items'] if item['topic_id']=='A']
    assert sum(item['questions'] for item in smaller if not item['added_by_user'])<=36
    assert [item['questions'] for item in smaller if item['added_by_user']]==[5]
    assert sum(item['topic_id']=='B' for day in days for item in day['items'])>3
    rows={row['topic_id']:row for row in trajectory_summary(states,profile,DAY,days)['rows']}
    assert rows['A']['Questões com vaga prevista']==sum(item['questions'] for item in smaller)
