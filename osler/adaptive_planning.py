"""Alocação explícita de prática; incerteza estatística não é previsão de aprovação."""
from collections import defaultdict
from dataclasses import replace
import math
from datetime import timedelta

from .classification import wilson_interval
from .guide import daily_blocks
from .incidence import prepare_incidence
from .models import normalize_path
from .planning import _date, _number
from .topic_spacing import spacing_state, learning_state
from .review_queue import review_queue
from .topic_trajectory import question_dose, next_stage
from .study_allocation import category_allocation,practice_minimum,practice_capacity
from .review_policy import initial_interval,domain_evidence,review_order
from .balanced_reviews import confirmed_deficit,coordinate_due,unresolved_linked_failure,daily_evidence,operational_contact_due


def posterior(correct, n):
    _number(n,'Amostra',integer=True)
    _number(correct,'Acertos',integer=True,maximum=n)
    a,b=1+correct,1+n-correct
    return {'exact_n':n,'exact_correct':correct,'observed':correct/n if n else None,
            'mean':a/(a+b),'sd':math.sqrt(a*b/((a+b)**2*(a+b+1))),
            'interval':[x/100 for x in wilson_interval(100*correct/n,n)] if n else None}


def incidence_weights(topics,datasets,institution_weights,as_of,parameters=None):
    from .algorithm_parameters import V1
    parameters=parameters or V1
    keys={t['topic_id']:tuple(normalize_path(t['path'])) for t in topics}
    if not topics: return {'weights':{},'warnings':[],'coverage':0,'contexts':[]}
    targets={normalize_path([k])[0]:v for k,v in institution_weights.items()}
    prepared=prepare_incidence(datasets,list(targets),as_of)
    groups={frozenset(normalize_path(d['institutions'])):d for d in prepared}
    contexts,warnings=[],[]
    uniform_mass=0
    if targets:
        total=sum(targets.values())
        if all(frozenset([k]) in groups for k in targets):
            contexts=[(groups[frozenset([k])],v/total) for k,v in targets.items()]
        elif frozenset(targets) in groups:
            contexts=[(groups[frozenset(targets)],1)]
            if len(targets)>1: warnings.append('Tabela conjunta: seus membros não podem receber pesos individuais sem tabelas separadas.')
        else:
            contexts=[(groups[frozenset([k])],v/total) for k,v in targets.items() if frozenset([k]) in groups]
            uniform_mass=1-sum(w for _,w in contexts)
            warnings.append('Faltam tabelas para parte das instituições. Essa parcela usa exploração uniforme, não incidência presumida.')
    elif prepared:
        contexts=[(max(prepared,key=lambda d:(d['observed_date'],d['id'])),1)]
        if len(prepared)>1: warnings.append('Sem pesos definidos, usei somente o conjunto mais recente; não somei conjuntos sobrepostos.')
    else:
        uniform_mass=1
        warnings.append('Sem incidência aplicável: distribuição exploratória uniforme, sem tratar ausência como zero.')
    weights={key:uniform_mass/len(topics) for key in keys}
    covered=set()
    for dataset,context_weight in contexts:
        index=dataset['_index']
        chosen={key:next((path[:i] for i in range(len(path),0,-1) if path[:i] in index),None) for key,path in keys.items()}
        children=defaultdict(list)
        for path in index:
            parent=next((path[:i] for i in range(len(path)-1,0,-1) if path[:i] in index),None)
            if parent: children[parent].append(path)
        counts=defaultdict(int)
        for path in chosen.values():
            if path: counts[path]+=1
        residual={p:max(0,index[p]['value']-sum(index[c]['value'] for c in children[p])) for p in counts}
        raw={key:residual[path]/counts[path] if path else 0 for key,path in chosen.items()}
        rolled=set()
        for t in topics:
            if not t.get('rollup'): continue
            key=t['topic_id']
            path=keys[key]
            if path in index:
                raw[key]=index[path]['value']
                rolled.add(key)
            else:
                descendants=[p for p in index if len(p)>len(path) and p[:len(path)]==path]
                roots=[p for p in descendants if not any(p[:n] in index for n in range(len(path),len(p)))]
                if roots:
                    raw[key]+=sum(index[p]['value'] for p in roots)
                    rolled.add(key)
        missing=[key for key,path in chosen.items() if path is None and key not in rolled]
        covered.update(key for key,path in chosen.items() if path is not None or key in rolled)
        if missing:
            exploration=sum(raw.values())*parameters.exploration_reserve/len(missing)
            for key in missing: raw[key]=exploration
            warnings.append('Incidência parcial: temas sem linha receberam uma pequena reserva exploratória; contagens de pais foram repartidas entre folhas.')
        total=sum(raw.values())
        if not total: warnings.append('Consulta sem peso positivo utilizável: usei exploração uniforme, sem interpretar isso como ausência de cobrança futura.')
        for key in weights:
            weights[key]+=context_weight*(raw[key]/total if total else 1/len(topics))
    return {'weights':weights,'warnings':list(dict.fromkeys(warnings)), 'coverage':len(covered)/len(topics),'known_topic_ids':sorted(covered),
            'contexts':[{'dataset_id':d['id'],'institutions':d['institutions'],'observed_date':d['observed_date'],'weight':w,'unit':d['unit']} for d,w in contexts]}


