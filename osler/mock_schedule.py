"""Datas de simulados são reservas, nunca resultados ou evidência de contato."""
from datetime import timedelta
from .planning import _date,_number


def schedule_dates(first_day,interval,end,exceptions=None):
    first,last=_date(first_day),_date(end)
    _number(interval,'Intervalo entre simulados',integer=True,positive=True,maximum=365)
    if last<first or (last-first).days>547: raise ValueError('Escolha uma série de até 18 meses.')
    exceptions=exceptions or {}
    origins=[(first+timedelta(days=i)).isoformat() for i in range(0,(last-first).days+1,interval)]
    if not isinstance(exceptions,dict) or set(exceptions)-set(origins): raise ValueError('A ocorrência não pertence a esta série.')
    rows=[]; occupied=set()
    for origin in origins:
        day=exceptions.get(origin,origin)
        if day is not None:
            _date(day)
            if day>end: raise ValueError('A data deve ficar até o fim da preparação.')
            if day in occupied: raise ValueError('Já existe outro simulado nesta data. Mova ou retire o outro primeiro.')
            occupied.add(day)
        rows.append({'occurrence_id':origin,'original_date':origin,'date':day,'status':'removed' if day is None else 'reserved'})
    return rows


def calendar_changes(before,after,*,include_quantities=False,include_additions=False):
    """Compara apenas o próximo contato de cada tema no horizonte visível."""
    def index(days):
        result={}
        for day in days:
            for item in day['items']:
                result.setdefault(item['topic_id'],{'date':day['date'],'item':item})
        return result
    old,new=index(before),index(after)
    changes=[]
    for key,original in old.items():
        revised=new.get(key)
        if revised and revised['date']==original['date'] and (not include_quantities or revised['item']['questions']==original['item']['questions']): continue
        t=original['item']
        changes.append({'topic_id':key,'path':t['path'],'before_date':original['date'],
                        'after_date':revised['date'] if revised else None,'questions':t['questions'],
                        'after_questions':revised['item']['questions'] if revised else None,
                        'priority':t['priority']})
    if include_additions:
        for key,revised in new.items():
            if key in old: continue
            t=revised['item']
            changes.append({'topic_id':key,'path':t['path'],'before_date':None,'after_date':revised['date'],
                            'questions':None,'after_questions':t['questions'],'priority':t['priority']})
    ranks={'urgente':0,'alta':1,'normal':2}
    return sorted(changes,key=lambda r:(r['before_date'] or r['after_date'] or '9999-12-31',ranks.get(r['priority'],3),r['path']))
