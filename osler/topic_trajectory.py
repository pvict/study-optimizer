"""Doses e trajetórias condicionais; nenhuma previsão é transformada em resultado."""
from collections import defaultdict
from datetime import timedelta
from math import ceil

from .planning import _date


def question_dose(state,profile,entries=(),as_of=None):
    """Política inicial explícita: necessidade + incerteza + relevância, não dose clínica validada."""
    if profile.review_strategy=='balanced_v2':
        from .balanced_reviews import balanced_dose
        return balanced_dose(state,profile,entries,as_of)
    params=profile.parameters
    p=state['confidence'] if state['confidence']['exact_n'] else state['performance']
    target=profile.target_accuracy/100
    rate=p['observed'] if p['observed'] is not None else p['mean']
    snapshot=state.get('planner_safety') if state.get('planner_snapshot_current',True) else None
    initial=not state.get('review_committed',True)
    if initial and snapshot and snapshot.get('confident_accuracy_pct') is not None:
        rate=snapshot['confident_accuracy_pct']/100
    # Resultados do último dia protegem contra uma média antiga que oculte piora.
    daily=defaultdict(list)
    for e in entries:
        if e['kind']=='bloco' and not e.get('review_of') and (not as_of or e['day']<=as_of):
            daily[e['day']].append(e)
    streak=0
    last_spaced=None
    latest_rate=None
    latest_day=None
    latest_complete=False
    evidence_window=min(profile.recent_days,2*state['review_interval_days'])
    for day,blocks in sorted(daily.items()):
        n=sum(e['questions'] for e in blocks)
        if n<profile.min_block: continue
        known=[e for e in blocks if e.get('confident_correct') is not None]
        latest_complete=sum(e['questions'] for e in known)==n
        latest_day=day
        rates=[sum(e['confident_correct'] for e in known)/sum(e['questions'] for e in known)] if known else []
        raw=[e for e in blocks if e.get('correct') is not None or e.get('percent') is not None]
        if raw:
            rates.append(sum(e['correct'] if e.get('correct') is not None else e['questions']*e['percent']/100 for e in raw)/sum(e['questions'] for e in raw))
        latest_rate=min(rates) if rates else None
        if last_spaced and (_date(day)-_date(last_spaced)).days>evidence_window: streak=0
        if latest_rate is not None and latest_rate<target:
            streak=0
            last_spaced=day
        elif not latest_complete:
            streak=0
            last_spaced=day
        elif latest_complete and (last_spaced is None or (_date(day)-_date(last_spaced)).days>=params.spaced_min_days):
            streak+=1
            last_spaced=day
    # Blocos pequenos e lotes de erros não provam aprendizagem do tema,
    # mas uma falha neles também não pode ser ocultada por sucessos anteriores.
    for e in entries:
        if e['kind']!='bloco' or as_of and e['day']>as_of or latest_day and e['day']<latest_day: continue
        signals=[]
        if e.get('confident_correct') is not None: signals.append(e['confident_correct']/e['questions'])
        if e.get('correct') is not None: signals.append(e['correct']/e['questions'])
        elif e.get('percent') is not None: signals.append(e['percent']/100)
        if signals and min(signals)<target:
            latest_rate=min([min(signals)]+([latest_rate] if latest_rate is not None else []))
    if latest_rate is not None: rate=min(rate,latest_rate)
    gap=max(0,target-rate)/target
    uncertainty=min(1,p['sd']/.25)
    h=state.get('incidence_strength',0)
    desired=max(profile.min_block,ceil(profile.min_block+params.gap_dose*gap+params.uncertainty_dose*uncertainty+params.incidence_dose*h))
    reliable_initial=bool(initial and snapshot and snapshot['unique_questions']>=params.sufficient_sample and rate>=target)
    if not state['spacing']['block_days'] and not reliable_initial: desired=max(desired,params.diagnostic_dose,profile.min_block)
    stale=bool(as_of and latest_day and (_date(as_of)-_date(latest_day)).days>evidence_window)
    adverse=bool(state.get('manual_adverse') or state.get('registered_error') or state.get('alert_signal') or
                 latest_rate is not None and latest_rate<target or p['exact_n']>=5 and rate<target)
    maintenance=bool(streak>=2 and latest_complete and not stale and not adverse and not state.get('pending_due'))
    kind='maintenance' if maintenance else 'reinforcement' if adverse else 'diagnostic' if stale or not daily else 'practice'
    reason='Conferir retenção após bons resultados com convicção em dias espaçados.' if maintenance else 'Reforçar dificuldades nos resultados registrados ou nos sinais de erro informados.' if adverse else 'Conferir retenção após longo período sem uma medição suficiente.' if stale else 'Medir diferentes partes do tema antes de reduzir a prática.'
    if maintenance:
        # Piso de manutenção é uma regra do produto, não um ótimo científico.
        desired=profile.min_block+ceil(params.maintenance_incidence_dose*h)
    elif adverse or stale:
        desired=max(desired,params.diagnostic_dose,profile.min_block)
    available=min(state['total'],desired)
    return {'recommended_questions':desired if state['total']<profile.min_block else available,
            'available_per_block':available,'complement_per_block':max(0,desired-state['total']) if state['total']<profile.min_block else 0,
            'small_bank':state['total']<profile.min_block,'dose_kind':kind,'dose_reason':reason}


