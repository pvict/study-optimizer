"""Dispensa auditável do complemento de um encontro; não é evidência de estudo."""
from .models import normalize_path
from .study_allocation import topic_is_new
from .study_agenda import booking_completed


def can_skip_complement(item,day):
    supply=item.get('planner_supply') or {}
    return bool(not item.get('added_by_user') and supply.get('external_only') and supply.get('planner_total',0)>0 and
                supply.get('completed',0)>=supply['planner_total'] and
                not any(q['due_date']<=day for q in item.get('pending_reviews',[])))


def active_completions(records,sessions,as_of):
    """Correções/exclusões reavaliam quantidade; capacidade original fica preservada."""
    restored={r['decision_id'] for r in records if r.get('kind')=='planner_complement.restore' and r['day']<=as_of}
    declared={}
    for row in records:
        if row.get('kind')=='planner_complement.skip' and row['day']<=as_of:
            scope=(row.get('credit_start',row['day']),row.get('credit_cutoff',-1),
                   row.get('credit_date',row['day']),row.get('source_exam_key'),tuple(sorted(row.get('extra_ids',[]))))
            declared[(row['day'],tuple(normalize_path(row['path'])),scope)]=row
    latest={}
    for row in declared.values():
        if row['id'] in restored:continue
        key=(row['day'],tuple(normalize_path(row['path'])),
             row.get('credit_start',row['day']),row.get('credit_cutoff',-1),row.get('credit_date',row['day']),
             row.get('source_exam_key'),tuple(sorted(row.get('extra_ids',[]))))
        total=booking_completed({'path':row['path'],'created_day':row.get('credit_start',row['day']),
              'cutoff':row.get('credit_cutoff',-1),'date':row.get('credit_date',row['day']),
              'source_exam_key':row.get('source_exam_key')},[s for s in sessions if s['entry']['day']<=row['day']])
        required=row.get('required_completed',row.get('planner_total',0))
        if row['recommended']>total>=required>0:latest[key]=row
    return list(latest.values())


def apply_completions(plan,agenda,day,extra_topics=()):
    decisions=agenda.get('planner_completions',[])
    current={r['topic_id']:r for r in decisions if r['day']==day}
    if not current:
        plan['planner_completions']=[]
        return
    skipped=[];kept=[]
    for item in plan['items']:
        decision=current.get(item['topic_id'])
        if decision and decision.get('manual_partial'):
            if item.get('added_by_user') and item.get('extra_pending',0)>0 and any(e['topic_id']==item['topic_id'] and e['extra_id'] not in decision.get('extra_ids',[]) for e in extra_topics):decision=None
            if decision and item.get('day_swap_id') and any(s.get('topic_id')==item['topic_id'] and s['day']==day and s['id']>decision['id'] for s in agenda.get('swaps',[])):decision=None
        if decision and any(r['topic_id']==item['topic_id'] and r['plan_id']>decision['id'] and
                            r['date']<=day for r in agenda['rows']):decision=None
        if decision and (decision.get('manual_partial') or can_skip_complement(item,day)):
            skipped.append({**decision,'skipped_questions':decision['skipped_questions'] if decision.get('manual_partial') else item['questions']})
            group='new' if topic_is_new(item) else 'reviews'
            plan['distribution']['planned_'+group]-=item['questions']
        else:kept.append(item)
    # A decisão continua visível quando o registro normal já retirou o item da alocação.
    present={r['topic_id'] for r in skipped}|{i['topic_id'] for i in kept}
    skipped.extend(r for key,r in current.items() if key not in present)
    removed=plan['questions']-sum(i['questions'] for i in kept)
    plan.update(items=kept,questions=sum(i['questions'] for i in kept),planner_completions=skipped)
    plan['planned_minutes']-=removed*plan['minutes_per_question']
    plan['capacity']['unused_questions']=max(0,plan['target_questions']-plan['done_questions']-plan['questions'])


