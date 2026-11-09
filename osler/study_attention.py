"""Leitura descritiva da atenção por tema, sem recalcular a política de estudo."""
from .incidence import prepare_incidence
from .models import normalize_path
from .planning import _date
from .review_policy import review_order


GROUPS=('Atenção','Nunca praticados','Sem contato','Todos')


def _incidences(path, prepared):
    key=tuple(normalize_path(path)); result=[]
    for dataset in prepared:
        selected=next((dataset['_index'][key[:n]] for n in range(len(key),0,-1)
                       if key[:n] in dataset['_index']),None)
        if selected is not None:
            result.append({'value':selected['value'],'unit':dataset['unit'],
                           'institutions':list(dataset['institutions']),
                           'observed_date':dataset['observed_date'],'dataset_id':dataset['id'],
                           'path':list(selected['path']),
                           'exact':len(selected['path'])==len(path)})
    return result


def _accuracy(state):
    stats=state.get('performance') or {}; source=state.get('performance_source')
    # A primeira base já foi selecionada pela política: novas, mistas ou acumulado.
    if stats.get('exact_n') and stats.get('observed') is not None:
        return {'rate':stats['observed'],'n':stats['exact_n'],'mode':source,
                'interval':stats.get('interval'),'approximate':False}
    repeated=state.get('repeated') or {}
    if repeated.get('exact_n') and repeated.get('observed') is not None:
        return {'rate':repeated['observed'],'n':repeated['exact_n'],'mode':'repetidas',
                'interval':repeated.get('interval'),'approximate':False}
    if stats.get('reported_n') and stats.get('reported_percent') is not None:
        return {'rate':stats['reported_percent'],'n':stats['reported_n'],'mode':source,
                'interval':None,'approximate':True}
    return {'rate':None,'n':None,'mode':None,'interval':None,'approximate':False}


def _conviction(state,day):
    stats=state.get('confidence') or {}
    if stats.get('exact_n') and stats.get('observed') is not None:
        return {'rate':stats['observed'],'n':stats['exact_n'],
                'source':'App · '+str(state.get('confidence_source') or 'modalidade não informada')}
    snapshot=state.get('planner_safety') or {}
    if snapshot.get('observed_date','9999')<=day and snapshot.get('confident_accuracy_pct') is not None:
        return {'rate':snapshot['confident_accuracy_pct']/100,'n':snapshot.get('unique_questions'),
                'source':'Osler · retrato de '+snapshot['observed_date']}
    return {'rate':None,'n':None,'source':None}


def attention_overview(view,datasets,day):
    """Produz linhas específicas completas, preservando bases e ordem existentes.

    Somente leitura: view e datasets não são alterados. Ausência de incidência,
    acerto ou contato continua None. Pais e áreas não viram recomendações.
    """
    states=view.get('states',[])
    paths={tuple(normalize_path(t['path'])) for t in states}
    targets=list(view.get('profile',{}).get('institution_weights',{}))
    prepared=prepare_incidence(datasets,targets,day)
    contexts=view.get('incidence',{}).get('contexts')
    if contexts is not None:
        ids={c['dataset_id'] for c in contexts}
        prepared=[d for d in prepared if d['id'] in ids]
    rows=[]
    for state in states:
        path=state['path']; key=tuple(normalize_path(path))
        if (len(path)<2 or state.get('historical_aggregate') or state.get('rollup')
                or state.get('is_leaf') is False
                or any(len(p)>len(key) and p[:len(key)]==key for p in paths)):
            continue
        incidence=_incidences(path,prepared)
        exact_incident=any(i['exact'] and i['value']>0 for i in incidence)
        snapshot=state.get('planner_safety') or {}
        if snapshot.get('observed_date','9999')>day: snapshot={}
        accuracy=_accuracy(state)
        limited=bool(accuracy['rate'] is not None and (accuracy['approximate'] or
                     accuracy['n']<(state.get('minimum_block') or 10)))
        practiced=bool(state.get('answered_pdf') or state.get('recorded_attempts') or
                        snapshot.get('unique_questions') or
                        (state.get('baseline') or {}).get('questions') or
                        (state.get('performance') or {}).get('reported_n'))
        last=state.get('last_contact')
        if last and last>day: last=None
        age=(_date(day)-_date(last)).days if last else None
        interval=state.get('review_interval_days')
        stale=age is not None and interval is not None and age>=interval
        due=state.get('next_review')
        adverse=bool(state.get('low_accuracy') or state.get('manual_adverse') or
                     state.get('registered_error') or state.get('reported_difficulty') or
                     state.get('alert_signal') or state.get('linked_adverse') or
                     state.get('evidence_priority') in {'alta','urgente'})
        needed=bool(adverse or stale or state.get('pending_due') or due and due<=day or
                    not practiced and exact_incident or
                    practiced and (last is None or accuracy['rate'] is None or limited))
        reasons=[]
        if adverse: reasons.append(state.get('reason') or 'Há um sinal de dificuldade registrado')
        if not practiced:
            reasons.append('Sem questões registradas; há incidência específica na tabela' if exact_incident
                           else 'Sem questões registradas; incidência específica não informada')
        if stale: reasons.append(f'{age} dias sem contato; intervalo atual de {interval} dias')
        elif last is None: reasons.append('Último contato desconhecido; não é atraso medido')
        if state.get('pending_due'): reasons.append(f"{state['pending_due']} respostas com retorno para hoje ou antes")
        elif due and due<=day: reasons.append('Revisão prevista para '+due)
        if practiced and accuracy['rate'] is None: reasons.append('Acerto objetivo ainda sem medição nesta base')
        if limited:
            reasons.append('Percentual aproximado; confirmar com contagens exatas' if accuracy['approximate']
                           else f"Amostra pequena nesta modalidade (n={accuracy['n']}); ampliar a medição")
        if not reasons: reasons.append(state.get('reason') or 'Manter os contatos previstos no plano')
        rows.append({'topic_id':state['topic_id'],'path':list(path),'incidences':incidence,
                     'accuracy':accuracy,'conviction':_conviction(state,day),
                     'last_contact':last,'days_without_contact':age,'next_review':due,
                     'review_interval_days':interval,'never_practiced':not practiced,
                     'never_seen':state.get('status')=='sem_registro',
                     'incident_unpracticed':not practiced and exact_incident,
                     'stale':stale,'attention':needed,'reason':' · '.join(dict.fromkeys(reasons)),
                     'questions':state.get('recommended_questions') or state.get('minimum_block') or 10,
                     'importance':state.get('importance',0),
                     '_order':review_order(state,day)})
    rows.sort(key=lambda r:r['_order'])
    return {'rows':rows,'counts':{g:len(attention_filter(rows,g)) for g in GROUPS},
            'incident_unpracticed':sum(r['incident_unpracticed'] for r in rows),
            'unknown_contact':sum(r['last_contact'] is None for r in rows)}