def _series(entries):
    exact=[e for e in entries if e.get('correct') is not None]
    n=sum(e['questions'] for e in exact)
    stats=posterior(sum(e['correct'] for e in exact),n)
    total=sum(e['questions'] for e in entries)
    stats['reported_n']=total
    stats['approximate']=any(e.get('percent') is not None for e in entries)
    stats['reported_percent']=(sum(e['correct'] if e.get('correct') is not None else e['questions']*e['percent']/100 for e in entries)/total) if total else None
    confident=[e for e in entries if e.get('confident_correct') is not None]
    stats['confidence']=posterior(sum(e['confident_correct'] for e in confident),sum(e['questions'] for e in confident))
    if not n and total:
        stats['mean']=stats['reported_percent']
        stats['sd']=.25
    return stats


def topic_states(topics,sessions,datasets,institution_weights,as_of,profile,contacts=None,error_paths=(),return_dates=None):
    day=_date(as_of)
    params=profile.parameters
    balanced=profile.review_strategy=='balanced_v2'
    incidence=incidence_weights(topics,datasets,institution_weights,as_of,params)
    by_path=defaultdict(list)
    for event in sessions:
        e=event['entry']
        if balanced: e={**e,'_session_id':event.get('session_id')}
        if e['day']<=as_of: by_path[tuple(normalize_path(e['path']))].append(e)
    contact_paths={}
    for path,contact in contacts or []:
        key=tuple(normalize_path(path))
        if contact<=as_of: contact_paths[key]=max(contact,contact_paths.get(key,contact))
    states=[]
    queued=review_queue(sessions,return_dates) if all('session_id' in s for s in sessions) else []
    base_profile=profile
    error_keys={tuple(normalize_path(p)) for p in error_paths}
    for topic in topics:
        profile=replace(base_profile,target_accuracy=base_profile.target_for_area(topic['path'][0]))
        key=tuple(normalize_path(topic['path']))
        registered_error=key in error_keys or bool(topic.get('rollup') and any(p[:len(key)]==key for p in error_keys))
        snapshot=topic.get('planner_snapshot')
        if snapshot and snapshot['observed_date']>as_of: snapshot=None
        safety_rate=snapshot['confident_accuracy_pct']/100 if snapshot and snapshot['confident_accuracy_pct'] is not None else None
        entries=[e for p,values in by_path.items() if p[:len(key)]==key for e in values] if topic.get('rollup') and not topic.get('group_members') else by_path[key]
        evidence_pending=[q for q in queued if tuple(normalize_path(q['path']))==key or topic.get('rollup') and not topic.get('group_members') and tuple(normalize_path(q['path']))[:len(key)]==key]
        pending=evidence_pending if profile.return_mode=='linked' else []
        linked_adverse=balanced and unresolved_linked_failure(entries,evidence_pending,profile)
        committed=bool(pending or topic.get('cards_reduced_day') or any(e['kind']=='bloco' and (not profile.start_date or e['day']>=profile.start_date) for e in entries))
        recent=[e for e in entries if e['kind']=='bloco' and (day-_date(e['day'])).days<=profile.recent_days]
        fresh=[e for e in recent if e['mode']=='novas']
        mixed=[e for e in recent if e['mode']=='mistas']
        repeated=_series([e for e in recent if e['mode']=='repetidas'])
        baselines=[e for e in entries if e['kind']=='acumulado']
        baseline=max(baselines,key=lambda e:e['day']) if baselines else None
        manual=topic.get('manual_context') or {}
        manual_adverse=manual.get('erros_criticos') is True or manual.get('erros_recorrentes') is True
        difficulty_day=manual.get('data_observacao')
        reported_difficulty=bool(manual.get('dificuldade')=='alta' and difficulty_day and
            0<=(day-_date(difficulty_day)).days<=min(profile.recent_days,profile.max_contact_gap) and
            not any(e['kind']=='bloco' and e['day']>difficulty_day and e['questions']>=profile.min_block and
                    e.get('correct') is not None and not e.get('review_of') for e in entries))
        manual_percent=manual.get('acerto_recente') if manual.get('acerto_recente') is not None else manual.get('acerto_primeira_tentativa')
        manual_baseline={'questions':manual.get('questoes_distintas') or 0,'correct':None,'percent':manual_percent} if manual_percent is not None and manual.get('questoes_distintas') else None
        primary=fresh or mixed or ([baseline] if baseline and baseline['mode']!='repetidas' else [])
        if not primary and manual_baseline: primary=[manual_baseline]
        performance=_series(primary)
        source='novas' if fresh else 'mistas' if mixed else 'acumulado' if baseline and primary else 'observacao' if primary else 'pdf' if topic['answered_pdf'] else 'sem_medicao'
        mean=performance['mean']
        if not primary and topic['pdf_accuracy']['operator']=='=' and topic['pdf_accuracy']['value'] is not None:
            mean=topic['pdf_accuracy']['value']/100
        contact_dates=[e['day'] for e in entries if e['kind']!='acumulado']+[e['last_contact'] for e in entries if e.get('last_contact')]
        known=contact_paths.get(tuple(normalize_path(topic['path'])))
        if known: contact_dates.append(known)
        if snapshot and snapshot['last_contact']: contact_dates.append(snapshot['last_contact'])
        last=max(contact_dates) if contact_dates else None
        age=(day-_date(last)).days if last else None
        seen=bool(topic['answered_pdf'] or topic.get('studied_cards') or entries or last or snapshot and snapshot['unique_questions'])
        observed=performance['reported_percent']
        # Sinais adversos alteram urgência, mantendo cada modalidade fora do posterior das outras.
        signals=[]
        for mode in ('novas','mistas','repetidas'):
            series=_series([e for e in recent if e['mode']==mode and not e.get('review_of')])
            below=series['reported_percent'] is not None and (series['reported_percent']<params.raw_low_threshold or confirmed_deficit(series,profile.target_accuracy/100,profile.min_block)) if balanced else series['reported_percent'] is not None and series['reported_percent']<profile.target_accuracy/100
            if series['reported_n']>=(profile.min_block if balanced else 5) and below:
                signals.append({'mode':mode,'n':series['reported_n'],'percent':series['reported_percent']})
        alert=min(signals,key=lambda s:s['percent']) if signals else None
        # Segurança recuperada é sinal descritivo separado, nunca amostra binomial de tentativas novas.
        snapshot_current=bool(snapshot and (day-_date(snapshot['observed_date'])).days<=profile.recent_days and
                              not any(e['day']>snapshot['observed_date'] for e in fresh+mixed))
        safety_alert=bool(snapshot_current and safety_rate is not None and snapshot['unique_questions']>=5 and safety_rate<profile.target_accuracy/100)
        scheduling_observed=min(x for x in (observed,alert['percent'] if alert else None) if x is not None) if observed is not None or alert else None
        interval=params.failure_interval if observed is not None and observed<params.raw_low_threshold else params.second_interval if observed is not None and observed<profile.target_accuracy/100 else params.max_contact_gap if performance['exact_n']>=params.sufficient_sample else params.first_interval
        importance=incidence['weights'][topic['topic_id']]
        incidence_strength=importance/max(incidence['weights'].values()) if incidence['contexts'] and max(incidence['weights'].values()) else 0
        spacing=spacing_state(entries,profile,as_of,incidence_strength)
        if entries: interval=spacing['interval'] if spacing['last_evidence_day'] else min(interval,spacing['interval'])
        else: interval=max(1,math.ceil(interval/(1+.5*incidence_strength)))
        if not committed: interval=initial_interval(snapshot if snapshot_current else None,profile,incidence_strength)
        if alert and not balanced: interval=min(interval,params.failure_interval if alert['percent']<params.raw_low_threshold else params.second_interval)
        if balanced:
            latest_primary=next((e for e in reversed(daily_evidence(entries,as_of,profile.min_block)) if e['mode']==source and e['n']>=profile.min_block),None)
            if latest_primary and latest_primary['rate']<params.failure_threshold: interval=min(interval,params.failure_interval)
        if balanced and (manual_adverse or registered_error): interval=min(interval,params.failure_interval)
        if reported_difficulty: interval=min(interval,params.first_interval)
        if linked_adverse: interval=min(interval,params.first_interval)
        days_left=max(1,(_date(profile.exam_date)-day).days)
        interval=min(interval,max(1,days_left//4))
        interval=min(interval,profile.max_contact_gap)
        reduced_due=bool(topic.get('cards_reduced_day') and (day-_date(topic['cards_reduced_day'])).days>=14
                         and (last is None or last<topic['cards_reduced_day'] or age>=14))
        if topic.get('cards_reduced_day'): interval=min(interval,14)
        evidence_age=(day-_date(spacing['last_evidence_day'])).days if spacing['last_evidence_day'] else age
        overdue=evidence_age is not None and evidence_age>=interval
        pending_due=sum(q['questions'] for q in pending if q['due_date']<=as_of)
        confidence=performance['confidence']
        confidence_source=source
        if not confidence['exact_n'] and repeated['confidence']['exact_n']:
            confidence=repeated['confidence']
            confidence_source='repetidas'
        confidence_rate=confidence['observed']
        adverse_urgent=(observed is not None and performance['reported_n']>=10 and observed<.6 or
                        alert and alert['n']>=10 and alert['percent']<.6 or
                        manual.get('erros_criticos') is True or manual.get('erros_recorrentes') is True or
                        not balanced and confidence_rate is not None and confidence_rate<.6 or
                        safety_alert and snapshot['unique_questions']>=10 and safety_rate<.6 and (incidence_strength>=.1 or not incidence['contexts']))
        below_goal=confirmed_deficit(performance,profile.target_accuracy/100,profile.min_block) if balanced else observed is not None and performance['reported_n']>=10 and observed<profile.target_accuracy/100
        evidence_priority='urgente' if adverse_urgent else 'alta' if (alert or safety_alert or below_goal or linked_adverse) else 'normal'
        if reported_difficulty and evidence_priority=='normal':evidence_priority='alta'
        temporal_priority='urgente' if committed and age is not None and age>=2*interval else 'alta' if reduced_due or overdue or pending_due else 'normal'
        priority=min((evidence_priority,temporal_priority),key={'urgente':0,'alta':1,'normal':2}.get)
        status='sem_registro' if not seen else 'diagnostico' if not primary or last is None else 'revisao'
        uncertainty=performance['sd'] if primary else .25
        gap=max(0,profile.target_accuracy/100-min(mean,scheduling_observed if scheduling_observed is not None else mean))
        if snapshot_current and safety_rate is not None and not primary: gap=max(0,profile.target_accuracy/100-safety_rate)
        if safety_alert: gap=max(gap,profile.target_accuracy/100-safety_rate)
        urgency=1+min(age/max(1,interval),2) if age is not None else 1
        importance=incidence['weights'][topic['topic_id']]
        imported_pending=bool(snapshot_current and snapshot.get('pending_reviews'))
        score=max(importance,.000001)*(gap+profile.uncertainty_weight*uncertainty+.1*imported_pending+.01)*urgency
        reason='Começar um tema sem estudo registrado' if not seen else 'Medir rendimento e confirmar o último contato' if status=='diagnostico' else 'Reforçar desempenho abaixo da meta' if observed is not None and observed<profile.target_accuracy/100 else 'Revisitar pelo tempo sem contato' if overdue else 'Manter prática espaçada e conferir retenção'
        if balanced and primary and not below_goal: reason='Ampliar a amostra e conferir retenção em um contato espaçado'
        if reduced_due: reason='Revisitar por questões após redução seletiva de cartões'
        if alert: reason=f"Reforçar erros recentes em questões {alert['mode']} ({100*alert['percent']:.0f}% em {alert['n']} questões)"
        if not balanced and confidence_rate is not None and confidence_rate<.6: reason='Recuperar acerto com convicção abaixo de 60%'
        if pending_due: reason=f'Revisar {pending_due} respostas ainda sem convicção, com retorno marcado'
        if safety_alert and not pending_due: reason=f"Reforçar segurança acumulada da Osler ({100*safety_rate:.1f}% em {snapshot['unique_questions']} questões distintas; retrato de {snapshot['observed_date']})"
        if manual_adverse: reason='Reforçar erros críticos ou recorrentes informados por você'
        elif reported_difficulty: reason='Dificuldade alta relatada em '+difficulty_day+'; retomar e medir o rendimento'
        if linked_adverse: reason='Há erros em retornos vinculados ainda não recuperados; eles não entram na taxa de questões novas'
        theme_contacts=[e['day'] for e in entries if e['kind']!='acumulado' and not e.get('review_of')]+[e['last_contact'] for e in entries if e.get('last_contact') and not e.get('review_of')]
        if known: theme_contacts.append(known)
        if snapshot and snapshot['last_contact']: theme_contacts.append(snapshot['last_contact'])
        theme_last=max(theme_contacts,default=None)
        due=(_date(spacing['last_evidence_day'])+timedelta(days=interval)).isoformat() if spacing['last_evidence_day'] else (_date(theme_last)+timedelta(days=interval)).isoformat() if theme_last else None
        coordination=None
        if balanced:
            due,coordination=coordinate_due(due,pending,profile,as_of,spacing['last_evidence_day'] or theme_last,
                protected=bool(manual_adverse or registered_error or linked_adverse or topic.get('cards_reduced_day') or observed is not None and observed<params.raw_low_threshold or alert and alert['percent']<params.raw_low_threshold))
        theme_due=due
        if pending: due=min([q['due_date'] for q in pending]+([due] if due else []))
        if reduced_due:
            reduction_return=(_date(topic['cards_reduced_day'])+timedelta(days=14)).isoformat()
            due=min(due,reduction_return) if due else reduction_return
        retention_due=due
        if due and profile.start_date: due=max(due,profile.start_date)
        raw_signal=observed if observed is not None else topic['pdf_accuracy']['value']/100 if topic['answered_pdf'] and topic['pdf_accuracy']['operator']=='=' and topic['pdf_accuracy']['value'] is not None else None
        if alert: raw_signal=min(raw_signal,alert['percent']) if raw_signal is not None else alert['percent']
        low_accuracy=not balanced and confidence_rate is not None and confidence_rate<.6 or raw_signal is not None and raw_signal<.6 or safety_alert and safety_rate<.6
        evidence=performance if balanced else confidence
        phase=learning_state({'seen':seen,'n':evidence['exact_n'],'rate':evidence['observed'],'lower':evidence['interval'][0] if evidence['interval'] else None,
                              'source':source if balanced else confidence_source,'overdue':overdue,'pending_due':pending_due,'raw_rate':raw_signal},profile)
        if balanced and phase=='dominado' and spacing['streak']<2: phase='aprendendo'
        if linked_adverse: phase='alerta'
        if safety_alert and safety_rate<.6: phase='alerta'
        if not committed and seen and not low_accuracy and not reduced_due: phase='aprendendo'
        if manual_adverse or registered_error: phase='alerta'
        if reported_difficulty: phase='alerta'
        new_since_pdf=sum(e['questions'] for e in entries if e['kind']=='bloco' and e['mode']=='novas' and (not topic['report_date'] or e['day']>topic['report_date']))
        available=max(0,topic['total']-topic['answered_pdf']-new_since_pdf)
        balance_uncertain=not bool(topic['report_date'])
        if snapshot and snapshot['observed_date']>=(topic['report_date'] or ''):
            after_snapshot=sum(e['questions'] for e in entries if e['kind']=='bloco' and e['mode']=='novas' and e['day']>snapshot['observed_date'])
            available=max(0,snapshot['available_questions']-snapshot['unique_questions']-after_snapshot)
            balance_uncertain=bool(snapshot['unique_questions']<topic['answered_pdf'] or
                                   any(e['kind']=='bloco' and e['mode']=='novas' and e['day']==snapshot['observed_date'] for e in entries))
        states.append({**topic,'performance':performance,'repeated':repeated,'baseline':baseline,'performance_source':source,'alert_signal':alert,
                       'confidence':confidence,'confidence_source':confidence_source,'learning_state':phase,'low_accuracy':bool(low_accuracy),'next_review':due,'pending_due':pending_due,'pending_reviews':pending,'spacing':spacing,
                       'last_contact':last,'days_without_contact':age,'review_interval_days':interval,'priority':priority,'evidence_priority':evidence_priority,'status':status,'target_accuracy':profile.target_accuracy,'minimum_block':profile.min_block,
                       'retention_due':retention_due,'theme_review_due':theme_due,
                       'review_committed':committed,'review_origin':'retorno de respostas' if pending else 'acompanhamento de cartões' if topic.get('cards_reduced_day') else 'blocos registrados' if committed else 'fila inicial',
                       'initial_contact_deadline':(_date(last)+timedelta(days=profile.max_contact_gap)).isoformat() if not committed and seen and last else None,
                       'domain_evidence':domain_evidence(seen,snapshot if snapshot_current else None,phase=='dominado',bool(low_accuracy or manual_adverse or registered_error),profile.target_accuracy),
                       'importance':importance,'incidence_strength':incidence_strength,'incidence_known':topic['topic_id'] in incidence.get('known_topic_ids',[]),'score':score,'reason':reason,'available_new':available,'bank_balance_uncertain':balance_uncertain,
                       'planner_safety':snapshot,'planner_snapshot_current':snapshot_current,'manual_adverse':manual_adverse,'registered_error':registered_error,
                       'reported_difficulty':reported_difficulty,
                       'recorded_attempts':sum(e['questions'] for e in entries if e['kind']=='bloco'),
                       'incidence_warnings':incidence['warnings'],'incidence_coverage':incidence['coverage']})
        if balanced:
            states[-1].update(review_coordination=coordination,activity_day=as_of,
                linked_adverse=linked_adverse,
                coordinated_credits=[{'date':e['day'],'questions':e['questions']} for e in entries if e['kind']=='bloco' and e.get('review_of') and theme_due and abs((_date(e['day'])-_date(theme_due)).days)<=2],
                completed_today=sum(e['questions'] for e in entries if e['kind']=='bloco' and e['day']==as_of),
                representative_today=sum(e['questions'] for e in entries if e['kind']=='bloco' and e['day']==as_of and not e.get('review_of')))
        states[-1].update(question_dose(states[-1],profile,entries,as_of))
        states[-1]['theme_recommended_questions']=states[-1]['recommended_questions']
        if balanced:
            operational_due=operational_contact_due(states[-1],profile,entries,as_of)
            if operational_due!=states[-1]['theme_review_due']:
                states[-1]['theme_review_due']=operational_due
                states[-1]['next_review']=min([q['due_date'] for q in pending]+([operational_due] if operational_due else []),default=None)
        from .study_capacity import practice_state
        states[-1].update(practice_state(states[-1],as_of,profile))
        states[-1]['is_new_for_day']=not(topic['answered_pdf'] or topic.get('studied_cards') or baselines or manual_baseline or snapshot and snapshot['unique_questions'] or any(d<as_of for d in contact_dates))
        number,stage=next_stage(states[-1],as_of)
        states[-1].update({'review_number':number,'stage':stage})
    # Destaque operacional da fila inicial limitado à capacidade aproximada de uma semana.
    # O foco ajuda a navegar; não pode apagar uma evidência adversa já calculada.
    initial=sorted([t for t in states if not t['review_committed'] and t['status']!='sem_registro'],key=lambda t:review_order(t,as_of))
    weekly_slots=max(0,round(base_profile.max_topics*(1-base_profile.new_share)*7))
    for rank,t in enumerate(initial,1):
        focus='alta' if rank<=weekly_slots else 'normal'
        t.update(initial_rank=rank,initial_focus=rank<=weekly_slots,
                 priority=min((t['evidence_priority'],focus),key={'urgente':0,'alta':1,'normal':2}.get))
    for t in states:
        if t['registered_error']:
            t['priority']=min((t['priority'],'alta'),key={'urgente':0,'alta':1,'normal':2}.get)
            t['evidence_priority']=min((t['evidence_priority'],'alta'),key={'urgente':0,'alta':1,'normal':2}.get)
            t['reason']='Erros recorrentes registrados neste tema'
            t['learning_state']='alerta'
    return sorted(states,key=lambda t:review_order(t,as_of))


def allocate_day(states,profile,minutes,kind,sessions,as_of,question_target=None,extra_topics=None,reservations=None,capacity_limits=None,capacity_states=None,swaps=(),allocation_credits=None,unavailable_ids=()):
    profile.validate()
    not_started=bool(profile.start_date and as_of<profile.start_date)
    if not_started: kind='descanso'; extra_topics=None; reservations=None
    swaps=[] if not_started else swaps
    unavailable_ids=set(unavailable_ids)
    if extra_topics: extra_topics=[e for e in extra_topics if e['topic_id'] not in unavailable_ids]
    excluded={topic_id for row in swaps for topic_id in row['excluded_ids']}|unavailable_ids
    swapped_ids={row['topic_id'] for row in swaps}
    if question_target is None: _number(minutes,'Tempo disponível',integer=True,positive=True,maximum=720)
    else: _number(question_target,'Meta de questões',integer=True,maximum=1000)
    if kind not in {'normal','plantao','descanso'}: raise ValueError('Tipo de dia inválido.')
    today=[s['entry'] for s in sessions if s['entry']['day']==as_of and s['entry']['kind']!='acumulado']
    from .study_swaps import quota_entries
    allocation_sessions=[{**s,'entry':{**s['entry'],'questions':allocation_credits.get(s.get('session_id'),s['entry']['questions'])}} for s in sessions] if allocation_credits else sessions
    allocation_today,quota_adjustments=quota_entries(allocation_sessions,swaps,as_of)
    done=sum(e['questions'] for e in today)
    credited_done=sum(e['questions'] for e in allocation_today)
    spent=sum(e['minutes'] if e.get('minutes') else e['questions']*profile.minutes_per_question for e in today)
    extras=[]
    if question_target is None:
        blocks=daily_blocks(minutes,kind)
        question_minutes=sum(b['minutes'] for b in blocks if b['kind'] in {'questoes','erros'})
        reserves=sum(b['minutes'] for b in blocks if b['kind'] not in {'questoes','erros'})
        original_budget=min(profile.max_questions,math.floor(question_minutes/profile.minutes_per_question))
        budget=min(max(0,original_budget-done),max(0,math.floor((question_minutes-spent)/profile.minutes_per_question)))
        target=original_budget
    else:
        reserves=0
        batches=extra_topics or []
        credits={t['extra_id']:0 for t in batches}
        dated=[s for s in sessions if s['entry']['day']==as_of and s['entry']['kind']=='bloco']
        for event in sorted(dated,key=lambda s:s.get('first_event_id',s.get('id',0))):
            left=event['entry']['questions']
            for batch in batches:
                if event.get('first_event_id',event.get('id',0))<=batch['after_event_id']: continue
                direct=normalize_path(event['entry']['path'])==normalize_path(batch['path'])
                exchanged=sum(c['questions'] for r in swaps if batch['extra_id'] in r.get('extra_ids',[]) for c in r.get('credits',[])+r.get('prior_credits',[]) if c['session_id']==event['session_id'])
                if not direct and not exchanged: continue
                used=min(left,batch['requested']-credits[batch['extra_id']],left if direct else exchanged)
                credits[batch['extra_id']]+=used
                left-=used
        grouped={}
        for t in batches:
            if t['topic_id'] not in grouped: grouped[t['topic_id']]={**t,'remaining':0}
            grouped[t['topic_id']]['remaining']+=t['requested']-credits[t['extra_id']]
        target=max(question_target+sum(t['requested'] for t in batches),credited_done+sum(t['remaining'] for t in grouped.values())) if batches else question_target
        budget=max(0,target-credited_done)
        for t in grouped.values():
            if t['topic_id'] in excluded|swapped_ids: continue
            q=min(t['remaining'],t['total'],budget-sum(e['questions'] for e in extras))
            if q: extras.append({**t,'questions':q,'new_questions':min(q,t['available_new']),
                                  'repeat_questions':max(0,q-t['available_new']),'added_by_user':True,'reason':'Revisão que você adicionou para adiantar o estudo'})
        budget-=sum(e['questions'] for e in extras)
    if kind=='descanso': budget=0; extras=[]
    recovered=[]
    by_id={t['topic_id']:t for t in states}
    pinned=[]
    for row in swaps:
        t=by_id.get(row['topic_id'])
        if not t or t['topic_id'] in unavailable_ids or not row.get('extra_only') and sum(not p.get('is_extra_swap') for p in pinned)>=profile.max_topics: continue
        q=min(row['remaining'],practice_capacity(t,profile),max(0,budget-sum(p['questions'] for p in pinned)))
        if q:
            pinned.append({**t,'questions':q,'new_questions':min(q,t['available_new']),
                           'repeat_questions':max(0,q-t['available_new']),'added_by_user':False,
                           'day_swap_id':row['slot_id'],'swap_from_path':row['from_path'],
                           'day_swap_origin_id':row.get('origin_id',row['topic_id']),
                           'swap_quota_path':row.get('quota_path',row['from_path']),'is_extra_swap':row.get('extra_only',False),
                           'swap_extra_ids':row.get('extra_ids',[]),
                           'reason':'Tema escolhido para substituir '+row['from_path'][-1]+' apenas neste dia'})
    budget-=sum(p['questions'] for p in pinned)
    base_pins=[p for p in pinned if not p.get('is_extra_swap')]
    from .study_allocation import topic_is_new
    group_targets={'new':round((question_target if question_target is not None else target)*profile.new_share)}
    group_targets['reviews']=(question_target if question_target is not None else target)-group_targets['new']
    for e in allocation_today+[{'path':p['swap_quota_path'],'questions':p['questions']} for p in base_pins]:
        t=next((t for t in states if normalize_path(t['path'])==normalize_path(e['path'])),None)
        if t:
            group='new' if topic_is_new(t) else 'reviews'
            group_targets[group]=max(0,group_targets[group]-e['questions'])
    for row in sorted(reservations or [],key=lambda r:r['date']):
        t=by_id.get(row['topic_id'])
        if not t or t['topic_id'] in excluded|swapped_ids or row['date']>as_of or len(recovered)+len(base_pins)>=profile.max_topics: continue
        group='new' if topic_is_new(t) else 'reviews'
        remaining_budget=max(0,budget-sum(r['questions'] for r in recovered))
        group_budget=remaining_budget if row.get('manual_date') or row.get('daily_proposal') or row.get('swap_return') or row.get('return_unavailable') or row.get('final_review') or row.get('correction') or profile.workload_mode=='adaptive' and group=='reviews' else group_targets[group]
        q=min(row['remaining'],t['total'] if row.get('correction') else practice_capacity(t,profile),group_budget,remaining_budget)
        if q:
            group_targets[group]=max(0,group_targets[group]-q)
            recovered.append({**t,'questions':q,'new_questions':min(q,t['available_new']),'repeat_questions':max(0,q-t['available_new']),
                              'added_by_user':False,'rescheduled':not row.get('daily_proposal',False),'daily_proposal_preserved':bool(row.get('daily_proposal')),'reschedule_date':row['date'],'original_due':row['original_due'],
                              'swap_return':row.get('swap_return'),
                              'return_unavailable':bool(row.get('return_unavailable')),
                              'correction':bool(row.get('correction')),'source_exam_key':row.get('source_exam_key'),
                              'reason':'Retorno adiado por indisponibilidade na Osler' if row.get('return_unavailable') else 'Prática dos temas errados no simulado' if row.get('correction') else 'Data escolhida na prévia do rodízio' if row.get('manual_date') else 'Bloco já previsto para hoje; as questões excedentes não o substituem' if row.get('daily_proposal') else 'Recuperação reagendada; atraso original preservado'})
    budget-=sum(r['questions'] for r in recovered)
    recovery_ids={r['topic_id'] for r in recovered}
    extra_counts={t['topic_id']:t['questions'] for t in extras}
    minimum=min(profile.min_block,budget)
    from .study_capacity import capacity_policy
    allocated_questions={}
    for item in recovered+base_pins+extras:
        allocated_questions[item['topic_id']]=allocated_questions.get(item['topic_id'],0)+item['questions']
    candidates,allocation_profile,capacity=capacity_policy(capacity_states if capacity_states is not None else states,profile,as_of,budget,question_target if question_target is not None else target,capacity_limits,
        eligible_ids={t['topic_id'] for t in states if t['topic_id'] not in recovery_ids|excluded|swapped_ids and
                      (not t.get('reschedule_date') or t['reschedule_date']<=as_of)},
        allocated_questions=allocated_questions,available_slots=max(0,profile.max_topics-len(recovered)-len(base_pins)),
        new_done_questions=max(0,round((question_target if question_target is not None else target)*profile.new_share)-group_targets['new']))
    if swaps and not swapped_ids & unavailable_ids:
        latest=max(swaps,key=lambda r:r.get('id',0))
        if 'allowed_peers' in latest:
            active_targets={r['origin_id']:r['topic_id'] for r in swaps if 'origin_id' in r}
            peers={active_targets.get(origin,origin) for origin in latest['peer_origins']} if 'peer_origins' in latest else set(latest['allowed_peers'])
            candidates=[t for t in states if t['topic_id'] in peers]
            share=latest.get('allocation_share',profile.new_share) if profile.new_share==latest.get('reference_share') else profile.new_share
            allocation_profile=replace(profile,new_share=share)
            capacity.update(effective_share=share,user_swaps=True,deferred_admissions=0)
    candidate_ids={t['topic_id'] for t in candidates}
    candidates=[{**t,'intake_protected':t['topic_id']==capacity.get('protected_intake_topic') or t['topic_id'] in capacity.get('protected_new_topic_ids',[])} for t in states if t['topic_id'] in candidate_ids]
    available=[{**t,'allocation_capacity':practice_capacity(t,profile)-extra_counts.get(t['topic_id'],0)} for t in candidates
               if t['topic_id'] not in recovery_ids|excluded|swapped_ids and (not t.get('reschedule_date') or t['reschedule_date']<=as_of) and
               (not t.get('allocation_due',t.get('next_review')) or t.get('allocation_due',t.get('next_review'))<=as_of) and
               t['total']>0 and t['total']-extra_counts.get(t['topic_id'],0)>=max(1,min(practice_minimum(t,minimum),t['recommended_questions']) if t.get('allow_small_lot') else practice_minimum(t,minimum))]
    available.sort(key=lambda t:review_order(t,as_of))
    virtual=[{'path':r.get('swap_quota_path',r['path']),'questions':r['questions']} for r in recovered+base_pins]
    selected,counts,distribution=category_allocation(available,states,replace(allocation_profile,max_topics=max(0,profile.max_topics-len(recovered)-len(base_pins))),budget,question_target if question_target is not None else target,allocation_today+virtual)
    for adjustment in quota_adjustments:
        source=next((t for t in states if t['path']==adjustment['source_path']),None)
        actual=next((t for t in states if t['path']==adjustment['path']),None)
        if source is None or actual is None: continue
        old='new' if topic_is_new(source) else 'reviews'; new='new' if topic_is_new(actual) else 'reviews'
        if old!=new:
            distribution['done_'+old]-=adjustment['questions']; distribution['done_'+new]+=adjustment['questions']
            distribution['adjusted']=True
    for row in recovered+base_pins:
        group='new' if topic_is_new(row) else 'reviews'
        source=next((s for s in states if s['path']==row.get('swap_quota_path',row['path'])),row)
        source_group='new' if topic_is_new(source) else 'reviews'
        distribution['done_'+source_group]-=row['questions']
        distribution['planned_'+group]+=row['questions']
        if group!=source_group: distribution['adjusted']=True
    items=[{**t,'questions':counts[t['topic_id']], 'added_by_user':False,'new_questions':min(counts[t['topic_id']],t['available_new']),
            'repeat_questions':max(0,counts[t['topic_id']]-t['available_new'])} for t in selected if counts[t['topic_id']]]
    for item in items:
        if item.get('preventive_priority'):
            item['reason']=f"Revisão antecipada em {item['anticipated_days']}dia(s) para evitar acúmulo previsto" if item.get('anticipated_days') else 'Revisão priorizada pelo plano preventivo'
    items+=recovered+pinned
    combined={i['topic_id']:i for i in items}
    for extra in extras:
        if extra['topic_id'] in combined:
            current=combined[extra['topic_id']]
            current.update({'questions':current['questions']+extra['questions'],'added_by_user':True,'extra_pending':extra['questions']})
            current['new_questions']=min(current['questions'],current['available_new'])
            current['repeat_questions']=current['questions']-current['new_questions']
        else:
            extra['extra_pending']=extra['questions']
            items.append(extra)
    total=sum(i['questions'] for i in items)
    from .planner_snapshot import planner_supply
    bookings={r['topic_id']:r for r in reservations or []}
    for item in items:
        if topic_is_new(item) and item['questions']>item['total']:
            item['external_bank_questions']=item['questions']-item['new_questions']
            item['repeat_questions']=0
        row=bookings.get(item['topic_id']) if item.get('rescheduled') or item.get('daily_proposal_preserved') else None
        completed=sum(e['questions'] for e in today if e['kind']=='bloco' and normalize_path(e['path'])==normalize_path(item['path']))
        required=item['questions']+completed
        if row and 'questions' in row:
            required=row['questions'];completed=max(0,required-row['remaining'])
        item['planner_supply']=planner_supply(item,required,completed,as_of)
    order={'urgente':0,'alta':1,'normal':2}
    items.sort(key=lambda t:(not t.get('rescheduled',False),*review_order(t,as_of)))
    capacity['unused_questions']=max(0,target-done-total)
    return {'items':items,'questions':total,'capacity':capacity,'done_questions':done,'spent_minutes':spent,'reserves_minutes':reserves,
            'planned_minutes':spent+reserves+total*profile.minutes_per_question,'budget':budget,'minutes_per_question':profile.minutes_per_question,
            'kind':kind,'date':as_of,'target_accuracy':profile.target_accuracy,'available_minutes':minutes,
            'not_started':not_started,'start_date':profile.start_date,
            'target_questions':0 if kind=='descanso' else target,'base_questions':question_target if question_target is not None else target,
            'extra_questions':sum(t['requested'] for t in extra_topics or []),
            'overrun_questions':max(0,target-(question_target or target)-sum(t['requested'] for t in extra_topics or [])),
            'excess_done_questions':max(0,done-credited_done),'credited_done_questions':credited_done,
            'allocation_credits':dict(allocation_credits or {}),
            'mode':'questions' if question_target is not None else 'time','distribution':distribution}