def skip_complement(service,day,topic_id,expected_token):
    from .planner_service import today_local
    if day!=today_local().isoformat():raise ValueError('Encerre complementos somente no dia de estudo atual.')
    view=service.overview(day)
    if view['planning_token']!=expected_token:raise ValueError('O plano mudou. Atualize antes de encerrar o tema.')
    item=next((i for i in view['plan']['items'] if i['topic_id']==topic_id),None)
    if not item or not can_skip_complement(item,day):
        raise ValueError('Conclua as questões disponíveis no Planner e os retornos vinculados devidos antes de encerrar o tema.')
    supply=item['planner_supply']
    booking=next((r for r in view['agenda']['rows'] if r['topic_id']==topic_id and r['date']<=day),None) if item.get('rescheduled') else None
    previous=max((r['id'] for r in service.agenda.records() if r.get('kind')=='planner_complement.skip' and
                  r['day']==day and r['topic_id']==topic_id),default=0)
    return service.agenda.append({'kind':'planner_complement.skip','day':day,'topic_id':topic_id,
        'path':item['path'],'planner_total':supply['planner_total'],'observed_date':supply['observed_date'],
        'recommended':supply['recommended'],'skipped_questions':item['questions'],
        'credit_start':booking['created_day'] if booking else day,
        'credit_cutoff':booking['cutoff'] if booking else -1,
        'session_versions':view['plan']['session_versions'],'previous_decision_id':previous},expected_token)


def restore_complement(service,day,decision_id,expected_token):
    from .planner_service import today_local
    if day!=today_local().isoformat():raise ValueError('Desfaça a dispensa somente no dia de estudo atual.')
    if service.agenda.token()!=expected_token:raise ValueError('O plano mudou. Atualize antes de desfazer.')
    if not any(r['id']==decision_id and r['day']==day for r in active_completions(service.agenda.records(),service.store.active(day),day)):
        raise ValueError('Esta dispensa não está ativa.')
    return service.agenda.append({'kind':'planner_complement.restore','day':day,'decision_id':decision_id},expected_token)


def partial_block_context(view,item):
    day=view['date']
    booking=next((r for r in view['agenda']['rows'] if r['topic_id']==item['topic_id'] and r['date']<=day),None) if item.get('rescheduled') else None
    start=booking['created_day'] if booking else day
    cutoff=booking['cutoff'] if booking else -1
    extras=[e for e in view['day']['settings']['extra_topics'] if e['topic_id']==item['topic_id']]
    if item.get('added_by_user') and extras:
        start=day
        cutoff=max(cutoff,max(e['after_event_id'] for e in extras))
    credit={'path':item['path'],'created_day':start,'cutoff':cutoff,'date':booking['date'] if booking else day,
            'source_exam_key':booking.get('source_exam_key') if booking else None}
    completed=booking_completed(credit,view['sessions'])
    remaining=booking['remaining'] if booking and not item.get('added_by_user') else item['questions']
    return {'completed':completed,'recommended':completed+remaining,'remaining':remaining,'credit_start':start,'credit_cutoff':cutoff,
            'credit_date':credit['date'],'source_exam_key':credit['source_exam_key'],'extra_ids':[e['extra_id'] for e in extras]}


def complete_partial_block(service,day,topic_id,expected_token):
    from .planner_service import today_local
    if day!=today_local().isoformat():raise ValueError('Conclua o bloco pelo plano de hoje.')
    view=service.overview(day)
    if view['planning_token']!=expected_token:raise ValueError('O plano mudou. Atualize antes de concluir o bloco.')
    item=next((i for i in view['plan']['items'] if i['topic_id']==topic_id),None)
    if not item:raise ValueError('Esse bloco já saiu do plano. Atualize a página.')
    context=partial_block_context(view,item)
    if context['completed']<=0:raise ValueError('Registre primeiro as questões realmente feitas neste bloco.')
    previous=max((r['id'] for r in service.agenda.records() if r.get('kind')=='planner_complement.skip' and
                  r['day']==day and r['topic_id']==topic_id),default=0)
    return service.agenda.append({'kind':'planner_complement.skip','manual_partial':True,
        'reason':'Banco sem questões suficientes; conclusão parcial declarada pelo usuário.',
        'day':day,'topic_id':topic_id,'path':item['path'],'required_completed':context['completed'],
        'recommended':context['recommended'],'skipped_questions':context['remaining'],'extra_ids':context['extra_ids'],
        'credit_start':context['credit_start'],'credit_cutoff':context['credit_cutoff'],
        'credit_date':context['credit_date'],'source_exam_key':context['source_exam_key'],
        'session_versions':view['plan']['session_versions'],'previous_decision_id':previous},expected_token)
