"""Fronteira alternativa de agenda; as fontes e evidências dos filhos são preservadas."""
from .models import normalize_path
from .incidence import prepare_incidence
from .topic_catalog import is_practice_topic
from .balanced_reviews import confirmed_deficit


def key(path):
    return tuple(normalize_path(path))


def grouping_candidates(topics,datasets,profile,day,blocked=()):
    contexts=prepare_incidence(datasets,list(profile.institution_weights),day)
    # Usa os mesmos conjuntos escolhidos pelo planejamento, sem somá-los.
    targets=frozenset(normalize_path(list(profile.institution_weights)))
    singles=[d for d in contexts if len(d['institutions'])==1]
    if targets and len(singles)==len(targets): contexts=singles
    elif targets: contexts=[d for d in contexts if frozenset(normalize_path(d['institutions']))==targets]
    elif contexts: contexts=[max(contexts,key=lambda d:(d['observed_date'],d['id']))]
    leaves=[t for t in topics if is_practice_topic(t)]
    path_keys={t['topic_id']:key(t['path']) for t in topics}
    rows=[]
    for parent in topics:
        p=path_keys[parent['topic_id']]
        if len(p)<3 or parent.get('is_leaf',True): continue
        members=[t for t in leaves if path_keys[t['topic_id']][:len(p)]==p and path_keys[t['topic_id']]!=p]
        if len(members)<2: continue
        evidence=[]; known=True; important=[]
        for d in contexts:
            index=d['_index']; descendants=[q for q in index if q[:len(p)]==p and len(q)>len(p)]
            roots=[q for q in descendants if not any(q[:i] in index for i in range(len(p)+1,len(q)))]
            total=index[p]['value'] if p in index else sum(index[q]['value'] for q in roots)
            if not roots and p not in index: known=False
            for t in members:
                q=key(t['path']); value=index.get(q,{}).get('value')
                if value is None: known=False
                elif d['unit']=='questoes' and value>=profile.min_block: important.append(t['path'][-1])
            area=p[:1]
            area_roots=[q for q in index if q[:1]==area and not any(q[:i] in index for i in range(1,len(q)))]
            area_total=sum(index[q]['value'] for q in area_roots)
            evidence.append({'dataset_id':d['id'],'institutions':d['institutions'],'unit':d['unit'],'value':total,
                             'area_total':area_total,'observed_area_share_pct':100*total/area_total if area_total>=total and area_total>0 else None,
                             'partial':p not in index and any(key(t['path']) not in index for t in members)})
        reason=None
        if parent.get('partial_subdivision'): reason='Categoria tem conteúdo próprio: soma dos filhos não cobre o pai.'
        elif len(members)>12: reason='Categoria ampla: analise categorias mais específicas.'
        elif not contexts: reason='Falta uma fonte de incidência aplicável.'
        elif any(d['unit']!='questoes' for d in contexts): reason='Percentuais sem denominador comum: mantenha separado.'
        elif important: reason='Preservar blocos próprios: '+', '.join(sorted(set(important)))+'.'
        elif any(t['topic_id'] in blocked for t in members): reason='Há agendamento individual ou retorno vinculado a preservar.'
        elif any(d['value']<=0 for d in evidence): reason='Sem incidência positiva em todos os contextos.'
        # Não conciliar dados hierárquicos contraditórios por subtração truncada.
        if not reason:
            for d in contexts:
                idx=d['_index']
                for q in [q for q in idx if q[:len(p)]==p]:
                    kids=[r for r in idx if len(r)>len(q) and r[:len(q)]==q and not any(r[:i] in idx for i in range(len(q)+1,len(r)))]
                    child_total=sum(idx[r]['value'] for r in kids)
                    if kids and (child_total>idx[q]['value']+1e-8 or known and abs(child_total-idx[q]['value'])>1e-8):
                        reason='Contagem do pai diverge da soma dos descendentes.';break
        rows.append({'topic_id':parent['topic_id'],'path':parent['path'],'members':[t['topic_id'] for t in members],
                     'member_paths':[t['path'] for t in members],'evidence':evidence,'eligible':reason is None,
                     'complete_incidence':known,
                     'reason':reason or ('Agrupamento com incidência parcial da fonte; filhos sem dado permanecem desconhecidos.' if not known else 'Subtemas pequenos com incidência conhecida; um bloco misto reduz a fragmentação.'),
                     'savings':len(members)-1})
    # Prefere grupos mais específicos; não seleciona pai e filho simultaneamente.
    chosen=[]
    for row in sorted(rows,key=lambda r:(-len(r['path']),-r['savings'],r['path'])):
        row['recommended']=row['eligible'] and not any(set(row['members'])&set(c['members']) for c in chosen)
        if row['recommended']: chosen.append(row)
    return rows


