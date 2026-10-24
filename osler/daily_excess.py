"""Créditos de alocação por proposta; tentativas reais nunca são reescritas."""
import json
from .models import normalize_path
from .study_models import AdaptiveProfile


def _key(path): return tuple(normalize_path(path))


def daily_completion_context(repo,day,sessions,profile_id,day_revision,agenda_revision=()):
    with repo._connection() as db:
        rows=db.execute("SELECT id,payload,created_at FROM study_plan_runs WHERE json_extract(payload,'$.kind')='daily_schedule' AND json_extract(payload,'$.plan.date')=? ORDER BY id",(day,)).fetchall()
        events=[{**dict(r),'entry':json.loads(r['payload'])} for r in db.execute('SELECT * FROM study_events ORDER BY id')]
        profiles=[{**dict(r),'profile':json.loads(r['payload'])} for r in db.execute('SELECT id,payload,created_at FROM study_profiles ORDER BY id')]
        d=db.execute('SELECT updated_at FROM study_days WHERE day=?',(day,)).fetchone()
        config_times={r['id']:r['created_at'] for r in db.execute('SELECT id,created_at FROM study_plan_runs')}
    proposals=[{'id':r['id'],'at':r['created_at'],**json.loads(r['payload'])} for r in rows]
    if not proposals: return {'credits':{},'excess':0,'preserve':[]}
    event_by_id={e['id']:e for e in events}
    current=sorted([s for s in sessions if s['entry']['day']==day and s['entry']['kind']=='bloco'],key=lambda s:s.get('first_event_id',s['id']))
    actual_cache={}
    def before(proposal,entry):
        cutoff=proposal.get('event_cutoff')
        return entry['first_event_id']>cutoff if cutoff is not None else event_by_id[entry['first_event_id']]['created_at']>proposal['at']
    def actual_at(proposal):
        if proposal['id'] not in actual_cache:
            latest={}
            for e in events:
                after=e['id']>proposal['event_cutoff'] if 'event_cutoff' in proposal else e['created_at']>proposal['at']
                if after: continue
                latest[e['session_id']]=e
            totals={}
            for e in latest.values():
                v=e['entry']
                if e['action']=='save' and v['day']==day and v['kind']=='bloco': totals[_key(v['path'])]=totals.get(_key(v['path']),0)+v['questions']
            actual_cache[proposal['id']]=totals
        return actual_cache[proposal['id']]
    planned_cache={}
    def planned_total(proposal,item):
        key=(proposal['id'],item['topic_id'])
        if key not in planned_cache:
            value=proposal.get('planned_totals',{}).get(item['topic_id'])
            if value is None:
                inherited=0
                for previous in reversed(proposals):
                    if previous['id']>=proposal['id']: continue
                    old=next((i for i in previous['plan']['items'] if _key(i['path'])==_key(item['path'])),None)
                    if old:
                        inherited=max(0,actual_at(proposal).get(_key(item['path']),0)-planned_total(previous,old)); break
                value=max(0,item['questions']-inherited)
            planned_cache[key]=value
        return planned_cache[key]
    credits={}; exceeded=[]; credited_by_path={}
    for s in current:
        s={**s,'first_event_id':s.get('first_event_id',s['id'])}; key=_key(s['entry']['path'])
        match=None
        for proposal in reversed(proposals):
            if not before(proposal,s): continue
            item=next((i for i in proposal['plan']['items'] if _key(i['path'])==key),None)
            if item: match=(proposal,item); break
        if not match:
            credited_by_path[key]=credited_by_path.get(key,0)+s['entry']['questions']; continue
        proposal,item=match
        allowance=max(0,planned_total(proposal,item)-credited_by_path.get(key,0))
        credits[s['session_id']]=min(s['entry']['questions'],allowance)
        credited_by_path[key]=credited_by_path.get(key,0)+credits[s['session_id']]
        if s['entry']['questions']>allowance: exceeded.append((s,proposal))
    excess=sum(s['entry']['questions']-credits.get(s['session_id'],s['entry']['questions']) for s in current)
    preserve=[]
    def settings(profile): return {k:v for k,v in AdaptiveProfile(**profile).to_dict().items() if k!='review_strategy'}
    current_profile=next((p['profile'] for p in profiles if p['id']==profile_id),AdaptiveProfile().to_dict())
    legacy_cutoff=d['updated_at'] if d else ''
    legacy_cutoff=max(legacy_cutoff,max((config_times.get(i,'') for i in agenda_revision),default=''))
    for _,proposal in reversed(exceeded):
        old_profile=next((p['profile'] for p in reversed(profiles) if p['id']==proposal['profile_id']),None) if 'profile_id' in proposal else next((p['profile'] for p in reversed(profiles) if p['created_at']<=proposal['at']),AdaptiveProfile().to_dict())
        compatible=old_profile is not None and settings(old_profile)==settings(current_profile)
        compatible=compatible and (proposal.get('day_revision')==day_revision if 'day_revision' in proposal else proposal['at']>=legacy_cutoff)
        compatible=compatible and (proposal.get('agenda_revision')==list(agenda_revision) if 'agenda_revision' in proposal else proposal['at']>=legacy_cutoff)
        if not compatible: continue
        for item in proposal['plan']['items']:
            done=credited_by_path.get(_key(item['path']),0)
            remaining=max(0,planned_total(proposal,item)-done)
            if remaining: preserve.append({**item,'remaining':remaining})
        if preserve: break
    return {'credits':credits,'excess':excess,'preserve':preserve}