def next_stage(state,as_of=None):
    days=state['spacing']['block_days']
    if as_of: days=[d for d in days if d<as_of]
    if days: return len(days),'Revisão '+str(len(days))
    return 0,'Primeiro contato' if state['status']=='sem_registro' else 'Diagnóstico'


def topic_trajectory(state,profile,start):
    """Só o próximo encontro tem dose; os demais dependem de resultados reais."""
    first=max(start,state.get('theme_review_due') or state.get('next_review') or start,profile.start_date or start)
    number,label=next_stage(state,first)
    horizon_end=min(_date(profile.exam_date),_date(start)+timedelta(days=547))
    q=state.get('theme_recommended_questions',state['recommended_questions'])
    steps=[]
    if _date(first)<=horizon_end:
        steps.append({'stage':label,'review_number':number,'date':_date(first).isoformat(),
                      'questions':q,'cumulative_questions':q,
                      'available_questions':min(q,state['total']),
                      'complement_questions':max(0,q-state['total'])})
        if _date(first)<horizon_end:
            for offset in range(1,5):
                steps.append({'stage':'Revisão '+str(number+offset),'review_number':number+offset,
                              'date':None,'questions':None,'cumulative_questions':None,
                              'available_questions':None,'complement_questions':None})
    return {'topic_id':state['topic_id'],'path':state['path'],'steps':steps,'recommended_total':None,'horizon_end':horizon_end.isoformat(),
            'recorded_attempts':state['recorded_attempts'],'pdf_answered':state['answered_pdf'],
            'available_per_block':min(q,state['total']),
            'complement_per_block':max(0,q-state['total']),
            'assumption':'Próximo bloco com base nos registros atuais. Depois dele, quantidade e intervalo serão recalculados.'}


def trajectory_summary(states,profile,start,calendar):
    booked=defaultdict(lambda:{'questions':0,'contacts':0,'first':None})
    for day in calendar:
        if day['date']>profile.exam_date: continue
        for item in day['items']:
            row=booked[item['topic_id']]
            row['questions']+=item['questions']
            row['contacts']+=1
            if row['first'] is None: row['first']=day['date']
    rows=[]
    for state in states:
        b=booked[state['topic_id']]
        rows.append({'topic_id':state['topic_id'],'Tema':state['path'][-1],'Caminho':' → '.join(state['path']),
                     'Próximo bloco':state.get('theme_recommended_questions',state['recommended_questions']),
                     'Critério':state.get('dose_reason','Conferir o desempenho no próximo bloco.'),'Questões com vaga prevista':b['questions'],
                     'Encontros com vaga prevista':b['contacts'],'Primeira vaga prevista':b['first'],
                     'Feitas em blocos registrados':state['recorded_attempts'],'Respondidas no PDF':state['answered_pdf'],
                     'Complemento por encontro':max(0,state.get('theme_recommended_questions',state['recommended_questions'])-state['total']),
                     'Incidência relativa (%)':100*state['importance']})
    return {'rows':rows,
            'scheduled_questions':sum(r['Questões com vaga prevista'] for r in rows),
            'unscheduled_topics':sum(r['Primeira vaga prevista'] is None for r in rows),
            'small_bank_topics':sum(s['small_bank'] for s in states)}
