from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile
from osler.adaptive_planning import topic_states
from test_adaptive_planning import topic


def test_calendar_rotates_topics_and_does_not_fabricate_performance_or_sessions():
    p=AdaptiveProfile(max_questions=20,max_topics=2)
    states=topic_states([topic('A'),topic('B'),topic('C'),topic('D')],[],[],{},'2026-10-15',p)
    before=repr(states)
    calendar=forecast_calendar(states,p,'2026-10-15',35,[],{})
    assert len(calendar)==35
    assert calendar[0]['date']=='2026-10-15'
    assert calendar[-1]['date']=='2026-11-18'
    assert all(sum(i['questions'] for i in d['items'])<=20 for d in calendar)
    assert {i['topic_id'] for i in calendar[0]['items']}!={i['topic_id'] for i in calendar[1]['items']}
    assert repr(states)==before
    assert all('fake_correct' not in d for d in calendar)


def test_calendar_respects_future_rest_and_daily_quantity_override():
    p=AdaptiveProfile(max_questions=20)
    states=topic_states([topic('A'),topic('B')],[],[],{},'2026-10-15',p)
    settings={'2026-10-16':{'questions':40,'kind':'descanso','extra_topics':[]},'2026-10-17':{'questions':30,'kind':'normal','extra_topics':[]}}
    result=forecast_calendar(states,p,'2026-10-15',3,[],settings)
    assert result[1]['items']==[] and result[1]['kind']=='descanso'
    assert result[2]['target_questions']==30


def test_pending_queue_is_planned_on_its_seven_day_return_without_fake_success():
    p=AdaptiveProfile(max_questions=20)
    states=topic_states([topic('A')],[],[],{},'2026-10-15',p)
    states[0]['next_review']='2026-10-16'
    states[0]['pending_reviews']=[{'session_id':'pending','questions':4,'due_date':'2026-10-22','path':['Área','A']}]
    forecast=forecast_calendar(states,p,'2026-10-15',9,[],{})
    due=next(d for d in forecast if d['date']=='2026-10-22')
    assert any(i['topic_id']=='A' for i in due['items'])
    assert due['pending_planned']==4
