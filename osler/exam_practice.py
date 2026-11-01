"""Treinos de transferência e reforço: regras operacionais, sem prognóstico de nota."""
from datetime import timedelta
from math import sqrt

from .models import normalize_path
from .planning import _date, _number

AREAS=('Clínica Médica','Clínica Cirúrgica','Pediatria','Ginecologia e Obstetrícia','Preventiva & Social')
EXCLUSIVE={'final_review','final_rest','mock_day','mock_reserved'}


def recover_area_occurrences(occurrences,results,anchor,end,profile,settings,overrides,sessions=(),exam_dates=()):
    """Projeção de recuperação, sem mudar identidade, resultado ou data original."""
    from copy import deepcopy
    from .study_replanning import effective_routine
    rows=deepcopy(occurrences)
    completed={r['exam'].get('practice_id') for r in results}
    occupied={r['date'] for r in rows if r.get('date') and (r['date']>=anchor or r['id'] in completed)}
    for row in sorted(rows,key=lambda r:(r.get('date') or '9999',r['id'])):
        if not row.get('date') or row['date']>=anchor or row['id'] in completed:continue
        missed=row['date']; chosen=None
        for offset in range(max(0,(_date(end)-_date(anchor)).days+1)):
            day=(_date(anchor)+timedelta(days=offset)).isoformat()
            cfg=settings.get(day,{'questions':profile.max_questions,'kind':'normal'})
            override=overrides.get(day,{})
            if day in occupied or day in exam_dates or cfg['kind']=='descanso' or override.get('mode') in EXCLUSIVE:continue
            _,budget=effective_routine(profile,cfg,{k:v for k,v in override.items() if k!='area_reserved'})
            used=sum(s['entry']['questions'] for s in sessions if s['entry']['day']==day and s['entry']['kind']=='bloco')
            used+=area_extra_volume(results,sessions,day).get(day,0)
            if row['questions']<=max(0,budget-used):chosen=day;break
        row.update(missed_date=missed,days_late=(_date(anchor)-_date(missed)).days,
                   recovery=True,status='recovery' if chosen else 'waiting',
                   reason='Treino não realizado; recuperação automática.' if chosen else 'Treino atrasado sem capacidade: escolha outra data ou ajuste a meta.')
        if chosen:row['date']=chosen;occupied.add(chosen)
    return rows


def next_correction_day(exam_day, weekday=2):
    _number(weekday,'Dia da semana',integer=True,maximum=6)
    day=_date(exam_day)+timedelta(days=1)
    return (day+timedelta(days=(weekday-day.weekday())%7)).isoformat()


