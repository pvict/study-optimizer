from copy import deepcopy
from osler.adaptive_planning import topic_states, allocate_day
from osler.study_models import AdaptiveProfile
from osler.topic_catalog import planning_frontier
from osler.topic_spacing import spacing_state
from test_adaptive_planning import topic, session


def test_specific_frontier_keeps_tiny_topics_without_broad_replacement():
    tiny={**topic('Tiny',total=1),'path':['Area','Group','Tiny'],'is_leaf':True}
    leaf={**topic('Leaf'),'path':['Area','Group','Leaf'],'is_leaf':True}
    parent={**topic('Group'),'path':['Area','Group'],'is_leaf':False}
    assert {t['topic_id'] for t in planning_frontier([parent,tiny,leaf])}=={'Tiny','Leaf'}


def test_incidence_changes_interval_and_dose_without_changing_actual_performance():
    a,b=topic('A'),topic('B')
    events=[]
    for t in [a,b]:
        e=session(day='2026-10-10',n=20,correct=18)
        e['entry'].update(path=t['path'],confident_correct=18)
        events.append(e)
    data=[{'id':1,'institutions':['X'],'observed_date':'2026-10-15','unit':'questoes','rows':[{'path':a['path'],'value':90},{'path':b['path'],'value':10}]}]
    states={t['topic_id']:t for t in topic_states([a,b],events,data,{},'2026-10-15',AdaptiveProfile())}
    assert states['A']['review_interval_days']<states['B']['review_interval_days']
    assert states['A']['recommended_questions']>states['B']['recommended_questions']
    assert states['A']['confidence']['exact_n']==states['B']['confidence']['exact_n']==20


def test_one_day_or_tiny_followups_do_not_prove_spaced_relearning():
    e=session(day='2026-10-01',n=20,correct=20)['entry']
    e['confident_correct']=20
    early={**e,'day':'2026-10-02'}
    tiny={**e,'day':'2026-10-03','questions':1,'correct':1,'confident_correct':1}
    result=spacing_state([e,early,tiny],AdaptiveProfile(),'2026-10-15')
    assert result['streak']==1
    assert result['last_evidence_day']=='2026-10-01'


def test_trajectory_keeps_followups_conditional_and_distinguishes_capacity():
    from osler.topic_trajectory import topic_trajectory, trajectory_summary
    p=AdaptiveProfile(exam_date='2026-12-01',max_questions=20,max_topics=1)
    states=topic_states([topic('A'),topic('Tiny',total=1)],[],[],{},'2026-10-15',p)
    before=deepcopy(states)
    state=next(t for t in states if t['topic_id']=='A')
    roadmap=topic_trajectory(state,p,'2026-10-15')
    assert roadmap['steps'][0]['stage']=='Primeiro contato'
    assert roadmap['steps'][1]['stage']=='Revisão 1'
    assert len(roadmap['steps'])==5
    assert roadmap['recommended_total'] is None
    assert roadmap['steps'][0]['date']<=p.exam_date
    assert all(s['questions'] is None and s['date'] is None for s in roadmap['steps'][1:])
    tiny=topic_trajectory(next(t for t in states if t['topic_id']=='Tiny'),p,'2026-10-15')
    assert tiny['available_per_block']==1 and tiny['complement_per_block']>=9
    summary=trajectory_summary(states,p,'2026-10-15',[])
    assert summary['scheduled_questions']==0 and summary['unscheduled_topics']==2
    assert states==before


def test_automatic_blocks_are_useful_and_respect_bank_and_daily_goal():
    p=AdaptiveProfile(max_questions=120,max_topics=5)
    states=topic_states([topic(str(i)) for i in range(8)],[],[],{},'2026-10-15',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=120)
    assert all(10<=i['questions']<=i['total'] and i['recommended_questions']>=10 for i in plan['items'])
    assert plan['questions']==120


def test_actual_first_block_today_makes_future_contact_review_one():
    from osler.topic_trajectory import topic_trajectory
    from osler.study_calendar import forecast_calendar
    p=AdaptiveProfile(max_questions=20)
    e=session(n=20,correct=20)
    e['entry']['confident_correct']=20
    state=topic_states([topic()],[e],[],{},'2026-10-15',p)[0]
    roadmap=topic_trajectory(state,p,'2026-10-15')
    assert roadmap['steps'][0]['stage']=='Revisão 1'
    plans=forecast_calendar([state],p,'2026-10-15',10,[e],{})
    future=[i for d in plans[1:] for i in d['items']]
    assert future[0]['stage']=='Revisão 1'


def test_far_future_exam_trajectory_is_bounded_like_calendar():
    from osler.topic_trajectory import topic_trajectory
    from datetime import date
    p=AdaptiveProfile(exam_date='2035-12-01')
    state=topic_states([topic()],[],[],{},'2026-10-15',p)[0]
    roadmap=topic_trajectory(state,p,'2026-10-15')
    assert (date.fromisoformat(roadmap['horizon_end'])-date(2026,10,15)).days<=547
    assert roadmap['horizon_end']<p.exam_date


def test_automatic_day_waits_until_due_but_explicit_extra_can_advance_review():
    from osler.study_calendar import forecast_calendar
    p=AdaptiveProfile(max_questions=20)
    e=session(day='2026-10-14',n=20,correct=20)
    e['entry']['confident_correct']=20
    states=topic_states([topic()],[e],[],{},'2026-10-15',p)
    assert states[0]['next_review']=='2026-10-21'
    plan=allocate_day(states,p,None,'normal',[e],'2026-10-15',question_target=20)
    assert plan['items']==[]
    forecast=forecast_calendar(states,p,'2026-10-15',8,[e],{})
    assert all(not d['items'] for d in forecast if d['date']<'2026-10-21')
    assert forecast[6]['items'][0]['stage']=='Revisão 1'
    extra={**states[0],'extra_id':'explicit','requested':10,'after_event_id':0}
    advanced=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=20,extra_topics=[extra])
    assert advanced['items'][0]['added_by_user'] and advanced['items'][0]['questions']==10


def test_initial_dose_chooses_fewer_topics_instead_of_shrinking_every_block():
    p=AdaptiveProfile(max_questions=60,max_topics=4)
    states=topic_states([topic(str(i)) for i in range(4)],[],[],{},'2026-10-15',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-15',question_target=60)
    assert len(plan['items'])==3
    assert all(i['questions']>=i['recommended_questions'] for i in plan['items'])


def test_confident_repeated_reviews_can_expand_interval_without_novel_denominator():
    events=[]
    for day in ['2026-10-01','2026-10-10']:
        e=session(day=day,mode='repetidas',n=20,correct=20)
        e['entry']['confident_correct']=20
        events.append(e)
    state=topic_states([topic()],events,[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['review_interval_days']==14
    assert state['performance']['exact_n']==0
    assert state['confidence']['exact_n']==40
