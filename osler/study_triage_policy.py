"""Política pura e explícita de capacidade; não representa necessidade validada."""
from copy import deepcopy
from datetime import timedelta
from math import ceil
from .planning import _date,_number


def protected_reason(t,min_sample=30,lower_bound=.8):
    c=t.get('confidence',{})
    if t.get('registered_error') or t.get('manual_adverse') or t.get('open_error_count'): return 'Erro aberto ou sinal adverso: manter.'
    if t.get('low_accuracy') or t.get('alert_signal'): return 'Rendimento frágil: manter.'
    if not t.get('review_committed',True): return 'Sem compromisso de revisão recorrente: manter na fila inicial.'
    if not t.get('incidence_known'): return 'Incidência individual desconhecida: manter.'
    if t.get('confidence_source')!='novas' or c.get('exact_n',0)<min_sample or c.get('observed') is None or not c.get('interval'): return 'Medição de inéditas insuficiente: manter.'
    if c['observed']<t.get('target_accuracy',90)/100 or c['interval'][0]<lower_bound: return 'Convicção ou limite inferior de Wilson insuficiente: manter.'
    if t.get('reserved'): return 'Compromisso explícito: manter.'
    return None


def theme_demand(t,start,end,interval=None,first=None):
    due=max(start,first or t.get('theme_review_due') or t.get('next_review') or start)
    if not first and interval and t.get('theme_review_due') and t['theme_review_due']>start:
        due=(_date(due)+timedelta(days=max(0,interval-t['review_interval_days']))).isoformat()
    remaining=(_date(end)-_date(due)).days
    step=max(1,interval or t['review_interval_days'])
    contacts=0 if remaining<0 or not t.get('review_committed',True) else 1+remaining//step
    amounts={(_date(due)+timedelta(days=i*step)).isoformat():t.get('theme_recommended_questions',t['recommended_questions']) for i in range(contacts)}
    lots={}
    for q in t.get('pending_reviews',[]):
        day=max(start,q['due_date'])
        if day<=end: lots[day]=lots.get(day,0)+q['questions']
    for day,n in lots.items(): amounts[day]=max(amounts.get(day,0),min(t['total'],max(t.get('minimum_block',10),n)))
    return sum(amounts.values())


def propose_triage(states,calendar,start,end,*,frequency_factor=1.5,max_gap=90,min_sample=30,lower_bound=.8,defer_days=0):
    _number(frequency_factor,'Fator de intervalo',positive=True,maximum=3)
    _number(max_gap,'Máximo entre contatos',integer=True,positive=True,maximum=90)
    _number(min_sample,'Amostra mínima',integer=True,positive=True)
    _number(lower_bound,'Limite de Wilson',positive=True,maximum=1)
    if frequency_factor<1: raise ValueError('O fator não pode encurtar intervalos.')
    if not 0<=defer_days<=14 or type(defer_days) is not int: raise ValueError('Adiamento deve ser de 0 a 14 dias.')
    if end<start: raise ValueError('Período inválido.')
    capacity=sum(max(0,d.get('target_questions',d.get('questions',0))-d.get('done_questions',0)) for d in calendar if start<=d['date']<=end)
    rows=[]
    for t in states:
        reason=protected_reason(t,min_sample,lower_bound)
        interval=t['review_interval_days']; new_interval=min(max_gap,ceil(interval*frequency_factor))
        before=theme_demand(t,start,end)
        rows.append({'topic_id':t['topic_id'],'path':t['path'],'action':'manter','old_interval':interval,'new_interval':interval,
                     'importance':t['importance'],'confidence':t.get('confidence',{}).get('observed'),
                     'n':t.get('confidence',{}).get('exact_n',0),'before_questions':before,'after_questions':before,
                     'reason':reason or 'Sem redução necessária na carga deste cenário.','protected':bool(reason),
                     'candidate_interval':new_interval,'recorded_attempts':t.get('recorded_attempts',0)})
    demand=sum(r['before_questions'] for r in rows)
    after=demand
    candidates=sorted([r for r in rows if not r['protected']],key=lambda r:(r['importance'],-r['confidence'],-r['n'],-r['recorded_attempts'],r['path']))
    by_id={t['topic_id']:t for t in states}
    for row in candidates:
        if after<=capacity: break
        t=by_id[row['topic_id']]
        extended=theme_demand(t,start,end,row['candidate_interval'])
        if row['candidate_interval']>row['old_interval'] and extended<row['before_questions']:
            row.update(action='reduzir frequência',new_interval=row['candidate_interval'],after_questions=extended,
                       reason='Menor incidência e evidência recente suficiente em inéditas; intervalo futuro planejado ampliado.')
            after-=row['before_questions']-extended
    if defer_days and after>capacity:
        for row in candidates:
            if after<=capacity: break
            t=by_id[row['topic_id']]; due=t.get('theme_review_due')
            if not due or due<=start: continue
            latest=(_date(due)+timedelta(days=max(0,max_gap-row['old_interval']))).isoformat()
            deferred=min(latest,(_date(due)+timedelta(days=defer_days)).isoformat(),end)
            candidate=theme_demand(t,start,end,row['new_interval'],deferred)
            if deferred>due and candidate<row['after_questions']:
                after-=row['after_questions']-candidate
                row.update(action='adiar',defer_until=deferred,after_questions=candidate,reason='Contato futuro adiado dentro do intervalo máximo; retornos de questões preservados.')
    return {'rows':rows,'start':start,'end':end,'demand_questions':demand,'capacity_questions':capacity,
            'balance_questions':demand-capacity,'deficit_questions':max(0,demand-capacity),'after_demand_questions':after,'after_deficit_questions':max(0,after-capacity),
            'frequency_factor':frequency_factor,'defer_days':defer_days,'min_sample':min_sample,'lower_bound':lower_bound}


