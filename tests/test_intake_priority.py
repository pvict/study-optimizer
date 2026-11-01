from copy import deepcopy
from osler.adaptive_planning import topic_states,allocate_day
from osler.review_policy import review_order
from osler.study_models import AdaptiveProfile
from osler.study_capacity import capacity_policy
from test_initial_review_policy import imported
from test_adaptive_planning import session


def test_weekly_focus_never_erases_strong_adverse_evidence():
    topics=[imported(str(i),40,'2026-09-22') for i in range(40)]
    p=AdaptiveProfile(max_topics=1,new_share=.5,start_date='2026-10-22')
    states=topic_states(topics,[],[],{},'2026-10-28',p)
    outside=[t for t in states if not t['initial_focus']]
    assert outside and all(t['priority']=='urgente' for t in outside)


def test_waiting_beyond_deadline_continues_increasing_priority():
    states=topic_states([imported('waiting',95,'2026-09-22')],[],[],{},'2026-10-28',AdaptiveProfile())
    t=states[0];before=deepcopy(t)
    assert review_order(t,'2026-12-28')<review_order(t,'2026-10-28')
    assert t==before


def test_current_capacity_protects_one_old_contact_despite_hypothetical_future_pressure():
    p=AdaptiveProfile(max_questions=40,max_topics=2,new_share=.5,workload_mode='adaptive')
    states=topic_states([imported('old',57,'2026-09-22'),imported('new',n=0,contact=None)],[],[],{},'2026-10-28',p)
    limits=[(40,2)]*14;limits[7]=(0,0)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=40,capacity_limits=limits)
    assert 'old' in {i['topic_id'] for i in plan['items']}
    assert plan['capacity']['intake_future_pressure']
    assert plan['questions']<=40 and len(plan['items'])<=2
    assert all(not t['review_committed'] for t in states)


def test_protected_intake_never_displaces_full_real_commitment_or_rest():
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=.5,workload_mode='adaptive')
    states=topic_states([imported('old',57),imported('real',57)],[],[],{},'2026-10-28',p)
    real=next(t for t in states if t['topic_id']=='real')
    real.update(review_committed=True,next_review='2026-10-28',theme_review_due='2026-10-28',recommended_questions=20,theme_recommended_questions=20)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=20)
    assert [i['topic_id'] for i in plan['items']]==['real']
    assert allocate_day(states,p,None,'descanso',[],'2026-10-28',question_target=20)['questions']==0


def test_fixed_new_only_does_not_silently_change_user_quota():
    p=AdaptiveProfile(max_questions=40,max_topics=2,new_share=1,workload_mode='fixed')
    states=topic_states([imported('old',57),imported('new',n=0,contact=None)],[],[],{},'2026-10-28',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=40)
    assert 'old' not in {i['topic_id'] for i in plan['items']}


def test_qualitative_difficulty_is_current_signal_without_fabricated_accuracy():
    topic=imported('reported',95,'2026-09-22')
    topic['manual_context']={'dificuldade':'alta','data_observacao':'2026-10-28'}
    p=AdaptiveProfile(review_strategy='balanced_v2')
    state=topic_states([topic],[],[],{},'2026-10-28',p)[0]
    assert state['reported_difficulty'] and state['learning_state']=='alerta'
    assert state['performance']['exact_n']==0 and state['performance']['observed'] is None
    assert state['review_interval_days']<=7
    assert not state['manual_adverse']


def test_new_measured_block_supersedes_qualitative_difficulty():
    topic=imported('Tema',95,'2026-09-22')
    topic['manual_context']={'dificuldade':'alta','data_observacao':'2026-10-15'}
    p=AdaptiveProfile(review_strategy='balanced_v2')
    state=topic_states([topic],[session(day='2026-10-20',n=20,correct=19)],[],{},'2026-10-28',p)[0]
    assert not state['reported_difficulty']
    assert state['performance']['exact_n']==20


def test_only_currently_eligible_topics_can_consume_admission_capacity():
    p=AdaptiveProfile(max_questions=20,max_topics=1,workload_mode='adaptive')
    states=topic_states([imported('old',57),imported('active',57)],[],[],{},'2026-10-28',p)
    kept,_,meta=capacity_policy(states,p,'2026-10-28',20,20,eligible_ids={'active'})
    assert {t['topic_id'] for t in kept}=={'active'}
    assert meta['protected_intake_topic']=='active'


