"""Atraso confirmado e distribuição proposta; agendamento não é evidência de estudo."""
from collections import defaultdict
from dataclasses import replace
from datetime import timedelta
from .models import normalize_path
from .planning import _date

MODES={'balanced':'Distribuir na carga atual','reviews':'Priorizar revisões por alguns dias',
       'extra':'Acrescentar questões temporariamente','custom':'Escolher datas por tema'}


def collect_backlog(states,sessions,saved,as_of,start_date=None):
    if start_date and as_of<=start_date: return []
    latest={}
    for r in saved:
        if r['plan']['date']<as_of and (not start_date or r['plan']['date']>=start_date): latest[r['plan']['date']]=r['plan']
    done=defaultdict(int)
    for s in sessions:
        e=s['entry']
        if e['kind']=='bloco': done[(e['day'],tuple(normalize_path(e['path'])))]+=e['questions']
    missed=defaultdict(list)
    for day,plan in latest.items():
        for t in plan['items']:
            key=tuple(normalize_path(t['path']))
            left=max(0,t['questions']-done[(day,key)])
            if left: missed[key].append((day,left))
    result=[]
    for state in states:
        key=tuple(normalize_path(state['path']))
        failures=missed[key]
        # Um encontro útil posterior recupera planos anteriores; não acumular dívida de repetições.
        recovered=max(state.get('spacing',{}).get('block_days',[]),default=None)
        failures=[(day,n) for day,n in failures if not recovered or day>=recovered]
        due=state.get('next_review') if state.get('review_committed',True) or state.get('pending_reviews') else None
        due=due if due and due<as_of else None
        if failures: due=min([d for d,n in failures]+([due] if due else []))
        if not due: continue
        if start_date: due=max(due,start_date)
        if due>=as_of: continue
        late=(_date(as_of)-_date(due)).days
        interval=max(1,state['review_interval_days'])
        risk=(1+late/interval)*(1+state.get('incidence_strength',0))*(2 if state.get('low_accuracy') else 1)
        if state.get('pending_due'): risk*=2
        q=max(state['recommended_questions'],max((n for d,n in failures),default=0),state.get('pending_due',0))
        result.append({**state,'original_due':due,'days_late':late,'risk':risk,
                       'questions':min(state['total'],q),'missed_questions':sum(n for d,n in failures),
                       'source_days':[d for d,n in failures]})
    return sorted(result,key=lambda r:(-r['risk'],-r['importance'],r['original_due'],r['path']))


def effective_routine(profile,config,override):
    from .final_review import special_config
    config=special_config(config,override)
    q=config['questions']
    if override.get('mode')=='extra':
        total=min(1000,q+override['extra_questions'])
        return replace(profile,new_share=q*profile.new_share/total),total
    return (replace(profile,new_share=0) if override.get('mode') in {'reviews','final_review'} else profile),q


def preview_replan(backlog,profile,start,days,mode,settings,existing,extra_questions=20,dates=None,usage=None,previous_overrides=None):
    if mode not in MODES or type(days) is not int or not 1<=days<=90: raise ValueError('Escolha opção e período de1 a90dias.')
    if type(extra_questions) is not int or not 0<=extra_questions<=300: raise ValueError('Adicional deve estar entre0 e300questões.')
    if start>profile.exam_date: raise ValueError('O início deve ser anterior à prova.')
    output=[]
    unassigned=[]
    overrides={}
    capacity={}
    for n in range(days):
        day=(_date(start)+timedelta(days=n)).isoformat()
        if day>profile.exam_date: break
        config=settings.get(day,{'questions':profile.max_questions,'kind':'normal','extra_topics':[]})
        prior=(previous_overrides or {}).get(day,{})
        protected=prior.get('mode') in {'final_review','final_rest','mock_day'}
        over=prior if protected else {'mode':mode,'extra_questions':extra_questions} if mode in {'reviews','extra'} else prior
        if not protected and config['kind']!='descanso' and mode in {'reviews','extra'}: overrides[day]=over
        p,q=effective_routine(profile,config,over)
        done=(usage or {}).get(day,{})
        capacity[day]={'new':max(0,round(q*p.new_share)-done.get('new',0)),
                       'reviews':max(0,q-round(q*p.new_share)-done.get('reviews',0)),
                       'total':max(0,q-done.get('total',0)), 'slots':max(0,p.max_topics-done.get('slots',0)),'rest':config['kind']=='descanso' or protected}
    for row in sorted(existing,key=lambda r:r['date']):
        left=row['remaining']
        group='new' if row.get('new_topic') else 'reviews'
        for day,c in capacity.items():
            if day<row['date'] or c['rest'] or c['slots']<=0: continue
            q=min(left,c[group],c['total'])
            if q:
                c[group]-=q; c['total']-=q; c['slots']-=1; left-=q
            if not left: break
    for row in backlog:
        group='new' if row.get('is_new_for_day') else 'reviews'
        q=row['questions']
        candidates=[dates.get(row['topic_id'])] if mode=='custom' and dates else list(capacity)
        chosen=next((d for d in candidates if d in capacity and not capacity[d]['rest'] and capacity[d]['slots']>0 and capacity[d][group]>=q and capacity[d]['total']>=q),None)
        if not chosen:
            unassigned.append({'topic_id':row['topic_id'],'path':row['path'],'questions':q,'reason':'Sem vaga com a cota, datas, descanso e limites escolhidos.'})
            continue
        capacity[chosen][group]-=q; capacity[chosen]['total']-=q; capacity[chosen]['slots']-=1
        output.append({'topic_id':row['topic_id'],'path':row['path'],'date':chosen,'original_due':row['original_due'],
                       'questions':q,'new_topic':group=='new','days_late':row['days_late']})
    return {'rows':output,'unassigned':unassigned,'overrides':overrides,'start':start,'days':days,'mode':mode,'extra_questions':extra_questions,'dates':dates or {}}


def past_calendar(states,sessions,saved,start,as_of,backlog):
    latest={r['plan']['date']:r['plan'] for r in saved if r['plan']['date']<as_of}
    actual=defaultdict(int)
    for s in sessions:
        e=s['entry']
        if e['kind']=='bloco': actual[e['day']]+=e['questions']
    delayed=defaultdict(list)
    for row in backlog: delayed[row['original_due']].append(row)
    output={}
    day=_date(start)
    while day<_date(as_of):
        key=day.isoformat()
        plan=latest.get(key)
        output[key]={'date':key,'historical':True,'items':[],'questions':sum(r['questions'] for r in plan['items']) if plan else None,
                     'done_questions':actual[key],'delayed_topics':delayed[key],'has_plan':plan is not None,'kind':'normal'}
        day+=timedelta(days=1)
    return output