def grouped_frontier(topics,profile,candidates):
    if profile.grouping_mode=='osler': return [{**t,'rollup':False} for t in topics if is_practice_topic(t)]
    wanted={key(p) for p in profile.grouping_paths}
    selected=[r for r in candidates if r['eligible'] and (r['recommended'] if profile.grouping_mode=='balanced' else key(r['path']) in wanted)]
    excluded={i for r in selected for i in r['members']}
    by_id={t['topic_id']:t for t in topics}
    groups=[]
    for r in selected:
        parent=by_id[r['topic_id']]
        groups.append({**parent,'rollup':True,'is_practice_unit':True,'group_members':r['members'],
                       'group_member_paths':r['member_paths'],'group_evidence':r['evidence']})
    return [{**t,'rollup':False} for t in topics if is_practice_topic(t) and t['topic_id'] not in excluded]+groups


def protect_group_evidence(states,leaf_states):
    """Uma média ou contato de um filho não comprova retenção dos demais."""
    index={t['topic_id']:t for t in leaf_states}
    for t in states:
        if not t.get('group_members'): continue
        members=[index[i] for i in t['group_members'] if i in index]
        t['group_details']=[{'path':m['path'],'last_contact':m['last_contact'],'priority':m['priority'],
                            'next_review':m['next_review'],'accuracy':m['performance']['observed']} for m in members]
        # Antes de um bloco conjunto, o contato mais antigo é a referência conservadora.
        if not t['review_committed']:
            known=[m['last_contact'] for m in members if m['last_contact']]
            t['last_contact']=min(known) if len(known)==len(members) else None
            due=[m['next_review'] for m in members if m['next_review']]
            if due: t['next_review']=t['theme_review_due']=t['allocation_due']=min(due)
            t['score']=sum(m['score'] for m in members)
            t['priority']=min((m['priority'] for m in members),key={'urgente':0,'alta':1,'normal':2}.get)
            t['evidence_priority']=t['priority']
            deadlines=[m['initial_contact_deadline'] for m in members if m.get('initial_contact_deadline')]
            t['initial_contact_deadline']=min(deadlines) if deadlines else None
        t['domain_evidence']='Resultado conjunto não comprova domínio de cada subtema'
        t['reason']='Bloco misto: conferir todos os subtemas do grupo'
        # Um acerto conjunto não recupera uma dificuldade individual ainda presente.
        # Propagar proteção operacional, sem misturar amostras nem atribuir contato aos filhos.
        adverse=[]
        for m in members:
            snapshot=m.get('planner_safety') or {}
            safety=snapshot.get('confident_accuracy_pct')
            target=m.get('target_accuracy',90)
            safety_deficit=bool(m.get('planner_snapshot_current') and snapshot.get('unique_questions',0)>=5 and
                                safety is not None and safety<target)
            measured_deficit=confirmed_deficit(m['performance'],target/100,m.get('minimum_block',10))
            if (m.get('manual_adverse') or m.get('registered_error') or m.get('linked_adverse') or
                m.get('low_accuracy') or m.get('alert_signal') or m.get('reported_difficulty') or
                measured_deficit or safety_deficit): adverse.append(m)
        t['group_member_adverse']=[m['topic_id'] for m in adverse]
        protected=[m for m in members if m in adverse or m['priority']!='normal' or m['evidence_priority']!='normal']
        if protected:
            rank={'urgente':0,'alta':1,'normal':2}
            t['priority']=min([t['priority']]+[m['priority'] for m in protected],key=rank.get)
            t['evidence_priority']=min([t['evidence_priority']]+[m['evidence_priority'] for m in protected],key=rank.get)
            for field in ('next_review','theme_review_due','allocation_due','retention_due'):
                dates=[t.get(field)]+[m.get(field) or m.get('theme_review_due') for m in protected]
                t[field]=min((d for d in dates if d),default=None)
            t['score']=max(t['score'],sum(m['score'] for m in protected))
        if adverse:
            t['review_interval_days']=min([t['review_interval_days']]+[m['review_interval_days'] for m in adverse])
            t['learning_state']='alerta'
            t['dose_kind']='reinforcement'
            dose=max([t['theme_recommended_questions']]+[m['theme_recommended_questions'] for m in adverse])
            t['theme_recommended_questions']=t['recommended_questions']=min(t['total'],dose)
            t['dose_reason']=t['reason']='Reforçar dificuldade individual ainda presente: '+', '.join(m['path'][-1] for m in adverse)