def attention_filter(rows,group='Atenção',search=''):
    if group not in GROUPS: raise ValueError('Grupo de atenção desconhecido.')
    query=normalize_path([search.strip()])[0] if search.strip() else ''
    selected=[r for r in rows if (group=='Todos' or group=='Atenção' and r['attention'] or
            group=='Nunca praticados' and r['never_practiced'] or
            group=='Sem contato' and (r['stale'] or r['last_contact'] is None)) and
            (not query or query in ' '.join(normalize_path(r['path'])))]
    if group=='Nunca praticados':selected.sort(key=lambda r:(not r['incident_unpracticed'],-r['importance'],r['_order']))
    return selected


def attention_table(rows):
    """Incidências numéricas ordenáveis, sem somar fontes ou atribuir valores de pais."""
    contexts={i['dataset_id']:i for row in rows for i in row['incidences']}
    columns={}
    for dataset_id,i in contexts.items():
        label='Incidência (%)' if i['unit']=='percentual' else 'Incidência'
        if sum(c['unit']==i['unit'] for c in contexts.values())>1:
            label+=' · '+', '.join(i['institutions'])+f' · tabela #{dataset_id}'
        elif i['unit']=='questoes':label+=' bruta'
        columns[dataset_id]=label
    empty={label:None for label in columns.values()} or {'Incidência bruta':None}
    result=[]
    for row in rows:
        a=row['accuracy']; c=row['conviction']; incidence=dict(empty); sources=[]
        for i in row['incidences']:
            value=f"{i['value']:g}"+('%' if i['unit']=='percentual' else ' questões')
            scope='tema' if i['exact'] else 'grupo '+i['path'][-1]+' (não individual)'
            institutions=', '.join(i['institutions'])
            if i['exact']:incidence[columns[i['dataset_id']]]=i['value']
            sources.append(f"{institutions}: {value} · {scope} · {i['observed_date']} · tabela #{i['dataset_id']}")
        result.append({'Tema':row['path'][-1],'Caminho':' → '.join(row['path']),
                       **incidence,
                       'Fonte da incidência':' | '.join(sources) or 'Sem tabela aplicável',
                       'Acerto':(f"{100*a['rate']:.1f}% · n={a['n']} · {a['mode']}"+
                                 (' · aproximado' if a['approximate'] else ' · contagens exatas')) if a['rate'] is not None else 'Sem medição',
                       'Convicção':f"{100*c['rate']:.1f}% · n={c['n'] if c['n'] is not None else 'não informado'} · {c['source']}" if c['rate'] is not None else 'Não informada',
                       'Último contato':row['last_contact'] or 'Desconhecido',
                       'Dias sem contato':row['days_without_contact'],
                       'Próxima revisão':row['next_review'] or 'Sem data definida',
                       'Por que olhar':row['reason']})
    return result
