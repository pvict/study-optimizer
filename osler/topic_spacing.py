"""Adaptação explícita de intervalos SM-2 a blocos, sem curva pessoal calibrada."""
from collections import defaultdict
from datetime import timedelta
from math import ceil
from .planning import _date


def spacing_state(entries,profile,as_of,incidence_strength=0):
    if profile.review_strategy=='balanced_v2':
        from .balanced_reviews import balanced_spacing
        return balanced_spacing(entries,profile,as_of,incidence_strength)
    p=profile.parameters
    daily=defaultdict(list)
    for e in entries:
        if e['kind']=='bloco' and e['day']<=as_of and not e.get('review_of'): daily[e['day']].append(e)
    ease,streak,interval,last=p.default_ease,0,p.first_interval,None
    block_days=[]
    for day,blocks in sorted(daily.items()):
        if sum(e['questions'] for e in blocks)>=profile.min_block: block_days.append(day)
        known=[e for e in blocks if e.get('confident_correct') is not None]
        n=sum(e['questions'] for e in known)
        if n<profile.min_block: continue
        rate=sum(e['confident_correct'] for e in known)/n
        if last and (_date(day)-_date(last)).days<min(p.spaced_min_days,interval) and rate>=profile.target_accuracy/100:
            continue
        last=day
        grade=5 if rate>=profile.target_accuracy/100 else 4 if rate>=p.intermediate_threshold else 3 if rate>=p.failure_threshold else 1
        ease=max(p.min_ease,min(p.max_ease,ease+p.ease_step-(5-grade)*(p.ease_penalty+(5-grade)*p.ease_penalty_squared)))
        if rate>=profile.target_accuracy/100:
            streak+=1
            interval=p.first_interval if streak==1 else p.second_interval if streak==2 else ceil(interval*ease)
        else:
            streak=0
            interval=p.failure_interval if rate<p.failure_threshold else p.first_interval
        interval=min(profile.max_contact_gap,interval)
    interval=min(interval,profile.max_contact_gap)
    base_interval=interval
    interval=max(1,ceil(interval/(1+p.incidence_factor*max(0,min(1,incidence_strength)))))
    return {'interval':interval,'next_due':(_date(last)+timedelta(days=interval)).isoformat() if last else None,
            'base_interval':base_interval,'ease':ease,'streak':streak,'last_evidence_day':last,
            'block_days':block_days,'incidence_strength':incidence_strength,
            'method':'SM-2 adaptado a blocos, com prioridade por incidência; não calibrado'}


def learning_state(evidence,profile):
    p=profile.parameters
    rate=evidence['rate']
    if not evidence['seen'] or evidence['pending_due'] or evidence['overdue'] or rate is not None and rate<p.failure_threshold or evidence.get('raw_rate') is not None and evidence['raw_rate']<p.failure_threshold:
        return 'alerta'
    if rate is not None and rate>=profile.target_accuracy/100 and evidence['n']>=p.sufficient_sample and evidence['lower'] is not None and evidence['lower']>=p.mastery_wilson_lower and evidence['source'] in {'novas','mistas'}:
        return 'dominado'
    return 'aprendendo'
