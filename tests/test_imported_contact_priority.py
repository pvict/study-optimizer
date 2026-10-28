"""Histórico importado não pode ficar meses atrás da mesma fila de diagnóstico."""
from copy import deepcopy

from osler.adaptive_planning import topic_states,allocate_day
from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile
from test_initial_review_policy import imported


def crowded_initial_pool():
    topics=[imported('high',86.1,'2026-10-02',36)]
    topics += [imported('weak'+str(i),20,'2026-10-20',30) for i in range(60)]
    data=[{'id':1,'institutions':['X'],'unit':'questoes','observed_date':'2026-10-20',
           'rows':[{'path':t['path'],'value':36 if t['topic_id']=='high' else 15} for t in topics]}]
    p=AdaptiveProfile(max_questions=60,max_topics=2,new_share=.5,workload_mode='adaptive',
                      review_strategy='balanced_v2',max_contact_gap=30,start_date='2026-10-22')
    return topic_states(topics,[],data,{},'2026-10-28',p),p


def test_imported_high_incidence_gets_a_slot_when_known_contact_reaches_maximum_gap():
    states,p=crowded_initial_pool();before=deepcopy(states)
    # Antes do limite, os erros importantes continuam à frente do tema mais seguro.
    initial=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=60)
    assert 'high' not in {i['topic_id'] for i in initial['items']}
    settings={'2026-11-01':{'questions':60,'kind':'descanso','extra_topics':[]}}
    days=forecast_calendar(states,p,'2026-10-28',12,[],settings,next_contact_only=True)
    contacts=[d['date'] for d in days for i in d['items'] if i['topic_id']=='high']
    # 02/10 + 30 dias = 01/11, descanso: encaixe real no dia útil seguinte.
    assert contacts==['2026-11-02']
    assert all(d['questions']<=60 and len(d['items'])<=2 for d in days)
    assert not next(d for d in days if d['date']=='2026-11-01')['items']
    assert states==before
    assert all(t['performance']['exact_n']==0 and not t['review_committed'] for t in states)
    assert all(d['topic_backlog']==0 for d in days)


def test_overdue_imported_contact_uses_incidence_without_inventing_dates_for_pdf_only():
    from test_adaptive_planning import topic
    topics=[imported('important',90,'2026-09-01',50),imported('less',60,'2026-09-01',50),topic('unknown',answered=50)]
    data=[{'id':1,'institutions':['X'],'unit':'questoes','observed_date':'2026-10-20',
           'rows':[{'path':t['path'],'value':v} for t,v in zip(topics,[36,15,1])]}]
    p=AdaptiveProfile(max_questions=60,max_topics=1,new_share=0,workload_mode='adaptive',review_strategy='balanced_v2')
    states=topic_states(topics,[],data,{},'2026-10-28',p)
    plan=allocate_day(states,p,None,'normal',[],'2026-10-28',question_target=60)
    assert [i['topic_id'] for i in plan['items']]==['important']
    unknown=next(t for t in states if t['topic_id']=='unknown')
    assert unknown['last_contact'] is None
    assert unknown.get('initial_contact_deadline') is None


def test_known_return_and_explicit_rebooking_still_precede_initial_contacts():
    states,p=crowded_initial_pool()
    committed=deepcopy(states[-1]);committed.update(topic_id='committed',path=['Área','committed'],
        review_committed=True,next_review='2026-11-01',theme_review_due='2026-11-01',
        recommended_questions=20,theme_recommended_questions=20)
    states.append(committed)
    # O compromisso real conserva a primeira vaga; o histórico usa a outra.
    plan=allocate_day(states,p,None,'normal',[],'2026-11-02',question_target=60)
    ids=[i['topic_id'] for i in plan['items']]
    assert ids==['committed','high']
    reservation={'topic_id':'weak0','date':'2026-11-02','original_due':'2026-10-28','remaining':20,'questions':20}
    plan=allocate_day(states,p,None,'normal',[],'2026-11-02',question_target=60,reservations=[reservation])
    assert plan['items'][0]['topic_id']=='weak0' and plan['items'][0]['rescheduled']


def test_preventive_contact_does_not_disable_aging_for_other_imported_topics():
    from osler.study_prevention import preventive_state
    states,p=crowded_initial_pool()
    preventive=deepcopy(states[-1]);preventive.update(topic_id='preventive',path=['Área','preventive'],
        review_committed=True,next_review='2026-11-03',theme_review_due='2026-11-03',
        review_interval_days=7,recommended_questions=20,theme_recommended_questions=20,
        priority='alta',evidence_priority='alta')
    policy={'start':'2026-11-02','end':'2026-11-03','topics':['preventive']}
    active=[preventive_state(t,'2026-11-02',[policy]) for t in [*states,preventive]]
    plan=allocate_day(active,p,None,'normal',[],'2026-11-02',question_target=60)
    assert [i['topic_id'] for i in plan['items']]==['preventive','high']
