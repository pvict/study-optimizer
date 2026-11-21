"""A próxima vaga no calendário não é a data ideal de vencimento da revisão."""
from copy import deepcopy
from datetime import timedelta
from .planning import _date
from .study_models import AdaptiveProfile
from .study_calendar import iter_forecast_calendar
from .study_allocation import fits_recovery_bank, has_small_bank


def forecast_topic_contacts(service,view):
    day=view['date']; token=service.agenda.token(); p=AdaptiveProfile(**view['profile'])
    if view.get('planning_token')!=token:
        raise ValueError('O plano mudou. Atualize a tabela para calcular as próximas revisões.')
    days=min(548,(_date(p.exam_date)-_date(day)).days+1)
    if days<=0: return {'contacts':{},'end':day,'finished':True}
    settings=service.store.days()
    end=(_date(day)+timedelta(days=days-1)).isoformat()
    agenda=view['agenda']
    calendar=iter_forecast_calendar(view['planning_states'],p,day,days,view['sessions'],settings,view['plan'],agenda,next_contact_only=True)
    by_id={t['topic_id']:t for t in view['planning_states']}
    ids={topic_id for topic_id,t in by_id.items() if not has_small_bank(t,p.min_block)}
    manual_ids={extra['topic_id'] for date,config in settings.items() if day<=date<=end for extra in config.get('extra_topics',[])}
    manual_ids.update(r['topic_id'] for r in agenda.get('rows',[])
                      if r['topic_id'] in by_id and r['date']<=end and r.get('remaining')
                      and fits_recovery_bank(by_id[r['topic_id']],r,p.min_block))
    manual_ids.update(r.get('to_topic_id',r.get('topic_id')) for r in agenda.get('swaps',[]) if day<=r['day']<=end)
    manual_ids.update(row['topic_id'] for date,config in agenda.get('overrides',{}).items()
                      if day<=date<=end and config.get('mode')=='final_review' for row in config.get('rows',[]))
    sought=ids|(manual_ids&by_id.keys())
    contacts={}
    for plan in calendar:
        for item in plan['items']:
            contacts.setdefault(item['topic_id'],{'date':plan['date'],'stage':item['stage'],'questions':item['questions']})
            for member in item.get('group_members',[]):
                contacts.setdefault(member,{'date':plan['date'],'stage':'Bloco conjunto: '+item['path'][-1],
                                             'questions':None,'group_topic_id':item['topic_id']})
        if sought.issubset(contacts): break
    if token!=service.agenda.token(): raise ValueError('O plano mudou. Atualize a tabela para calcular as próximas revisões.')
    return {'contacts':contacts,'end':end,'finished':False,
            'coverage':{'scheduled':len(ids&contacts.keys()),'total':len(ids)},
            'unassigned_ids':sorted(ids-contacts.keys())}


def apply_next_contacts(rows,forecast):
    result=deepcopy(rows)
    for row in result:
        row['Revisão devida']=row.get('Próxima revisão')
        contact=forecast['contacts'].get(row['topic_id'])
        row['Tipo do próximo bloco']=contact['stage'] if contact else None
        if not row.get('catalog_available',True): label='Fora do catálogo atual'
        elif contact: label=_date(contact['date']).strftime('%d/%m/%Y')
        elif forecast.get('finished'): label='Preparação encerrada'
        elif row.get('small_bank'):
            label='Falta complemento'
            row['Revisão devida']=None
        else: label='Sem vaga prevista até '+_date(forecast['end']).strftime('%d/%m/%Y')
        row['Próxima revisão']=label
    return result
