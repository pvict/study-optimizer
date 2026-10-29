"""Agenda auditável sobre o registro imutável de planos já existente (schema9)."""
import hashlib
import json
from .study_storage import StudyStore,_encoded
from .storage import utc_now
from .models import normalize_path
from . import review_policy


def effective_applies(records,as_of):
    eligible=[r for r in records if r.get('created_day','0001-01-01')<=as_of]
    canceled={r['plan_id'] for r in eligible if r.get('kind')=='reschedule.cancel'}
    all_applies={r['id']:r for r in eligible if r.get('kind')=='reschedule.apply'}
    candidates=[r for r in all_applies.values() if r['id'] not in canceled]
    replaced=set()
    def suppress(previous):
        if previous in replaced: return
        replaced.add(previous)
        ancestor=all_applies.get(previous,{})
        if ancestor.get('replaces_plan_id'): suppress(ancestor['replaces_plan_id'])
    for row in candidates:
        if row.get('replaces_plan_id'): suppress(row['replaces_plan_id'])
    return [r for r in candidates if r['id'] not in replaced]


def planning_token(db):
    tables=['study_events','study_profiles','study_plan_runs','guide_settings','guide_days','incidence_datasets',
            'observations','observation_events','reduction_actions','audit_events','planner_events','exam_targets',
            'study_errors','mock_exams','mock_exam_areas','mock_exam_topics','algorithm_parameters','algorithm_selections']
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
        if view['plan'].get('routine_override',{}).get('mode') in {'final_review','final_rest','mock_day','mock_reserved'}: return None
        actual={}; credited={}
        from .exam_practice import practice_context
        for s in practice_context(view.get('agenda',{}),view['date'],view['sessions'])['ordinary_sessions']:
            e=s['entry']
            if e['day']==view['date'] and e['kind']=='bloco':
                key=tuple(normalize_path(e['path']))
                actual[key]=actual.get(key,0)+e['questions']
                credited[key]=credited.get(key,0)+view['plan'].get('allocation_credits',{}).get(s['session_id'],e['questions'])
        payload={'kind':'daily_schedule','plan':{'date':view['date'],'items':[
            {'topic_id':i['topic_id'],'path':i['path'],'questions':i['questions']+actual.get(tuple(normalize_path(i['path'])),0),
             **({'planner_supply':i['planner_supply']} if i.get('planner_supply') else {})} for i in view['plan']['items']]}}
        payload.update(event_cutoff=max((s['id'] for s in view['sessions']),default=0),
            actual_at_capture={i['topic_id']:actual.get(tuple(normalize_path(i['path'])),0) for i in view['plan']['items']},
            planned_totals={i['topic_id']:i['questions']+credited.get(tuple(normalize_path(i['path'])),0) for i in view['plan']['items']},
            agenda_revision=sorted(r['id'] for r in view.get('agenda',{}).get('active',[])),
            profile_id=view.get('profile_id',0),day_revision=view.get('day',{}).get('revision',0))
        previous=next((r for r in reversed(self.records()) if r.get('kind')=='daily_schedule' and r['plan']['date']==view['date']),None)
        if previous and all(previous.get(k)==payload.get(k) for k in ['plan','event_cutoff','actual_at_capture','planned_totals','profile_id','day_revision','agenda_revision']): return previous['id']
        payload['previous_daily_id']=previous['id'] if previous else 0
        return self.store.save_plan(payload,expected_planning_token=view.get('planning_token'))

    def active(self,sessions,as_of,excluded_plan_ids=()):
        records=self.records()
        applies=[r for r in effective_applies(records,as_of) if r['id'] not in excluded_plan_ids]
        rows={}
        overrides={}
        policies=[]
        triage_policies=[]
        for r in applies:
            overrides.update(r.get('overrides',{}))
            if r.get('scope')=='preventive': policies.append({**r['policy'],'plan_id':r['id']})
            if r.get('scope')=='triage': triage_policies.append({**r['policy'],'plan_id':r['id']})
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
            from .mock_exams import _prefix
            source_prefix=_prefix(item['source_exam_key']) if item.get('source_exam_key') else None
            used=sum(s['entry']['questions'] for s in sessions if s['entry']['kind']=='bloco' and
                     (not source_prefix or not s['session_id'].startswith(source_prefix)) and
                     (not item.get('source_exam_key') or s['entry']['day']>=item['date']) and
                     s.get('first_event_id',s.get('id',0))>item['cutoff'] and s['entry']['day']>=item['created_day'] and tuple(normalize_path(s['entry']['path']))==key)
            item['remaining']=max(0,item['questions']-used)
        from .planner_completion import active_completions
        completions=active_completions(records,sessions,as_of)
        for item in rows.values():
            closed=next((r for r in completions if r['topic_id']==item['topic_id'] and
                         item['plan_id']<r['id'] and item['date']<=r['day']),None)
            if closed:
                item['planner_completed_day']=closed['day']
                if as_of>closed['day']:item['remaining']=0
        from .mock_exams import MockExams
        from .exam_practice import practice_context,EXCLUSIVE
        practice=next((r for r in reversed(applies) if r.get('scope')=='area_practice'),{})
        area_rows=[dict(r) for r in practice.get('occurrences',[]) if r['date'] and r.get('status')!='blocked']
        results=[r for r in MockExams(self.repo).active() if r['exam'].get('practice_id')]
        practice_agenda={'area_practice':area_rows,'area_results':results}
        day_settings=self.store.days()
        for day in {r['date'] for r in area_rows}|{r['exam']['day'] for r in results}:
            prior=overrides.get(day,{})
            config=day_settings.get(day,{})
            if prior.get('mode') in EXCLUSIVE or config.get('kind')=='descanso': continue
            context=practice_context(practice_agenda,day)
            if context['tasks']: overrides[day]={**prior,'area_reserved':context['reserved']}
        return {'rows':[r for r in rows.values() if r['remaining']>0],'overrides':overrides,'active':applies,'policies':policies,'triage_policies':triage_policies,'swaps':swaps,
                **practice_agenda,
                'planner_completions':completions,
                'history':[r for r in records if r.get('kind','').startswith('reschedule.')]}