def apply_triage(states,policies,day,booked_ids=()):
    if not policies: return states
    result=deepcopy(states); chosen={}
    for p in policies:
        if p['start']<=day<=p['end']:
            for row in p['rows']:
                if row['action']!='manter': chosen[row['topic_id']]=(row,p['start'])
    for t in result:
        old=t.get('_triage_original_interval',t['review_interval_days'])
        selected=chosen.get(t['topic_id'])
        row,policy_start=selected if selected else (None,None)
        if not row or t['topic_id'] in booked_ids or protected_reason(t):
            if '_triage_original_interval' in t:
                shift=t.get('_triage_shift',0) if t.get('_triage_origin_contact')==t.get('last_contact') else t['review_interval_days']-old
                t['review_interval_days']=old
                if t.get('theme_review_due'): t['theme_review_due']=(_date(t['theme_review_due'])-timedelta(days=shift)).isoformat()
                dates=[q['due_date'] for q in t.get('pending_reviews',[])]+([t['theme_review_due']] if t.get('theme_review_due') else [])
                t['next_review']=min(dates) if dates else None
                t.pop('_triage_original_interval',None); t.pop('_triage_shift',None)
            continue
        interval=max(old,row['new_interval']); shift=interval-old
        t['_triage_original_interval']=old
        # Reconstruções futuras usam o início da política, não o dia da consulta.
        # Assim o vencimento original não desfaz um corte já aplicado.
        if t.get('theme_review_due') and t['theme_review_due']>policy_start and '_triage_shift' not in t:
            previous=t['theme_review_due']
            t['theme_review_due']=(_date(t['theme_review_due'])+timedelta(days=shift)).isoformat()
            if row.get('defer_until'): t['theme_review_due']=max(t['theme_review_due'],row['defer_until'])
            t['_triage_shift']=(_date(t['theme_review_due'])-_date(previous)).days
            t['_triage_origin_contact']=t.get('last_contact')
        t['review_interval_days']=interval
        due=[q['due_date'] for q in t.get('pending_reviews',[])]+([t['theme_review_due']] if t.get('theme_review_due') else [])
        t['next_review']=min(due) if due else t.get('next_review')
        t['triage_action']=row['action']; t['triage_reason']=row['reason']
    return result
