"""Unidades específicas: folhas e temas com conteúdo próprio não coberto pelos filhos."""
from .models import normalize_path,stable_topic_id
from collections import defaultdict


FRAGMENT_GROUP_LABEL='Subtemas menores'


def is_practice_topic(topic):
    return topic.get('is_practice_unit',topic.get('is_leaf',True))


def mark_practice_units(topics):
    """Não reescreve contagens originais nem atribui aos filhos o conteúdo do pai."""
    paths={tuple(normalize_path(t['path'])):t for t in topics}
    children_by_parent=defaultdict(list)
    for path,topic in paths.items():
        if len(path)>1:children_by_parent[path[:-1]].append(topic)
    result=[]
    for topic in topics:
        path=tuple(normalize_path(topic['path']))
        children=children_by_parent[path]
        direct=max(0,topic['total']-sum(t['total'] for t in children)) if children else topic['total']
        # Área/especialidade continuam sendo navegação; um tema de terceiro nível
        # pode ter questões próprias além de um pequeno desdobramento terminal.
        own=bool(not topic.get('is_leaf',True) and len(path)>=3 and children and direct>0)
        result.append({**topic,'is_practice_unit':topic.get('is_leaf',True) or own,
                       **({'direct_questions':direct,'partial_subdivision':True,
                           'evidence_scope':'inclusive_parent','non_additive':True} if own else {})})
    return result


def classify_theme_context(topics,indexes,as_of,sessions=(),contacts=()):
    """Descreve continuidade na categoria sem atribuir contato ou rendimento à folha."""
    started={tuple(normalize_path(event['entry']['path'])) for event in sessions if event['entry']['day']<=as_of}
    started.update(tuple(normalize_path(path)) for path,day in contacts if day<=as_of)
    for topic in topics:
        snapshot=topic.get('planner_snapshot') or {}
        if (topic.get('answered_pdf') or topic.get('studied_cards') or
                snapshot.get('observed_date','9999')<=as_of and
                (snapshot.get('unique_questions') or snapshot.get('last_contact'))):
            started.add(tuple(normalize_path(topic['path'])))
    started_nodes=defaultdict(int)
    for path in started:
        for depth in range(1,len(path)+1):
            started_nodes[path[:depth]]+=1
    institution_paths=set().union(*indexes)
    result=[]
    for topic in topics:
        path=topic['path']
        key=tuple(normalize_path(path))
        fallback=len(key) if len(key)<=2 or not topic.get('is_leaf',True) else len(key)-1
        depth=next((size for size in range(len(key),0,-1) if key[:size] in institution_paths),fallback)
        leaf_started=key in started
        result.append({**topic,'theme_path':list(path[:depth]),'theme_started':started_nodes[key[:depth]]>leaf_started,
                       'leaf_started':leaf_started})
    return result


def fragment_group_topic(theme_path,members):
    path=[*theme_path,FRAGMENT_GROUP_LABEL]
    return {'topic_id':stable_topic_id(path),'path':path,'theme_path':theme_path,'fragment_group':True,
            'is_practice_unit':True,'is_leaf':False,'rollup':False,
            'total':sum(t['total'] for t in members),'answered_pdf':sum(t.get('answered_pdf',0) for t in members),
            'studied_cards':sum(t.get('studied_cards') or 0 for t in members),
            'pdf_accuracy':{'value':None,'operator':None,'raw':'-'},
            'report_date':min((t['report_date'] for t in members if t.get('report_date')),default=None),
            'theme_started':any(t.get('theme_started',False) for t in members),
            'group_members':[t['topic_id'] for t in members],
            'group_member_paths':[t['path'] for t in members],
            'group_member_topics':[{k:t[k] for k in ('topic_id','path','total')} for t in members]}


def fragment_history(topics,sessions):
    """Mantém a composição que o usuário estudou, mesmo após outra importação."""
    by_path={tuple(normalize_path(t['path'])):t for t in topics}
    groups={}
    for event in sessions:
        entry=event['entry']
        paths=entry.get('fragment_members')
        if not paths:
            continue
        path=entry['path']
        key=tuple(normalize_path(path))
        if key not in groups:
            members=[by_path.get(tuple(normalize_path(p)),{'topic_id':stable_topic_id(p),'path':p,'total':0}) for p in paths]
            group=fragment_group_topic(path[:-1],members)
            groups[key]={**group,'path':path,'topic_id':stable_topic_id(path),
                         'group_member_paths':paths,'historical_aggregate':True,'is_practice_unit':False}
        groups[key]['total']=max(groups[key]['total'],entry['questions'],1)
    return groups


def planning_frontier(topics,minimum=10,*,blocked=(),recorded=None,reserved_paths=()):
    """Agrupa somente folhas sem atividade própria na fronteira já disponível."""
    blocked=set(blocked)
    recorded=recorded or {}
    occupied={tuple(normalize_path(t['path'])) for t in topics}
    occupied.update(tuple(normalize_path(path)) for path in reserved_paths)
    practice=[t for t in topics if is_practice_topic(t)]
    by_path={tuple(normalize_path(t['path'])):t for t in practice}
    candidates=defaultdict(list)
    for topic in practice:
        path=topic['path']
        theme=topic.get('theme_path') or (path[:-1] if len(path)>2 else path)
        if (not topic.get('is_leaf',True) or topic['topic_id'] in blocked or
                topic.get('leaf_started',bool(topic.get('answered_pdf') or topic.get('studied_cards'))) or
                not 0<topic['total']<minimum or len(theme)>=len(path)):
            continue
        key=tuple(normalize_path(path))
        if any(parent in by_path and by_path[parent]['total']>=minimum for parent in (key[:i] for i in range(1,len(key)))):
            continue
        candidates[tuple(normalize_path(theme))].append(topic)
    groups=[]
    for members in candidates.values():
        if sum(t['total'] for t in members)<minimum:
            continue
        first=members[0]
        theme=first.get('theme_path') or first['path'][:-1]
        group=fragment_group_topic(theme,members)
        key=tuple(normalize_path(group['path']))
        if key in occupied:
            continue
        old=recorded.get(key)
        if old and {tuple(normalize_path(p)) for p in old['group_member_paths']}!={tuple(normalize_path(p)) for p in group['group_member_paths']}:
            continue
        groups.append(group)
    assigned={i for group in groups for i in group['group_members']}
    return [{**t,'rollup':t.get('rollup',False)} for t in practice if t['topic_id'] not in assigned]+groups
