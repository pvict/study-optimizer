"""Controle conservador de admissões: não simula melhora nem alonga intervalos."""
from dataclasses import replace
from datetime import timedelta
from .planning import _date
from .study_allocation import topic_is_new

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
    if only_lot: q=min(state['total'],max(profile.min_block,due))
    elif due: q=max(q,min(state['total'],due))
    return {'recommended_questions':q,'review_kind':'lot_only' if only_lot else 'theme'}


def capacity_policy(states,profile,day,budget,target,limits=None):
    meta={'mode':profile.workload_mode,'reference_share':profile.new_share,'effective_share':profile.new_share,
          'deferred_admissions':0,'horizon_days':HORIZON}
    if profile.workload_mode!='adaptive' or budget<=0: return states,profile,meta
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
        for i,q in lots_by_day.items(): per_day[i]=max(per_day.get(i,0),min(t['total'],max(profile.min_block,q)))
        for i,q in per_day.items(): loads[i]+=q; slots[i]+=1
    # A proporção de referência cede espaço à revisão devida; 0% e100% fixos seguem no modo fixo.
    new_questions=min(round(target*profile.new_share),max(0,budget-loads[0]))
    meta['due_questions']=loads[0]
    effective=replace(profile,new_share=new_questions/max(1,target))
    meta['effective_share']=effective.new_share
    quota=[new_questions,max(0,budget-new_questions-loads[0])]
    admitted=set()
    for group in (0,1):
        left=quota[group]
        for t in states:
            if t.get('review_committed',True) or topic_is_new(t)!=(group==0): continue
            due=t.get('allocation_due',t.get('next_review'))
            if due and due>day: continue
            q=min(dose(t),left)
            if q<profile.min_block or slots[0]>=profile.max_topics: continue
            offsets=occurrences(t,True)
            if any(loads[i]+(q if i==0 else dose(t))>limits[i][0] or slots[i]>=limits[i][1] for i in offsets): continue
            admitted.add(t['topic_id']); left-=q
            for i in offsets: loads[i]+=q if i==0 else dose(t); slots[i]+=1
    kept=[t for t in states if t.get('review_committed',True) or t['topic_id'] in admitted or t.get('manual_adverse')]
    kept_ids={t['topic_id'] for t in kept}
    meta['deferred_admissions']=sum(not t.get('review_committed',True) and t['topic_id'] not in kept_ids and
                                    (not t.get('next_review') or t['next_review']<=day) for t in states)
    meta['slot_pressure']=any(slots[i]>limits[i][1] for i in range(HORIZON))
    return kept,effective,meta
