"""Cotas por questões em temas novos/revisões, com limites e desvio explícitos."""
from .models import normalize_path


def topic_is_new(t):
    return t.get('is_new_for_day',t['status']=='sem_registro')


def practice_minimum(topic,minimum):
    """Acervo pequeno positivo é uma exceção ao piso, não motivo para excluir o tema."""
    return min(minimum,topic['total'])


def practice_capacity(topic,profile):
    if profile.review_strategy=='balanced_v2' and topic_is_new(topic) and topic['total']<profile.min_block and topic.get('review_kind')!='lot_only':
        return max(topic['total'],topic.get('recommended_questions',topic['total']))
    return topic['total']


def _fill(selected,counts,target,capped=False):
    while sum(counts.get(t['topic_id'],0) for t in selected)<target:
        candidates=[t for t in selected if counts.get(t['topic_id'],0)<min(t['allocation_capacity'],t.get('recommended_questions',t['allocation_capacity']))] if capped else [t for t in selected if counts.get(t['topic_id'],0)<t['allocation_capacity']]
        if not candidates: break
        chosen=max(candidates,key=lambda t:t['score']/(counts.get(t['topic_id'],0)+1))
        counts[chosen['topic_id']]=counts.get(chosen['topic_id'],0)+1


def category_allocation(available,states,profile,budget,day_target,today):
    by_path={tuple(normalize_path(t['path'])):t for t in states} if today else {}
    done_new=done_reviews=unknown=0
    for e in today:
        t=by_path.get(tuple(normalize_path(e['path'])))
        if not t: unknown+=e['questions']
        elif topic_is_new(t): done_new+=e['questions']
        else: done_reviews+=e['questions']
    new_target=round(day_target*profile.new_share)
    want_new=max(0,new_target-done_new-round(unknown*profile.new_share))
    want_reviews=max(0,day_target-new_target-done_reviews-(unknown-round(unknown*profile.new_share)))
    if want_new+want_reviews>budget:
        n=round(budget*want_new/(want_new+want_reviews))
        want_new,want_reviews=n,budget-n
    elif want_new+want_reviews<budget:
        spare=budget-want_new-want_reviews
        want_new+=round(spare*profile.new_share)
        want_reviews=budget-want_new
    pools=[[t for t in available if topic_is_new(t)],[t for t in available if not topic_is_new(t)]]
    balanced=profile.review_strategy=='balanced_v2'
    minimum=profile.min_block if balanced else min(profile.min_block,budget)
    def floor(t):
        bank_floor=practice_minimum(t,minimum)
        return min(bank_floor,t.get('lot_questions',bank_floor),t.get('recommended_questions',bank_floor)) if t.get('allow_small_lot') else bank_floor
    def sized(t,limit):
        q=min(t.get('recommended_questions',minimum),t['allocation_capacity'],limit)
        if balanced and t.get('review_kind') in {'combined','lot_only'} and q<t['lot_questions']+t['representative_needed']:
            q=min(q,t['lot_questions'])
            t={**t,'review_kind':'lot_only','recommended_questions':q,'allocation_capacity':q}
        return t,q
    def pick(pool,quota,slots):
        result=[]
        used=0
        if not slots: return result
        for t in pool:
            if len(result)>=slots: break
            t,required=sized(t,quota-used if balanced else quota)
            if required>=floor(t) and required>0 and used+required<=quota and len(result)<slots:
                result.append((t,required))
                used+=required
        return result
    capped=profile.workload_mode=='adaptive' or profile.review_strategy=='balanced_v2'
    new_picks=[pick(pools[0],want_new,n) for n in range(profile.max_topics+1)]
    review_picks=[pick(pools[1],want_reviews,n) for n in range(profile.max_topics+1)]
    protected_floor=min(want_new,max(0,round(day_target*min(profile.new_share,profile.minimum_new_share))-done_new-round(unknown*profile.new_share))) if profile.workload_mode=='adaptive' and any(t.get('intake_protected') for t in pools[0]) else 0
    best=None
    for n in range(profile.max_topics+1):
        for r in range(profile.max_topics-n+1):
            groups=[new_picks[n],review_picks[r]]
            selected=[t for group in groups for t,q in group]
            filled=sum(min(quota,sum(min(t['allocation_capacity'],t.get('recommended_questions',t['allocation_capacity'])) if capped else t['allocation_capacity'] for t,q in group)) for group,quota in zip(groups,[want_new,want_reviews]))
            new_filled=min(want_new,sum(min(t['allocation_capacity'],t.get('recommended_questions',t['allocation_capacity'])) if capped else t['allocation_capacity'] for t,q in groups[0]))
            score=(min(protected_floor,new_filled),filled,len(selected),-abs(len(groups[0])-len(selected)*profile.new_share),len(groups[0]))
            if best is None or score>best[0]: best=(score,groups)
    _,groups=best
    selected=[t for group in groups for t,q in group]
    counts={t['topic_id']:q for group in groups for t,q in group}
    for group,quota in zip(groups,[want_new,want_reviews]): _fill([t for t,q in group],counts,quota,capped)
    # Ceder sobra é explícito; uma preferência de 0%/100% permanece estrita.
    if 0<profile.new_share<1:
        for t in available:
            left=budget-sum(counts.values())
            if left<=0: break
            if any(t['topic_id']==chosen['topic_id'] for chosen in selected) or len(selected)>=profile.max_topics: continue
            t,required=sized(t,left)
            if required>=floor(t) and required>0:
                selected.append(t)
                counts[t['topic_id']]=required
        _fill(selected,counts,budget,capped)
    actual_new=sum(counts[t['topic_id']] for t in selected if topic_is_new(t))
    actual_reviews=sum(counts.values())-actual_new
    return selected,counts,{'requested_share':profile.new_share,'target_new':new_target,'target_reviews':day_target-new_target,
                            'done_new':done_new,'done_reviews':done_reviews,'done_unclassified':unknown,
                            'planned_new':actual_new,'planned_reviews':actual_reviews,
                            'adjusted':actual_new!=want_new or actual_reviews!=want_reviews}
