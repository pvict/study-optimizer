"""Política por tema: acerto objetivo, amostra e contatos reais; não calibrada."""
from collections import defaultdict
from datetime import timedelta
from math import ceil
from .planning import _date

STRATEGIES={'legacy_v1':'Anterior · convicção como critério central','balanced_v2':'Equilibrada · acerto, amostra e retenção'}
COORDINATION_DAYS=2


def daily_evidence(entries,as_of):
    groups=defaultdict(list)
    for e in entries:
        if e['kind']=='bloco' and not e.get('review_of') and (not as_of or e['day']<=as_of): groups[e['day']].append(e)
    result=[]
    for day,blocks in sorted(groups.items()):
        selected=[]
        for mode in ('novas','mistas','repetidas'):
            selected=[e for e in blocks if e['mode']==mode and (e.get('correct') is not None or e.get('percent') is not None)]
            if selected: break
        if not selected: continue
        n=sum(e['questions'] for e in selected)
        correct=sum(e['correct'] if e.get('correct') is not None else e['questions']*e['percent']/100 for e in selected)
        result.append({'day':day,'n':n,'rate':correct/n,'correct':correct,
                       'exact':all(e.get('correct') is not None for e in selected),'mode':mode})
    return result


def confirmed_deficit(stats,target,minimum=10):
    return bool(stats['exact_n']>=minimum and stats['interval'] and stats['interval'][1]<target)


def unresolved_linked_failure(entries,pending):
    by_id={e.get('_session_id'):e for e in entries if e.get('_session_id')}
    unresolved=set()
    for lot in pending:
        key=lot['session_id']; seen=set()
        while key in by_id and key not in seen:
            seen.add(key); unresolved.add(key); key=by_id[key].get('review_of')
    return any(key in unresolved and e.get('review_of') and e.get('correct') is not None and e['correct']<e['questions'] for key,e in by_id.items())


def balanced_spacing(entries,profile,as_of,incidence_strength=0):
    from .adaptive_planning import posterior
    p=profile.parameters; interval=p.first_interval; streak=0; last=None; days=[]
    for e in daily_evidence(entries,as_of):
        if e['n']<profile.min_block: continue
        days.append(e['day'])
        elapsed=(_date(e['day'])-_date(last)).days if last else None
        spaced=elapsed is None or elapsed>=max(p.spaced_min_days,interval)
        if e['rate']<p.raw_low_threshold:
            streak=0; interval=p.failure_interval
        elif e['rate']>=p.intermediate_threshold and e['exact']:
            if not last or not streak or elapsed>max(profile.recent_days,2*interval):
                streak=1; interval=p.first_interval
            elif spaced:
                stats=posterior(int(e['correct']),e['n'])
                quality=max(0,min(1,(stats['mean']-p.failure_threshold)/max(.01,profile.target_accuracy/100-p.failure_threshold)))
                streak+=1; interval=ceil(interval*(1+quality))
                if streak==2: interval=min(interval,p.second_interval)
        else:
            streak=0; interval=p.first_interval
        interval=min(profile.max_contact_gap,interval)
        last=e['day']
    return {'interval':interval,'next_due':(_date(last)+timedelta(days=interval)).isoformat() if last else None,
            'base_interval':interval,'ease':p.default_ease,'streak':streak,'last_evidence_day':last,
            'block_days':days,'incidence_strength':incidence_strength,
            'method':'Acertos objetivos e encontros espaçados; política por tema não calibrada'}


def balanced_dose(state,profile,entries,as_of):
    from .adaptive_planning import posterior,_series
    p=profile.parameters; target=profile.target_accuracy/100
    repeated=_series([e for e in entries if e['kind']=='bloco' and e['mode']=='repetidas' and not e.get('review_of') and
        (not as_of or 0<=(_date(as_of)-_date(e['day'])).days<=profile.recent_days)])
    stats=state['performance'] if state['performance']['reported_n'] else repeated
    daily=[e for e in daily_evidence(entries,as_of) if e['n']>=profile.min_block]
    latest=daily[-1] if daily else None
    if not stats['reported_n'] and latest:
        stats=posterior(int(latest['correct']),latest['n']) if latest['exact'] else {
            'exact_n':0,'mean':latest['rate'],'sd':.25,'interval':None,'reported_n':latest['n']}
    measured=bool(stats.get('reported_n',stats['exact_n']))
    rate=stats['mean']
    if latest:
        last_mean=posterior(int(latest['correct']),latest['n'])['mean'] if latest['exact'] else latest['rate']
        rate=min(rate,last_mean)  # sucesso em repetidas não apaga dificuldade em novas
    gap=max(0,target-rate)/target
    uncertainty=min(1,stats['sd']/.25)
    strength=state.get('incidence_strength',0)
    desired=ceil(profile.min_block+p.gap_dose*gap+p.uncertainty_dose*uncertainty+p.incidence_dose*strength)
    stale=bool(latest and as_of and (_date(as_of)-_date(latest['day'])).days>min(profile.recent_days,2*state['review_interval_days']))
    critical=bool(state.get('manual_adverse') or state.get('registered_error'))
    weak=bool(state.get('linked_adverse') or state.get('alert_signal') or measured and (stats.get('observed',rate) is not None and stats.get('observed',rate)<p.raw_low_threshold or confirmed_deficit(stats,target,profile.min_block)) or latest and latest['rate']<p.raw_low_threshold)
    maintenance=bool(state['spacing']['streak']>=2 and measured and stats['exact_n']>=p.sufficient_sample and
                     not(critical or weak or stale or state.get('pending_due')))
    kind='diagnostic' if not measured or stale else 'reinforcement' if critical or weak else 'maintenance' if maintenance else 'practice'
    if kind=='diagnostic' or critical: desired=max(desired,p.diagnostic_dose)
    if maintenance: desired=profile.min_block+ceil(p.gap_dose*gap+p.maintenance_incidence_dose*strength)
    desired=max(profile.min_block,desired); available=min(state['total'],desired)
    reasons={'diagnostic':'Medir o tema com questões representativas; o histórico disponível não comprova retenção atual.',
             'reinforcement':'Reforçar dificuldades objetivas ou erros registrados; a dose considera amostra e incidência.',
             'maintenance':'Conferir retenção após bons resultados em encontros realmente espaçados.',
             'practice':'Ampliar a amostra do tema; resultado abaixo da meta não equivale a fracasso confirmado.'}
    return {'recommended_questions':desired if state['total']<profile.min_block else available,
            'available_per_block':available,'complement_per_block':max(0,desired-state['total']) if state['total']<profile.min_block else 0,
            'small_bank':state['total']<profile.min_block,'dose_kind':kind,'dose_reason':reasons[kind]}


def coordinate_due(due,pending,profile,as_of,last,protected=False):
    if not due or not pending or protected: return due,None
    for lot in sorted(pending,key=lambda q:q['due_date']):
        candidate=max(lot['due_date'],as_of)
        if abs((_date(candidate)-_date(due)).days)>COORDINATION_DAYS: continue
        if candidate>profile.exam_date or last and (_date(candidate)-_date(last)).days>profile.max_contact_gap: continue
        return candidate,{'original_due':due,'date':candidate,'lot_due':lot['due_date']}
    return due,None


def review_parts(item,day):
    left=item['questions']; lots=[]
    for lot in item.get('pending_reviews',[]):
        if lot['due_date']>day or not left: continue
        amount=min(left,lot['questions'])
        lots.append({**lot,'questions':amount}); left-=amount
    return {'lots':lots,'lot_questions':item['questions']-left,'complement':left}