def test_old_initial_pool_changes_adaptive_share_without_exceeding_capacity():
    p=AdaptiveProfile(max_questions=120,max_topics=6,new_share=.5,workload_mode='adaptive')
    topics=[imported(str(i),57,'2026-09-01') for i in range(100)]+[imported('new',n=0,contact=None)]
    states=topic_states(topics,[],[],{},'2026-10-28',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=120)
    assert plan['capacity']['effective_share']<.5
    assert sum(not t['is_new_for_day'] for t in plan['items'])>=4
    assert plan['questions']<=120 and len(plan['items'])<=6
    assert p.new_share==.5


def test_reported_difficulty_is_not_a_reason_to_suspend_cards():
    from osler.reduction_recommendations import current_recommendations
    t=imported('reported',95,'2026-10-15')
    t['manual_context']={'dificuldade':'alta','data_observacao':'2026-10-28'}
    states=topic_states([t],[],[],{},'2026-10-28',AdaptiveProfile(review_strategy='balanced_v2'))
    result=current_recommendations(states,[],'2026-10-28')
    assert len(result['protected'])==1
    assert any('dificuldade' in reason.casefold() for reason in result['protected'][0]['reasons'])


def test_contact_and_qualitative_observation_reach_planner_without_new_attempts(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    from osler.observations import Observation
    from osler.adaptive_service import AdaptiveService
    from osler.study_models import StudyEntry
    repo,assessment,matching,row=setup_assessment(tmp_path,sample_pdf)
    assessment.save_observation(matching,row.row_id,Observation('2026-10-15','Relato do usuario','informado_usuario',dificuldade='alta'),0)
    service=AdaptiveService(repo)
    service.save_entry(StudyEntry(row.qbank.path,'2026-10-15',kind='contato',source='Contato relatado, sem contagens'),'contact-report')
    state=next(t for t in service.overview('2026-10-15')['states'] if t['path']==row.qbank.path)
    assert state['reported_difficulty'] and state['last_contact']=='2026-10-15'
    assert state['performance']['exact_n']==0 and state['recorded_attempts']==0


def test_reserved_commitment_is_not_charged_twice_against_intake_budget():
    p=AdaptiveProfile(max_questions=60,max_topics=3,new_share=0,workload_mode='adaptive')
    states=topic_states([imported('old',57),imported('real',57)],[],[],{},'2026-10-28',p)
    real=next(t for t in states if t['topic_id']=='real')
    real.update(review_committed=True,next_review='2026-10-28',theme_review_due='2026-10-28',recommended_questions=40,theme_recommended_questions=40)
    reservation={'topic_id':'real','date':'2026-10-28','remaining':40,'original_due':'2026-10-28','daily_proposal':True}
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=60,reservations=[reservation])
    assert [(i['topic_id'],i['questions']) for i in plan['items']]==[('real',40),('old',20)]


def test_future_rebooking_cannot_steal_todays_protected_slot():
    p=AdaptiveProfile(max_questions=20,max_topics=1,new_share=0,workload_mode='adaptive')
    states=topic_states([imported('A',57),imported('B',57)],[],[],{},'2026-10-28',p)
    next(t for t in states if t['topic_id']=='A')['reschedule_date']='2026-10-29'
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=20)
    assert [i['topic_id'] for i in plan['items']]==['B']


def test_new_floor_preserves_coverage_instead_of_initial_backlog_taking_last_slot():
    p=AdaptiveProfile(max_questions=60,max_topics=2,new_share=.5,workload_mode='adaptive')
    states=topic_states([imported('old',57),imported('real',57),imported('new',n=0,contact=None)],[],[],{},'2026-10-28',p)
    real=next(t for t in states if t['topic_id']=='real')
    real.update(review_committed=True,next_review='2026-10-28',theme_review_due='2026-10-28',recommended_questions=30,theme_recommended_questions=30)
    old=next(t for t in states if t['topic_id']=='old');old.update(recommended_questions=10,theme_recommended_questions=10)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=60)
    assert {i['topic_id'] for i in plan['items']}=={'real','new'}
