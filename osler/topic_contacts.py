"""A próxima vaga no calendário não é a data ideal de vencimento da revisão."""
from copy import deepcopy
from .planning import _date
from .study_models import AdaptiveProfile
from .study_calendar import forecast_calendar


def forecast_topic_contacts(service,view):
    day=view['date']; token=service.agenda.token(); p=AdaptiveProfile(**view['profile'])
    if view.get('planning_token')!=token:
        raise ValueError('O plano mudou. Atualize a tabela para calcular as próximas revisões.')
    days=min(548,(_date(p.exam_date)-_date(day)).days+1)
    if days<=0: return {'contacts':{},'end':day,'finished':True}
    calendar=forecast_calendar(view['planning_states'],p,day,days,view['sessions'],service.store.days(),view['plan'],view['agenda'],next_contact_only=True)
    contacts={}
    for plan in calendar:
        for item in plan['items']:
            contacts.setdefault(item['topic_id'],{'date':plan['date'],'stage':item['stage'],'questions':item['questions']})
    if token!=service.agenda.token(): raise ValueError('O plano mudou. Atualize a tabela para calcular as próximas revisões.')
    ids={t['topic_id'] for t in view['planning_states']}
    return {'contacts':contacts,'end':calendar[-1]['date'],'finished':False,
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
        else: label='Sem vaga prevista até '+_date(forecast['end']).strftime('%d/%m/%Y')
        row['Próxima revisão']=label
    return result
