"""Escolhas pontuais de tema; não representam contato ou aprendizado."""
from math import log
from .models import normalize_path
from .study_allocation import topic_is_new
from .topic_catalog import is_practice_topic

PRIORITY={'urgente':0,'alta':1,'normal':2}


def replacement_candidates(original,states,excluded,day):
    manual=[t for t in states if t['topic_id'] not in excluded|{original['topic_id']} and
            is_practice_topic(t) and not t.get('historical_aggregate') and t['total']>=original['questions'] and
            not (t.get('review_kind')=='lot_only' and sum(q['questions'] for q in t.get('pending_reviews',[]) if q['due_date']<=day)>original['questions'])]
    similar=[t for t in manual if topic_is_new(t)==topic_is_new(original) and
             abs(PRIORITY[t['priority']]-PRIORITY[original['priority']])<=1 and
             (not t.get('allocation_due',t.get('next_review')) or t.get('allocation_due',t.get('next_review'))<=day) and
             (not t.get('reschedule_date') or t['reschedule_date']<=day)]
    def distance(t):
        return (abs(PRIORITY[t['priority']]-PRIORITY[original['priority']]),
                abs(log(max(t['score'],1e-12)/max(original['score'],1e-12))),t['path'])
    return {'manual':manual,'recommended':min(similar,key=distance) if similar else None}


def active_swaps(records,as_of):
    active={}
    canceled={r['apply_id'] for r in records if r.get('kind')=='day.swap.cancel' and r.get('created_day','')<=as_of and r.get('apply_id') is not None}
    for record in records:
        if record.get('created_day','')>as_of: continue
        if record.get('kind')=='day.swap' and record.get('id') not in canceled:
            active[record['slot_id']]={**record,'returns':[{**row,'booking_id':row.get('booking_id',record.get('id',0))} for row in record.get('returns',[])]}
        elif record.get('kind')=='day.swap.cancel' and record.get('apply_id') is None: active.pop(record['slot_id'],None)
    return list(active.values())


def swap_rows(swaps,sessions,day):
    rows=[]
    for swap in swaps:
        if swap['day']!=day: continue
        remaining=swap['questions']; credits=[]
        for s in sessions:
            if s['entry']['kind']!='bloco' or s['entry']['day']!=day or s.get('first_event_id',s.get('id',0))<=swap['cutoff'] or normalize_path(s['entry']['path'])!=normalize_path(swap['path']): continue
            used=min(remaining,s['entry']['questions'])
            if used: credits.append({'session_id':s['session_id'],'questions':used,'source_path':swap.get('quota_path',swap['from_path'])})
            remaining-=used
        rows.append({**swap,'remaining':remaining,'credits':credits})
    return rows


def quota_entries(sessions,swaps,day):
    """Credita o slot original só para alocação; o resultado real conserva seu tema."""
    credits=[c for r in swaps if not r.get('extra_only') for c in r.get('prior_credits',[])+r.get('credits',[])]
    entries=[]; adjustments=[]
    for s in sessions:
        e=s['entry']
        if e['day']!=day or e['kind']=='acumulado': continue
        left=e['questions']
        for c in credits:
            if c['session_id']!=s['session_id']: continue
            used=min(left,c['questions']); left-=used
            if used:
                entries.append({**e,'path':c['source_path'],'questions':used})
                adjustments.append({'source_path':c['source_path'],'path':e['path'],'questions':used})
        if left or not e['questions']: entries.append({**e,'questions':left})
    return entries,adjustments
