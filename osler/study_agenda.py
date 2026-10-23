"""Agenda auditável sobre o registro imutável de planos já existente (schema9)."""
import hashlib
import json
from .study_storage import StudyStore,_encoded
from .storage import utc_now
from .models import normalize_path
from . import review_policy


def planning_token(db):
    tables=['study_events','study_profiles','study_plan_runs','guide_settings','guide_days','incidence_datasets',
            'observations','observation_events','reduction_actions','audit_events','planner_events','exam_targets',
            'study_errors','mock_exams','mock_exam_areas','mock_exam_topics']
    values=[(name,db.execute('SELECT COALESCE(MAX(rowid),0) FROM '+name).fetchone()[0]) for name in tables]
    values.append(('days',[tuple(r) for r in db.execute('SELECT day,revision FROM study_days ORDER BY day')]))
    values.append(('review_policy',review_policy.POLICY_VERSION))
    return hashlib.sha256(_encoded(values).encode()).hexdigest()


class StudyAgenda:
    def __init__(self,repo):
        self.repo=repo
        self.store=StudyStore(repo)

    def token(self):
        with self.repo._connection() as db: return planning_token(db)

    def records(self):
        with self.repo._connection() as db:
            return [{'id':r['id'],**json.loads(r['payload'])} for r in db.execute('SELECT id,payload FROM study_plan_runs ORDER BY id')]

    def append(self,payload,expected_token):
        encoded=_encoded(payload)
        digest=hashlib.sha256(encoded.encode()).hexdigest()
        with self.repo._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if planning_token(db)!=expected_token: raise ValueError('O plano mudou. Atualize a prévia antes de aplicar.')
            db.execute('INSERT OR IGNORE INTO study_plan_runs(payload,digest,created_at) VALUES(?,?,?)',(encoded,digest,utc_now()))
            return db.execute('SELECT id FROM study_plan_runs WHERE digest=?',(digest,)).fetchone()[0]

    def daily_plans(self):
        return [{'id':r['id'],'plan':r['plan']} for r in self.records() if r.get('kind')=='daily_schedule']

    def remember(self,view):
        if view['plan'].get('not_started'): return None
        if view['plan'].get('routine_override',{}).get('mode') in {'final_review','final_rest','mock_day'}: return None
        actual={}
        for s in view['sessions']:
            e=s['entry']
            if e['day']==view['date'] and e['kind']=='bloco':
                key=tuple(normalize_path(e['path']))
                actual[key]=actual.get(key,0)+e['questions']
        payload={'kind':'daily_schedule','plan':{'date':view['date'],'items':[
            {'topic_id':i['topic_id'],'path':i['path'],'questions':i['questions']+actual.get(tuple(normalize_path(i['path'])),0)} for i in view['plan']['items']]}}
        previous=next((r for r in reversed(self.records()) if r.get('kind')=='daily_schedule' and r['plan']['date']==view['date']),None)
        if previous and previous['plan']==payload['plan']: return previous['id']
        payload['previous_daily_id']=previous['id'] if previous else 0
        return self.store.save_plan(payload)

    def active(self,sessions,as_of):
        records=self.records()
        canceled={r['plan_id'] for r in records if r.get('kind')=='reschedule.cancel'}
        applies=[r for r in records if r.get('kind')=='reschedule.apply' and r['id'] not in canceled and r['created_day']<=as_of]
        rows={}
        overrides={}
        policies=[]
        for r in applies:
            overrides.update(r.get('overrides',{}))
            if r.get('scope')=='preventive': policies.append({**r['policy'],'plan_id':r['id']})
            selected=set(r.get('selected',[]))
            rows={key:item for key,item in rows.items() if item['topic_id'] not in selected}
            for item in r['rows']: rows[tuple(normalize_path(item['path']))]={**item,'plan_id':r['id'],'cutoff':r['cutoff'],'created_day':r['created_day']}
        from .study_swaps import active_swaps
        swaps=active_swaps(records,as_of)
        for swap in swaps:
            for item in swap.get('returns',[]):
                key=tuple(normalize_path(item['path']))
                booking=item.get('booking_id',swap['id'])
                if key in rows and rows[key]['plan_id']>booking: continue
                rows[key]={**item,'plan_id':booking,'cutoff':item.get('cutoff',swap['cutoff']),
                                                         'created_day':swap['created_day'],'swap_return':swap['slot_id']}
        for key,item in rows.items():
            used=sum(s['entry']['questions'] for s in sessions if s['entry']['kind']=='bloco' and
                     s.get('first_event_id',s.get('id',0))>item['cutoff'] and s['entry']['day']>=item['created_day'] and tuple(normalize_path(s['entry']['path']))==key)
            item['remaining']=max(0,item['questions']-used)
        return {'rows':[r for r in rows.values() if r['remaining']>0],'overrides':overrides,'active':applies,'policies':policies,'swaps':swaps,
                'history':[r for r in records if r.get('kind','').startswith('reschedule.')]}
