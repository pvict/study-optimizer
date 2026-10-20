from copy import deepcopy
from dataclasses import replace
from osler.adaptive_planning import topic_states
from osler.study_models import AdaptiveProfile
from osler.study_calendar import forecast_calendar
from osler.study_replanning import collect_backlog
from test_adaptive_planning import topic,session


def imported(name='A',rate=95,contact='2026-09-01',n=50):
    return {**topic(name,answered=n),'planner_snapshot':{'observed_date':'2026-10-15','unique_questions':n,
        'available_questions':100,'confident_accuracy_pct':rate,'pending_reviews':0,'last_contact':contact,'dataset_id':1}}


def test_imported_history_is_a_ranked_pool_not_hundreds_of_overdue_appointments():
    p=AdaptiveProfile(max_questions=40,max_topics=2,new_share=0,start_date='2026-10-15')
    states=topic_states([imported(str(i)) for i in range(100)],[],[],{},'2026-10-15',p)
    before=deepcopy(states)
    calendar=forecast_calendar(states,p,'2026-10-15',7,[],{})
    assert calendar[0]['topic_backlog']==0
    assert all(d['questions']<=40 for d in calendar)
    assert calendar[0]['initial_topics_waiting']>=98
    assert sum(t['priority'] in {'alta','urgente'} for t in states)<=14
    assert len({i['topic_id'] for d in calendar for i in d['items']})>2
    assert not collect_backlog(states,[],[],'2026-10-16',start_date=p.start_date)
    assert states==before


def test_safety_exposure_and_incidence_change_initial_interval_not_first_attempt_posterior():
    p=AdaptiveProfile()
    states=topic_states([imported('weak',45),imported('strong',95),imported('small',100,n=2)],[],[],{},'2026-10-15',p)
    by={s['topic_id']:s for s in states}
    assert by['strong']['review_interval_days']>by['weak']['review_interval_days']
    assert by['weak']['recommended_questions']>by['strong']['recommended_questions']
    assert by['small']['review_interval_days']<=by['strong']['review_interval_days']
    assert all(s['performance']['exact_n']==0 and s['confidence']['exact_n']==0 for s in states)
    assert not by['strong']['review_committed']
    assert by['strong']['domain_evidence']=='Segurança alta na Osler'
    assert by['strong']['priority']!='urgente'


def test_high_incidence_learning_gap_beats_old_low_incidence_safe_topic():
    topics=[imported('important',50,'2026-10-10'),imported('old',99,'2026-01-01')]
    datasets=[{'id':1,'institutions':['A'],'unit':'questoes','observed_date':'2026-10-15',
        'rows':[{'path':t['path'],'value':v,'band':'alta'} for t,v in zip(topics,[100,1])]}]
    states=topic_states(topics,[],datasets,{'A':1},'2026-10-15',AdaptiveProfile())
    assert states[0]['topic_id']=='important'
    assert states[0]['score']>states[1]['score']


def test_real_committed_review_and_actual_missed_plan_remain_visible():
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0)
    states=topic_states([imported('A'),imported('B')],[],[],{},'2026-10-15',p)
    for t in states: t.update(review_committed=True,next_review='2026-10-15',review_interval_days=7)
    calendar=forecast_calendar(states,p,'2026-10-15',1,[],{})
    assert calendar[0]['topic_backlog']==1
    uncommitted=topic_states([imported()],[],[],{},'2026-10-15',p)
    saved=[{'plan':{'date':'2026-10-15','items':[{'path':uncommitted[0]['path'],'questions':20}]}}]
    assert collect_backlog(uncommitted,[],saved,'2026-10-16')[0]['missed_questions']==20


def test_recorded_block_creates_a_real_review_obligation():
    entries=[session(day='2026-10-14',n=20,correct=10)]
    states=topic_states([imported('Tema')],entries,[],{},'2026-10-15',AdaptiveProfile())
    assert states[0]['review_committed']


def test_expired_or_superseded_safety_cannot_shrink_dose_or_claim_high_safety():
    old=imported('Tema',99)
    old['planner_snapshot']['observed_date']='2026-01-01'
    state=topic_states([old],[],[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['review_interval_days']<=7
    assert state['recommended_questions']>=20
    assert state['domain_evidence']=='Medição pendente'
    assert state['performance']['exact_n']==0
    old['planner_snapshot']['observed_date']='2026-10-10'
    state=topic_states([old],[session(day='2026-10-14',n=50,correct=25)],[],{},'2026-10-15',
                       AdaptiveProfile(start_date='2026-10-15'))[0]
    assert state['low_accuracy']
    without_snapshot=deepcopy(old)
    without_snapshot.pop('planner_snapshot')
    control=topic_states([without_snapshot],[session(day='2026-10-14',n=50,correct=25)],[],{},'2026-10-15',
                         AdaptiveProfile(start_date='2026-10-15'))[0]
    assert state['recommended_questions']==control['recommended_questions']
    assert state['recommended_questions']>12


def test_manual_critical_errors_keep_alert_and_precede_initial_safe_pool():
    topics=[imported(str(i)) for i in range(30)]
    topics[-1]['manual_context']={'erros_criticos':True}
    states=topic_states(topics,[],[],{},'2026-10-15',AdaptiveProfile(max_topics=1,new_share=0))
    flagged=next(t for t in states if t['topic_id']=='29')
    assert flagged['priority']=='urgente'
    assert flagged['learning_state']=='alerta'
    assert flagged['domain_evidence']=='Reforçar segurança'
    assert 'críticos' in flagged['reason']
    assert states[0]['topic_id']=='29'


def test_policy_version_invalidates_cached_planning_token(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from osler.study_agenda import StudyAgenda
    from osler import review_policy
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    agenda=StudyAgenda(repo)
    before=agenda.token()
    monkeypatch.setattr(review_policy,'POLICY_VERSION','future')
    assert agenda.token()!=before
