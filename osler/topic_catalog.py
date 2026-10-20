"""Somente temas específicos são unidades de prática; pais servem para navegação."""


def planning_frontier(topics,minimum=10):
    return [{**t,'rollup':False} for t in topics if t.get('is_leaf',True)]
