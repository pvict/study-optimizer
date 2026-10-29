"""Controle conservador de admissões: não simula melhora nem alonga intervalos."""
from dataclasses import replace
from datetime import timedelta
from math import ceil
from .planning import _date
from .study_allocation import topic_is_new,practice_minimum
from .review_policy import review_order

HORIZON=14


def capacity_limits(profile,day,settings,agenda):
    from .study_replanning import effective_routine
    result=[]
    for offset in range(HORIZON):
        key=(_date(day)+timedelta(days=offset)).isoformat()
        config=settings.get(key,{'questions':profile.max_questions,'kind':'normal','extra_topics':[]})
        from .final_review import special_config
        config=special_config(config,agenda.get('overrides',{}).get(key,{}))
        _,q=effective_routine(profile,config,agenda.get('overrides',{}).get(key,{}))
        rest=config['kind']=='descanso' or key>profile.exam_date
        result.append((0,0) if rest else (q,profile.max_topics))
    return result


def practice_state(state,day,profile):
    q=state.get('theme_recommended_questions',state['recommended_questions'])
    due=sum(lot['questions'] for lot in state.get('pending_reviews',[]) if lot['due_date']<=day)
    theme_due=state.get('theme_review_due',state.get('next_review'))
    only_lot=bool(due and (not theme_due or theme_due>day))
    if profile.review_strategy=='balanced_v2':
        representative=state.get('representative_today',0) if state.get('activity_day')==day else 0
        credits=sum(c['questions'] for c in state.get('coordinated_credits',[]) if theme_due and c['date']<=day and
                    abs((_date(c['date'])-_date(theme_due)).days)<=2 and (_date(day)-_date(theme_due)).days<=2)
        done=representative+credits
        if only_lot: q=min(state['total'],due)
        elif theme_due and theme_due<=day:
            q=min(state['total'],max(0,q-done,due))
        return {'recommended_questions':q,'review_kind':'lot_only' if only_lot or due and q<=due else 'combined' if due else 'theme',
                'allow_small_lot':bool(due or credits),'lot_questions':due,
                'representative_needed':max(0,q-due)}
    if only_lot: q=min(state['total'],max(profile.min_block,due))
    elif due: q=max(q,min(state['total'],due))
    return {'recommended_questions':q,'review_kind':'lot_only' if only_lot else 'theme'}


