"""Jornada descritiva e condicional: contatos previstos não são domínio adquirido."""
from bisect import bisect_right
from collections import defaultdict
from .models import normalize_path
from .planning import _date
from .topic_catalog import is_practice_topic

SNAPSHOT_VERSION=2


def evolution_snapshot(states,sessions,calendar,as_of,max_gap=30,area_results=(),planning_states=()):
    _date(as_of)
    topics=[t for t in states if is_practice_topic(t) and not t.get('historical_aggregate')]
    ids={t['topic_id'] for t in topics}
    by_path={tuple(normalize_path(t['path'])):t['topic_id'] for t in topics}
    # O pai informa somente inclusão em um bloco conjunto. A distribuição por filho é desconhecida.
    joint_groups={t['topic_id']:{'path':list(t['path']),'members':[i for i in t['group_members'] if i in ids]}
                  for t in planning_states if t.get('group_members')}
    joint_by_path={tuple(normalize_path(g['path'])):i for i,g in joint_groups.items()}
    def joint_for_path(path):
        key=tuple(normalize_path(path))
        if key in by_path: return None
        if key not in joint_by_path:
            members=[i for p,i in by_path.items() if len(p)>len(key) and p[:len(key)]==key]
            if not members: return None
            # Histórico de grupos desfeitos continua visível mesmo fora da fronteira atual.
            import json
            group_id='joint:'+json.dumps(list(key),ensure_ascii=False)
            joint_by_path[key]=group_id
            joint_groups[group_id]={'path':list(path),'members':members}
        return joint_by_path[key]
    joint_contacts=defaultdict(list); planned_joint_contacts=defaultdict(list)
    joint_members=set(); joint_attempts=0
    records=[e['entry'] for e in sessions if e['entry']['day']<=as_of]
    entries=[e for e in records if e['kind']=='bloco']
    actual_by_day=defaultdict(int)
    local_ids=set()
    for e in entries:
        actual_by_day[e['day']]+=e['questions']
        key=by_path.get(tuple(normalize_path(e['path'])))
        if key: local_ids.add(key)
        else:
            group_id=joint_for_path(e['path'])
            if group_id:
                joint_contacts[group_id].append(e['day'])
                joint_members.update(joint_groups[group_id]['members'])
                joint_attempts+=e['questions']
    from .exam_practice import area_extra_volume
    for day,n in area_extra_volume(area_results,sessions,as_of).items(): actual_by_day[day]+=n
    actual=sum(actual_by_day.values()); covered=set(local_ids)
    for e in records:
        if e['kind']=='acumulado' and e['questions']>0:
            key=by_path.get(tuple(normalize_path(e['path'])))
            if key: covered.add(key)
    imported_unique=0; evidence=[]; contacts=defaultdict(list)
    safety_n=safety_sum=safety_topics=0; safety_dates=set()
    for t in topics:
        snapshot=t.get('planner_safety') or t.get('planner_snapshot') or {}
        if snapshot.get('observed_date','')>as_of: snapshot={}
        n=snapshot.get('unique_questions',t.get('answered_pdf',0)) or 0
        if not t.get('non_additive'):imported_unique+=n
        if n and not t.get('non_additive') and snapshot.get('confident_accuracy_pct') is not None:
            safety_n+=n; safety_sum+=n*snapshot['confident_accuracy_pct']; safety_topics+=1
            if snapshot.get('observed_date'): safety_dates.add(snapshot['observed_date'])
        if n or t.get('answered_pdf',0): covered.add(t['topic_id'])
        rate=t.get('confidence',{}).get('observed')
        if rate is None: rate=t.get('performance',{}).get('observed')
        source={'acumulado':'Total acumulado informado','observacao':'Observação informada'}.get(t.get('performance_source'),'Blocos no app')
        if rate is None:
            pct=snapshot.get('confident_accuracy_pct')
            rate=pct/100 if pct is not None else None
            source='Segurança acumulada Osler · '+snapshot.get('observed_date','data não informada')
        evidence.append({'topic_id':t['topic_id'],'path':list(t['path']),'importance':t.get('importance',0) or 0,
                         'weak':bool(t.get('low_accuracy')),'rate':rate,'rate_source':source,'last_contact':t.get('last_contact')})
    total=len(topics); covered_now=set(covered); joint_members_now=set(joint_members)
    def point(day,attempts,future,kind):
        return {'date':day,'attempts':attempts,'future_attempts':future,'covered':len(covered),
                'coverage_pct':100*len(covered)/total if total else 0,'kind':kind,
                'included_jointly':len(joint_members),'joint_only':len(joint_members-covered),
                'joint_attempts':joint_attempts}
    points=[point(as_of,actual,0,'Realizado')]; cumulative=actual; future=0
    for day in sorted(calendar,key=lambda d:d['date']):
        if day['date']<as_of: continue
        future+=day['questions']; cumulative+=day['questions']
        for item in day['items']:
            if item.get('questions',0)<=0: continue
            if item['topic_id'] in ids:
                covered.add(item['topic_id']); contacts[item['topic_id']].append(day['date'])
            else:
                group_id=item['topic_id'] if item['topic_id'] in joint_groups else joint_for_path(item['path']) if item.get('path') else None
                if group_id:
                    planned_joint_contacts[group_id].append(day['date'])
                    joint_members.update(joint_groups[group_id]['members'])
                    joint_attempts+=item['questions']
        points.append(point(day['date'],cumulative,future,'Previsto'))
    history=[]; running=0
    for day,q in sorted(actual_by_day.items()):
        running+=q; history.append({'date':day,'attempts':running,'kind':'Realizado'})
    if not history or history[-1]['date']<as_of: history.append({'date':as_of,'attempts':actual,'kind':'Realizado'})
    days=sorted(actual_by_day)
    milestones=[('first','Primeiro registro',bool(entries or actual),days[0] if days else None,
                 next((p['date'] for p in points if p['attempts']>0),None),'Um bloco registrado no app'),
                ('questions100','100 respostas',actual>=100,next((p['date'] for p in history if p['attempts']>=100),None),
                 next((p['date'] for p in points if p['attempts']>=100),None),'Inclui questões novas e repetidas no app'),
                ('days3','3 dias de prática',len(days)>=3,days[2] if len(days)>=3 else None,None,'Dias com estudo realmente registrado; não precisam ser seguidos'),
                ('coverage25','25% dos temas',points[0]['coverage_pct']>=25,None,
                 next((p['date'] for p in points if p['coverage_pct']>=25),None),'Cobertura reconhecida nos arquivos e registros; não significa domínio')]
    achievements=[{'id':key,'title':title,'earned':earned,'earned_date':date,
                   'projected_date':None if earned else projected,'description':description} for key,title,earned,date,projected,description in milestones]
    return {'as_of':as_of,'total_topics':total,'actual_attempts':actual,'actual_days':len(days),'imported_unique':imported_unique,
            'non_additive_topics':sum(bool(t.get('non_additive')) for t in topics),
            'imported_safety':{'topics':safety_topics,'questions_per_topic_sum':safety_n,'weighted_pct':safety_sum/safety_n if safety_n else None,'dates':sorted(safety_dates)},
            'points':points,'history':history,'topics':evidence,'covered_now':points[0]['covered'],
            'covered_ids_now':sorted(covered_now),
            'joint_groups':joint_groups,'joint_member_ids_now':sorted(joint_members_now),
            'joint_contacts':{i:sorted(set(days)) for i,days in joint_contacts.items()},
            'planned_joint_contacts':{i:sorted(set(days)) for i,days in planned_joint_contacts.items()},
            'planned_contacts':dict(contacts),'achievements':achievements,'max_gap':max_gap}


