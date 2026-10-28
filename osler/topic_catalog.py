"""Unidades específicas: folhas e temas com conteúdo próprio não coberto pelos filhos."""
from .models import normalize_path
from collections import defaultdict


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


def planning_frontier(topics,minimum=10):
    return [{**t,'rollup':False} for t in topics if is_practice_topic(t)]
