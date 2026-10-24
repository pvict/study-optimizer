"""Hipótese de espaçamento para cenários; nunca produz sessões ou acertos."""
from math import ceil
from .planning import _date

SCENARIOS={'progressive':'Atingindo a meta nas revisões','unchanged':'Mantendo os intervalos atuais'}
SCENARIO_VERSION=1


def advance_projected_spacing(state,profile,day,questions,lot_only=False):
    p=profile.parameters
    if lot_only or questions<profile.min_block or state.get('manual_adverse'): return
    source=state.get('projected_spacing') or state.get('spacing',{})
    last=source.get('last_evidence_day')
    gap=max(p.spaced_min_days,source.get('base_interval',p.first_interval)) if profile.review_strategy=='balanced_v2' else min(p.spaced_min_days,source.get('base_interval',p.first_interval))
    if last and (_date(day)-_date(last)).days<gap: return
    streak=source.get('streak',0)+1
    ease=min(p.max_ease,max(p.min_ease,source.get('ease',p.default_ease)+p.ease_step))
    base=p.first_interval if streak==1 else p.second_interval if streak==2 else ceil(source.get('base_interval',p.first_interval)*ease)
    if profile.review_strategy=='balanced_v2':
        base=p.first_interval if streak==1 else ceil(source.get('base_interval',p.first_interval)*2)
        if streak==2: base=min(base,p.second_interval)
    base=min(profile.max_contact_gap,base)
    strength=max(0,min(1,state.get('incidence_strength',0)))
    interval=base if profile.review_strategy=='balanced_v2' else max(1,ceil(base/(1+p.incidence_factor*strength)))
    interval=min(interval,max(1,(_date(profile.exam_date)-_date(day)).days//4))
    if state.get('cards_reduced_day'): interval=min(interval,14)
    state['projected_spacing']={'streak':streak,'ease':ease,'base_interval':base,'last_evidence_day':day}
    state['review_interval_days']=interval
