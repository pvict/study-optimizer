"""Hipótese de espaçamento para cenários; nunca produz sessões ou acertos."""
from math import ceil
from .planning import _date

SCENARIOS={'progressive':'Atingindo a meta nas revisões','unchanged':'Mantendo os intervalos atuais'}
SCENARIO_VERSION=1


def advance_projected_spacing(state,profile,day,questions,lot_only=False):
    if lot_only or questions<profile.min_block or state.get('manual_adverse'): return
    source=state.get('projected_spacing') or state.get('spacing',{})
    last=source.get('last_evidence_day')
    if last and (_date(day)-_date(last)).days<min(3,source.get('base_interval',7)): return
    streak=source.get('streak',0)+1
    ease=min(3.,max(1.3,source.get('ease',2.5)+.1))
    base=7 if streak==1 else 14 if streak==2 else ceil(source.get('base_interval',7)*ease)
    base=min(profile.max_contact_gap,base)
    strength=max(0,min(1,state.get('incidence_strength',0)))
    interval=max(1,ceil(base/(1+.5*strength)))
    interval=min(interval,max(1,(_date(profile.exam_date)-_date(day)).days//4))
    if state.get('cards_reduced_day'): interval=min(interval,14)
    state['projected_spacing']={'streak':streak,'ease':ease,'base_interval':base,'last_evidence_day':day}
    state['review_interval_days']=interval
