"""Prevenção por tema/janela, sem transformar projeções em contatos reais."""
from datetime import timedelta
from .planning import _date

PREVENTION_MODES={'balanced':'Manter carga e equilibrar revisões',
                  'reviews':'Reservar o período para revisões',
                  'extra':'Adicionar questões temporariamente'}


def preventive_state(state,day,policies,pending_due_dates=None):
    due=state.get('next_review')
    pending=pending_due_dates if pending_due_dates is not None else [q['due_date'] for q in state.get('pending_reviews',[])]
    selected=bool(due and any(p['start']<=day<=p['end'] and state['topic_id'] in p['topics'] for p in policies))
    lead=min(2,max(0,state.get('review_interval_days',0)//5)) if selected else 0
    # Um lote de7dias ainda não vencido não é antecipado como revisão individual.
    if pending and due and min(pending)<=due: lead=0
    allocation_due=(_date(due)-timedelta(days=lead)).isoformat() if due else None
    if pending: allocation_due=min(pending+([allocation_due] if allocation_due else []))
    anticipated=max(0,(_date(due)-_date(day)).days) if selected and allocation_due<=day else 0
    return {**state,'allocation_due':allocation_due,'preventive_priority':selected,
            'anticipated_days':anticipated,'preventive_original_due':due}


def projected_backlog(states,pending,day,start_date=None):
    result=[]
    for t in states:
        due=t.get('next_review')
        lots=[pending[q['session_id']] for q in t.get('pending_reviews',[]) if pending[q['session_id']]['remaining']>0]
        if not t.get('review_committed',True) and not lots: continue
        dates=[q['due_date'] for q in lots]+([due] if due else [])
        if not dates or min(dates)>day: continue
        due=min(dates)
        if start_date: due=max(due,start_date)
        if due>day: continue
        n=sum(q['remaining'] for q in lots if q['due_date']<=day)
        result.append({'topic_id':t['topic_id'],'path':list(t['path']),'due_date':due,
                       'questions':min(t['total'],max(n,t.get('recommended_questions',10))),
                       'review_interval_days':t.get('review_interval_days',7),'priority':t['priority'],
                       'importance':t['importance'],'score':t['score'],'pending_questions':n,
                       'projected_last_contact':t.get('last_contact')})
    return result


def summarize_risk(calendar,start,end,selected=None):
    ids=set(selected) if selected is not None else None
    days=[d for d in calendar if start<=d['date']<=end]
    first={}
    late_topic_days=0
    for day in days:
        for row in day.get('backlog_items',[]):
            if ids is not None and row['topic_id'] not in ids: continue
            late_topic_days+=1
            t=first.setdefault(row['topic_id'],{'first_pending':day['date'],**row,'pending_days':0,'max_delay_days':0})
            t['pending_days']+=1
            t['max_delay_days']=max(t['max_delay_days'],(_date(day['date'])-_date(row['due_date'])).days)
    return {'risk_topics':len(first),'late_topic_days':late_topic_days,'topics':list(first.values()),
            'planned_questions':sum(d['questions'] for d in days),'target_questions':sum(d['target_questions'] for d in days)}


def worsened_risks(before,after):
    original={r['topic_id']:r for r in before['topics']}
    return [{**r,'before_pending_days':original[r['topic_id']]['pending_days'],
             'before_max_delay_days':original[r['topic_id']]['max_delay_days']} for r in after['topics']
            if r['topic_id'] in original and (r['pending_days']>original[r['topic_id']]['pending_days'] or
               r['max_delay_days']>original[r['topic_id']]['max_delay_days'] or r['first_pending']<original[r['topic_id']]['first_pending'])]
