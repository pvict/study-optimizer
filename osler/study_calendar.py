"""Projeção de contatos planejados, sem sessões/acertos simulados ou gravações."""
from copy import deepcopy
from datetime import timedelta

from .planning import _date
from .adaptive_planning import allocate_day
from .study_replanning import effective_routine
from .study_prevention import preventive_state,projected_backlog


def forecast_calendar(states,profile,start,days,sessions,settings,today_plan=None,agenda=None):
    if type(days) is not int or not 1<=days<=548: raise ValueError('O calendário prevê até18meses.')
    working=deepcopy(states)
    contact_counts={t['topic_id']:len([d for d in t.get('spacing',{}).get('block_days',[]) if d<=start]) for t in working}
    pending={q['session_id']:{**q,'remaining':q['questions']} for t in working for q in t.get('pending_reviews',[])}
    output=[]
    agenda=deepcopy(agenda or {'rows':[],'overrides':{}})
    for offset in range(days):
        day=(_date(start)+timedelta(days=offset)).isoformat()
        config=settings.get(day,{'questions':profile.max_questions,'kind':'normal','extra_topics':[]})
        daily_profile,daily_target=effective_routine(profile,config,agenda['overrides'].get(day,{}))
        if profile.start_date and day<profile.start_date:
            plan=allocate_day([],daily_profile,None,config['kind'],sessions if offset==0 else [],day,question_target=daily_target)
            output.append({**plan,'projection':True,'pending_planned':0,'pending_backlog':0,'topic_backlog':0,'backlog_items':[]})
            continue
        active=[]
        for state in working:
            returns=[q['due_date'] for q in state.get('pending_reviews',[]) if pending[q['session_id']]['remaining']>0]
            decorated=preventive_state(state,day,agenda.get('policies',[]),returns)
            due=decorated['allocation_due']
            eligible=(not state.get('reschedule_date') or state['reschedule_date']<=day) and (not offset or day==profile.start_date or due is None or due<=day)
            if not eligible: continue
            original=min(returns+([state['next_review']] if state.get('next_review') else []),default=None)
            contact_age=max(0,(_date(day)-_date(state['last_contact'])).days) if state.get('last_contact') else 0
            reduced=state.get('cards_reduced_day')
            reduced_due=bool(reduced and (_date(day)-_date(reduced)).days>=14 and
                             (not state.get('last_contact') or state['last_contact']<reduced or contact_age>=14))
            temporal='urgente' if contact_age>=2*state.get('review_interval_days',profile.max_contact_gap) else 'alta' if reduced_due or original and original<=day else 'normal'
            ranks={'urgente':0,'alta':1,'normal':2}
            decorated['priority']=min((state.get('evidence_priority',state['priority']),temporal),key=ranks.get)
            active.append(decorated)
        active.sort(key=lambda t:({'urgente':0,'alta':1,'normal':2}[t['priority']],t['next_review'] if t.get('next_review') and t['next_review']<=day else '9999-12-31',-t['score'],t['path']))
        by_id={t['topic_id']:t for t in working}
        extras=[{**by_id[e['topic_id']],'extra_id':e['extra_id'],'requested':e['questions'],'after_event_id':e['after_event_id']} for e in config.get('extra_topics',[]) if e['topic_id'] in by_id]
        due_reservations=[r for r in agenda['rows'] if r['date']<=day and r['remaining']>0]
        # Reservas também podem antecipar a fila normal; jamais duplicar o tema.
        active_ids={t['topic_id'] for t in active}
        active.extend(by_id[r['topic_id']] for r in due_reservations if r['topic_id'] in by_id and r['topic_id'] not in active_ids)
        plan=deepcopy(today_plan) if offset==0 and today_plan else allocate_day(active,daily_profile,None,config['kind'],sessions if offset==0 else [],day,question_target=daily_target,extra_topics=extras,reservations=due_reservations)
        plan['routine_override']=agenda['overrides'].get(day,{})
        scheduled_pending=0
        for item in plan['items']:
            if item['topic_id'] not in by_id: continue
            t=by_id[item['topic_id']]
            if item.get('rescheduled'):
                for row in due_reservations:
                    if row['topic_id']==item['topic_id']: row['remaining']=max(0,row['remaining']-item['questions'])
                if not any(r['topic_id']==item['topic_id'] and r['remaining'] for r in agenda['rows']): t.pop('reschedule_date',None)
            already_recorded=day in t.get('spacing',{}).get('block_days',[])
            number=contact_counts[t['topic_id']]-(1 if already_recorded else 0)
            item['review_number']=number
            item['stage']='Revisão '+str(number) if number else 'Primeiro contato' if t['status']=='sem_registro' else 'Diagnóstico'
            if item['questions']>=profile.min_block and not already_recorded: contact_counts[t['topic_id']]+=1
            free=item['questions']
            for q in t.get('pending_reviews',[]):
                record=pending[q['session_id']]
                if record['due_date']<=day:
                    assigned=min(free,record['remaining'])
                    record['remaining']-=assigned
                    free-=assigned
                    scheduled_pending+=assigned
            t['next_review']=(_date(day)+timedelta(days=t.get('review_interval_days',7))).isoformat()
            t['last_contact']=day
            t['available_new']=max(0,t['available_new']-item['new_questions'])
            t['status']='revisao'
            t['is_new_for_day']=False
            t['priority']=t.get('evidence_priority',t['priority'])
            # Só contato previsto. Nenhum sucesso, confiança ou posterior é inventado.
        backlog=projected_backlog(working,pending,day,start_date=profile.start_date)
        output.append({**plan,'projection':offset>0,'pending_planned':scheduled_pending,
                       'pending_backlog':sum(q['remaining'] for q in pending.values() if q['due_date']<=day),
                       'topic_backlog':len(backlog),'backlog_items':backlog})
    return output