def area_rotation(first,end,frequency,questions,institutions,exceptions=None):
    start,stop=_date(first),_date(end)
    if frequency not in (1,2) or type(frequency) is not int: raise ValueError('Escolha um ou dois treinos por semana.')
    _number(questions,'Questões por treino',positive=True,integer=True,maximum=1000)
    if not 0<=(stop-start).days<=547: raise ValueError('Escolha um período de até 18 meses.')
    if not isinstance(institutions,list) or not institutions or len(institutions)>30 or any(not isinstance(i,str) or not i.strip() or len(i)>200 for i in institutions):
        raise ValueError('Informe de uma a 30 instituições.')
    if len({tuple(normalize_path([i])) for i in institutions})!=len(institutions): raise ValueError('Não repita instituições.')
    if exceptions is not None and not isinstance(exceptions,dict): raise ValueError('As mudanças de data devem identificar cada ocorrência.')
    changes=exceptions or {}; rows=[]; index=0
    for offset in range((stop-start).days+1):
        if offset%7 not in ([0] if frequency==1 else [0,3]): continue
        day=(start+timedelta(days=offset)).isoformat(); identity='area-'+day
        moved=changes.get(identity,day)
        if moved is not None and not first<=moved<=end: raise ValueError('Mova o treino dentro do período da série.')
        if moved: _date(moved)
        # A cada ciclo de cinco áreas, deslocar a instituição evita ciclos cegos
        # quando o número de instituições é múltiplo de cinco.
        rows.append({'id':identity,'original_date':day,'date':moved,'questions':questions,
                     'area':AREAS[index%5],'institution':institutions[(index//5+index%5)%len(institutions)]})
        index+=1
    if set(changes)-{r['id'] for r in rows}: raise ValueError('Ocorrência desconhecida.')
    dates=[r['date'] for r in rows if r['date']]
    if len(set(dates))!=len(dates): raise ValueError('Dois treinos não podem ocupar a mesma data.')
    return rows


def validate_errors(rows,catalog,total_errors):
    if not isinstance(rows,list): raise ValueError('Informe uma lista de temas.')
    by_path={tuple(normalize_path(t['path'])):t for t in catalog}
    found=[]; keys=[]
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('path'),list) or not row['path'] or any(not isinstance(p,str) or not p.strip() for p in row['path']):
            raise ValueError('Escolha o caminho completo de um tema específico.')
        key=tuple(normalize_path(row['path'])); topic=by_path.get(key)
        if not topic: raise ValueError('Tema específico não encontrado no catálogo atual.')
        if any(key[:len(k)]==k or k[:len(key)]==key for k in keys): raise ValueError('Não repita nem sobreponha temas.')
        n=row.get('errors')
        if n is not None: _number(n,'Erros no tema',positive=True,integer=True,maximum=total_errors)
        keys.append(key); found.append({'topic_id':topic['topic_id'],'path':topic['path'],'errors':n})
    if sum(r['errors'] if r['errors'] is not None else 1 for r in found)>total_errors:
        raise ValueError('A quantidade de erros por tema excede os erros e brancos do simulado.')
    return found


def correction_doses(errors,states,minimum):
    by_id={t['topic_id']:t for t in states}; result=[]
    incidence_scale=max((t.get('importance',0) for t in states),default=0) or 1
    for row in errors:
        state=by_id.get(row['topic_id'])
        if not state: raise ValueError('Um tema saiu do catálogo; confira os erros antes de planejar.')
        observed=state.get('performance',{}).get('observed')
        # Prioridade relativa, não probabilidade de erro. Sem denominador,
        # quantidade de erros recebe peso sublinear e não vira taxa de acerto.
        performance=state.get('performance',{})
        estimate=performance.get('mean',observed)
        deficit=max(0,state.get('target_accuracy',90)/100-estimate) if estimate is not None else .3
        weight=(.1+max(0,state.get('importance',0))/incidence_scale)*(1+deficit)*sqrt(row['errors'] or 1)
        result.append({**row,'weight':weight,'cap':min(state['total'],state['recommended_questions'])})
    peak=max((r['weight'] for r in result),default=1)
    return sorted([{**r,'questions':min(r['cap'],max(1,round(min(minimum,r['cap'])+
                    (r['cap']-min(minimum,r['cap']))*r['weight']/peak)))} for r in result],key=lambda r:(-r['weight'],r['path']))


def schedule_corrections(doses,profile,start,limit,settings,agenda,usage):
    """Carga de correção e capacidade total são limites distintos, ambos reais."""
    from .study_replanning import effective_routine
    capacity={}
    for n in range(90):
        day=(_date(start)+timedelta(days=n)).isoformat()
        if day>profile.exam_date: break
        cfg=settings.get(day,{'questions':profile.max_questions,'kind':'normal'})
        override=agenda['overrides'].get(day,{})
        _,total=effective_routine(profile,cfg,override)
        used=usage.get(day,{})
        capacity[day]={'total':0 if cfg['kind']=='descanso' or override.get('mode') in EXCLUSIVE else max(0,total-used.get('total',0)),
                       'slots':max(0,profile.max_topics-used.get('slots',0)),'batch':limit}
    selected={r['topic_id'] for r in doses}
    for row in sorted(agenda['rows'],key=lambda r:r['date']):
        if row['topic_id'] in selected: continue
        left=row['remaining']
        for day,cap in capacity.items():
            if day<row['date'] or not cap['slots'] or not cap['total']: continue
            q=min(left,cap['total']);cap['total']-=q;cap['slots']-=1;left-=q
            if not left: break
    rows=[]; unassigned=[]
    for row in doses:
        q=row['questions']
        chosen=next((day for day,cap in capacity.items() if cap['slots'] and q<=min(cap['total'],cap['batch'])),None)
        if chosen is None:
            unassigned.append({**row,'reason':'Dose não cabe na carga, nas vagas ou no horizonte de 90 dias. Ajuste o início ou o limite de correção.'})
            continue
        cap=capacity[chosen];cap['total']-=q;cap['batch']-=q;cap['slots']-=1
        rows.append({**row,'date':chosen,'original_due':start,'days_late':0,'new_topic':False})
    return rows,unassigned


def practice_context(agenda,day,sessions=()):
    """Capacidade e volume externos; os blocos convertidos continuam na evidência."""
    from .mock_exams import _prefix
    occurrences=agenda.get('area_practice',[])
    results=agenda.get('area_results',[])
    tasks=[]; prefixes=[]
    for row in occurrences:
        linked=next((r for r in results if r['exam'].get('practice_id')==row['id']),None)
        actual_day=linked['exam']['day'] if linked else row['date']
        if actual_day!=day: continue
        actual=linked['exam']['questions'] if linked else 0
        tasks.append({**row,'done':actual,'completed':bool(linked),'exam_key':linked['exam_key'] if linked else None})
        if linked: prefixes.append(_prefix(linked['exam_key']))
    # Resultados vinculados continuam contando se a série futura for substituída.
    for linked in results:
        if linked['exam']['day']!=day or any(t['exam_key']==linked['exam_key'] for t in tasks): continue
        exam=linked['exam'];tasks.append({'id':exam['practice_id'],'date':day,'institution':exam['institution'],
            'area':exam['areas'][0]['area'],'questions':exam['questions'],'done':exam['questions'],'completed':True,'exam_key':linked['exam_key']})
        prefixes.append(_prefix(linked['exam_key']))
    ordinary=[s for s in sessions if not any(s['session_id'].startswith(p) for p in prefixes)]
    return {'tasks':tasks,'reserved':sum(min(t['questions'],t['done']) if t['completed'] else t['questions'] for t in tasks),
            'done':sum(t['done'] for t in tasks),'pending':sum(t['questions'] for t in tasks if not t['completed']),
            'ordinary_sessions':ordinary}


def area_extra_volume(results,sessions,as_of):
    """Só volume ainda não representado por blocos convertidos; sem acertos inferidos."""
    from .mock_exams import _prefix
    extra={}
    for row in results:
        e=row['exam']; day=e['day']
        if day>as_of or not e.get('practice_id'): continue
        converted=sum(s['entry']['questions'] for s in sessions if s['session_id'].startswith(_prefix(row['exam_key'])) and s['entry']['kind']=='bloco')
        extra[day]=extra.get(day,0)+max(0,e['questions']-converted)
    return extra


def decorate_practice_plan(plan,agenda,day,sessions=()):
    context=practice_context(agenda,day,sessions)
    if plan.get('historical') and context['tasks']:
        ordinary={s['session_id'] for s in context['ordinary_sessions']}
        converted=sum(s['entry']['questions'] for s in sessions if s['entry']['day']==day and s['entry']['kind']=='bloco' and s['session_id'] not in ordinary)
        plan['done_questions']=max(0,(plan.get('done_questions') or 0)-converted)+context['done']
        plan['area_tasks']=context['tasks']
        return plan
    if not context['tasks'] or plan.get('kind')=='descanso' or plan.get('not_started'): return plan
    if plan.get('area_tasks') is not None: return plan
    plan.update(area_tasks=context['tasks'],ordinary_target_questions=plan['target_questions'],ordinary_questions=plan['questions'])
    plan['target_questions']+=context['reserved']
    plan['done_questions']+=context['done']
    plan['questions']+=context['pending']
    return plan