def capacity_policy(states,profile,day,budget,target,limits=None,*,eligible_ids=None,allocated_questions=None,available_slots=None):
    meta={'mode':profile.workload_mode,'reference_share':profile.new_share,'effective_share':profile.new_share,
          'deferred_admissions':0,'horizon_days':HORIZON,'protected_intake_topic':None,'intake_future_pressure':False}
    if profile.workload_mode!='adaptive' or budget<=0: return states,profile,meta
    states=sorted(states,key=lambda t:review_order(t,day))
    allocated_questions=allocated_questions or {}
    available_slots=profile.max_topics if available_slots is None else available_slots
    start=_date(day)
    limits=limits or [(target,profile.max_topics)]*HORIZON
    loads=[0]*HORIZON; slots=[0]*HORIZON
    def dose(t): return min(t['total'],max(profile.min_block,t.get('recommended_questions',profile.min_block)))
    def occurrences(t,initial=False):
        interval=max(1,t.get('review_interval_days',7))
        due=start if initial else max(start,_date(t.get('next_review') or day))
        offset=(due-start).days
        return list(range(offset,HORIZON,interval)) if offset<HORIZON else []
    for t in states:
        if not t.get('review_committed',True) or not t.get('next_review'): continue
        per_day={}
        theme_due=t.get('theme_review_due',t.get('next_review'))
        if theme_due:
            for i in occurrences({**t,'next_review':theme_due}): per_day[i]=min(t['total'],t.get('theme_recommended_questions',dose(t)))
        lots_by_day={}
        for lot in t.get('pending_reviews',[]):
            i=max(0,(_date(lot['due_date'])-start).days)
            if i<HORIZON: lots_by_day[i]=lots_by_day.get(i,0)+lot['questions']
        for i,q in lots_by_day.items():
            amount=max(per_day.get(i,0),q) if profile.review_strategy=='balanced_v2' else max(profile.min_block,q)
            per_day[i]=max(per_day.get(i,0),min(t['total'],amount))
        if 0 in per_day:
            per_day[0]=max(0,per_day[0]-allocated_questions.get(t['topic_id'],0))
        for i,q in per_day.items():
            if q:loads[i]+=q;slots[i]+=1
    # A proporção de referência cede espaço à revisão devida; 0% e100% fixos seguem no modo fixo.
    meta['due_questions']=loads[0]
    admitted=set()
    def expired(t):
        deadline=t.get('initial_contact_deadline')
        return bool(not t.get('review_committed',True) and not topic_is_new(t) and
                    (deadline and deadline<=day or t.get('reported_difficulty')))
    def admit(t,left,protect=False):
        if t['topic_id'] in admitted or t.get('review_committed',True): return 0
        if eligible_ids is not None and t['topic_id'] not in eligible_ids:return 0
        due=t.get('allocation_due',t.get('next_review'))
        if due and due>day:return 0
        q=min(dose(t),left)
        if q<practice_minimum(t,profile.min_block) or slots[0]>=available_slots or loads[0]+q>min(budget,limits[0][0]):return 0
        offsets=occurrences(t,True)
        future_pressure=any(loads[i]+(q if i==0 else dose(t))>limits[i][0] or slots[i]>=limits[i][1] for i in offsets)
        if future_pressure and not protect:return 0
        if future_pressure:meta['intake_future_pressure']=True
        admitted.add(t['topic_id'])
        for i in offsets:loads[i]+=q if i==0 else dose(t);slots[i]+=1
        return q
    # Uma retomada antiga não pode ficar bloqueada para sempre por repetições
    # hipotéticas. Compromissos reais e capacidade de hoje já foram descontados.
    for t in states:
        if expired(t):
            if admit(t,max(0,budget-loads[0]),protect=True):
                meta['protected_intake_topic']=t['topic_id'];break
    waiting=[t for t in states if expired(t) and (eligible_ids is None or t['topic_id'] in eligible_ids)]
    waiting_questions=sum(dose(t) for t in waiting)
    demand=ceil(waiting_questions/max(1,profile.max_contact_gap))
    reference_new=round(target*profile.new_share)
    exploration=min(reference_new,max(profile.min_block,round(target*profile.parameters.exploration_reserve))) if reference_new else 0
    review_reserve=min(max(0,budget-loads[0]-exploration),demand)
    new_questions=min(reference_new,max(0,budget-loads[0]-review_reserve))
    if slots[0]>=available_slots:new_questions=0
    meta.update(initial_waiting_questions=waiting_questions,initial_recovery_demand=demand,
                initial_capacity_shortfall=demand+meta['due_questions']>budget)
    effective=replace(profile,new_share=new_questions/max(1,target))
    meta['effective_share']=effective.new_share
    quota=[new_questions,max(0,budget-new_questions-loads[0])]
    for group in (0,1):
        left=quota[group]
        for t in states:
            if topic_is_new(t)==(group==0):left-=admit(t,left,protect=expired(t))
    # Mesma cessão de sobra já usada no alocador: uma quota sem candidatos
    # não deixa vagas ociosas enquanto outros temas aguardam admissão.
    if 0<profile.new_share<1:
        left=max(0,budget-loads[0])
        for t in states:left-=admit(t,left,protect=expired(t))
    kept=[t for t in states if t.get('review_committed',True) or t['topic_id'] in admitted or t.get('manual_adverse')]
    kept_ids={t['topic_id'] for t in kept}
    meta['deferred_admissions']=sum(not t.get('review_committed',True) and t['topic_id'] not in kept_ids and
                                    (not t.get('next_review') or t['next_review']<=day) for t in states)
    meta['slot_pressure']=any(slots[i]>limits[i][1] for i in range(HORIZON))
    return kept,effective,meta
