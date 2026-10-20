"""Adaptação explícita de intervalos SM-2 a blocos, sem curva pessoal calibrada."""
from collections import defaultdict
from datetime import timedelta
from math import ceil
from .planning import _date


def spacing_state(entries,profile,as_of,incidence_strength=0):
    daily=defaultdict(list)
    for e in entries:
        if e['kind']=='bloco' and e['day']<=as_of and not e.get('review_of'): daily[e['day']].append(e)
    ease,streak,interval,last=2.5,0,7,None
    block_days=[]
    for day,blocks in sorted(daily.items()):
        if sum(e['questions'] for e in blocks)>=profile.min_block: block_days.append(day)
        known=[e for e in blocks if e.get('confident_correct') is not None]
        n=sum(e['questions'] for e in known)
        if n<profile.min_block: continue
        rate=sum(e['confident_correct'] for e in known)/n
        if last and (_date(day)-_date(last)).days<min(3,interval) and rate>=profile.target_accuracy/100:
            continue
        last=day
        grade=5 if rate>=profile.target_accuracy/100 else 4 if rate>=.8 else 3 if rate>=.6 else 1
        ease=max(1.3,min(3.,ease+.1-(5-grade)*(.08+(5-grade)*.02)))
        if rate>=profile.target_accuracy/100:
            streak+=1
            interval=7 if streak==1 else 14 if streak==2 else ceil(interval*ease)
        else:
            streak=0
            interval=3 if rate<.6 else 7
        interval=min(profile.max_contact_gap,interval)
    interval=min(interval,profile.max_contact_gap)
    base_interval=interval
    interval=max(1,ceil(interval/(1+.5*max(0,min(1,incidence_strength)))))
    return {'interval':interval,'next_due':(_date(last)+timedelta(days=interval)).isoformat() if last else None,
            'base_interval':base_interval,'ease':ease,'streak':streak,'last_evidence_day':last,
            'block_days':block_days,'incidence_strength':incidence_strength,
            'method':'SM-2 adaptado a blocos, com prioridade por incidência; não calibrado'}


def learning_state(evidence,profile):
    rate=evidence['rate']
    if not evidence['seen'] or evidence['pending_due'] or evidence['overdue'] or rate is not None and rate<.6 or evidence.get('raw_rate') is not None and evidence['raw_rate']<.6:
        return 'alerta'
    if rate is not None and rate>=profile.target_accuracy/100 and evidence['n']>=30 and evidence['lower'] is not None and evidence['lower']>=.8 and evidence['source'] in {'novas','mistas'}:
        return 'dominado'
    return 'aprendendo'
