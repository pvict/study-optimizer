"""Lotes agregados de revisões: vencimentos observados, nunca erros presumidos."""
from collections import defaultdict
from datetime import date,timedelta


def due_after_week(day):
    return (date.fromisoformat(day)+timedelta(days=7)).isoformat()


def outstanding_batches(config,events,as_of,*,include_seed=True):
    batches=[{'due':config['start'],'count':config['total'],'seed':True}]
    batches += [{**r,'seed':False} for r in config.get('carried_returns',[])]
    events=sorted((e for e in events if e.get('plan_id')==config['id'] and e.get('day','9999')<=as_of),
                  key=lambda e:(e['day'],e['id']))
    for event in events:
        if event['kind']=='recovery.quantity.generated':
            batches.append({'due':due_after_week(event['day']),'count':event['count'],'seed':False})
        elif event['kind']=='recovery.quantity.done':
            left=event['count']
            for batch in sorted(batches,key=lambda r:r['due']):
                if batch['due']>event['day']:break
                used=min(left,batch['count']);batch['count']-=used;left-=used
                if not left:break
            if left:raise ValueError('O histórico contém revisões realizadas antes do saldo vencer. Confira os registros.')
            returning=event.get('returning')
            if returning:
                batches.append({'due':due_after_week(event['day']),'count':returning,'seed':False})
    totals=defaultdict(int)
    for batch in batches:
        if include_seed or not batch['seed']:totals[batch['due']]+=batch['count']
    return [{'due':due,'count':n} for due,n in sorted(totals.items()) if n>0]
