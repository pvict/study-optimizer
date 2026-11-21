"""Lotes de questões sem convicção; não identifica questões individuais da plataforma."""
from datetime import timedelta
from .planning import _date
from .models import normalize_path


def review_queue(sessions,not_before=None):
    by_id={s['session_id']:s['entry'] for s in sessions}
    used={sid:0 for sid in by_id}
    for sid,e in by_id.items():
        parent=e.get('review_of')
        if not parent: continue
        if parent not in by_id: raise ValueError('Há revisão vinculada a um lançamento ausente. Corrija/desconsidere as revisões dependentes primeiro.')
        source=by_id[parent]
        if source.get('confident_correct') is None or source['kind']!='bloco' or e.get('confident_correct') is None:
            raise ValueError('Revisões vinculadas precisam de contagens de convicção na origem e no resultado.')
        if normalize_path(source['path'])!=normalize_path(e['path']) or e['day']<source['day']:
            raise ValueError('A revisão deve ser do mesmo tema e não pode anteceder a origem.')
        chain={sid}
        current=parent
        while current:
            if current in chain: raise ValueError('Revisões não podem formar um ciclo.')
            chain.add(current)
            current=by_id.get(current,{}).get('review_of')
        used[parent]+=e['questions']
    queue=[]
    for sid,e in by_id.items():
        confidence=e.get('confident_correct')
        if e['kind']!='bloco' or confidence is None: continue
        remaining=e['questions']-confidence-used[sid]
        if remaining<0: raise ValueError('A alteração excede a pendência disponível para revisões vinculadas. Corrija as revisões dependentes primeiro.')
        if remaining:
            queue.append({'session_id':sid,'path':e['path'],'questions':remaining,'due_date':(_date(e['day'])+timedelta(days=7)).isoformat(),'source_date':e['day']})
    for lot in queue:
        available=(not_before or {}).get(lot['session_id'])
        if available and available>lot['due_date']:
            lot['original_due_date']=lot['due_date']
            lot['due_date']=available
    return sorted(queue,key=lambda q:(q['due_date'],q['path'],q['session_id']))


def review_progress(sessions):
    review_queue(sessions)
    by_id={s['session_id']:s['entry'] for s in sessions}
    roots={sid:{'session_id':sid,'path':e['path'],'day':e['day'],'questions':e['questions'],'consolidated':e['confident_correct']} for sid,e in by_id.items()
           if e['kind']=='bloco' and e.get('confident_correct') is not None and not e.get('review_of')}
    for sid,e in by_id.items():
        if not e.get('review_of'): continue
        parent=e['review_of']
        while by_id[parent].get('review_of'): parent=by_id[parent]['review_of']
        roots[parent]['consolidated']+=e['confident_correct']
    return list(roots.values())