def evolution_attention(snapshot,at):
    _date(at)
    if at<snapshot['as_of']: raise ValueError('Escolha hoje ou uma data futura.')
    covered=set(snapshot['covered_ids_now']); result=[]
    jointly=set(snapshot.get('joint_member_ids_now',[]))
    for group_id,dates in snapshot.get('planned_joint_contacts',{}).items():
        if bisect_right(dates,at): jointly.update(snapshot['joint_groups'][group_id]['members'])
    for t in snapshot['topics']:
        dates=snapshot['planned_contacts'].get(t['topic_id'],[])
        index=bisect_right(dates,at)
        if index: covered.add(t['topic_id'])
        last=dates[index-1] if index else t['last_contact']
        age=(_date(at)-_date(last)).days if last else None
        if t['weak']: kind,reason,factor='Reforçar','Última medição fraca; contatos previstos não comprovam melhora.',3
        elif t['topic_id'] not in covered and t['topic_id'] in jointly:
            kind,reason,factor='Medir subtema','Incluído em bloco conjunto; quantidade e rendimento individuais ainda não medidos.',2
        elif t['topic_id'] not in covered: kind,reason,factor='Não visto','Sem questões registradas ou primeiro bloco previsto até esta data.',2
        elif age is not None and age>snapshot['max_gap']: kind,reason,factor='Retomar contato',f'Sem contato previsto há {age} dias nesta data.',1.5
        elif t['rate'] is None: kind,reason,factor='Medir rendimento','Há contato, mas falta medição de rendimento utilizável.',.8
        else: continue
        result.append({**t,'kind':kind,'reason':reason,'last_contact_in_scenario':last,'score':t['importance']*factor})
    return sorted(result,key=lambda r:(-r['score'],r['path']))
