"""Doses e trajetórias condicionais; nenhuma previsão é transformada em resultado."""
from collections import defaultdict
from datetime import timedelta
from math import ceil

from .planning import _date


def question_dose(state,profile):
    """Política inicial explícita: necessidade + incerteza + relevância, não dose clínica validada."""
    p=state['confidence'] if state['confidence']['exact_n'] else state['performance']
    target=profile.target_accuracy/100
    rate=p['observed'] if p['observed'] is not None else p['mean']
    gap=max(0,target-rate)/target
    uncertainty=min(1,p['sd']/.25)
    h=state.get('incidence_strength',0)
    desired=max(profile.min_block,ceil(profile.min_block+10*gap+5*uncertainty+5*h))
    if not state['spacing']['block_days']: desired=max(desired,20,profile.min_block)
    available=min(state['total'],desired)
    return {'recommended_questions':desired if state['total']<profile.min_block else available,
            'available_per_block':available,'complement_per_block':max(0,desired-state['total']) if state['total']<profile.min_block else 0,
            'small_bank':state['total']<profile.min_block}


def next_stage(state,as_of=None):
    days=state['spacing']['block_days']
    if as_of: days=[d for d in days if d<as_of]
    if days: return len(days),'Revisão '+str(len(days))
    return 0,'Primeiro contato' if state['status']=='sem_registro' else 'Diagnóstico'


def topic_trajectory(state,profile,start):
    """Demanda indicativa mantendo o intervalo observado. Datas não reservam vagas."""
    first=max(start,state.get('next_review') or start)
    number,label=next_stage(state,first)
    horizon_end=min(_date(profile.exam_date),_date(start)+timedelta(days=547))
    interval=max(1,state['review_interval_days'])
    steps=[]
    cumulative=0
    day=_date(first)
    while day<=horizon_end:
        q=state['recommended_questions']
        cumulative+=q
        steps.append({'stage':label,'review_number':number,'date':day.isoformat(),
                      'questions':q,'cumulative_questions':cumulative,
                      'available_questions':min(q,state['total']),
                      'complement_questions':max(0,q-state['total'])})
        number+=1
        label='Revisão '+str(number)
        day+=timedelta(days=interval)
    return {'topic_id':state['topic_id'],'path':state['path'],'steps':steps,'recommended_total':cumulative,'horizon_end':horizon_end.isoformat(),
            'recorded_attempts':state['recorded_attempts'],'pdf_answered':state['answered_pdf'],
            'available_per_block':state['available_per_block'],
            'complement_per_block':max(0,state['recommended_questions']-state['total']),
            'assumption':'Mantendo o desempenho e intervalo atuais; datas indicativas sem reserva de vaga.'}


def trajectory_summary(states,profile,start,calendar):
    booked=defaultdict(lambda:{'questions':0,'contacts':0,'first':None})
    for day in calendar:
        if day['date']>profile.exam_date: continue
        for item in day['items']:
            row=booked[item['topic_id']]
            row['questions']+=item['questions']
            row['contacts']+=1
            if row['first'] is None: row['first']=day['date']
    rows=[]
    for state in states:
        roadmap=topic_trajectory(state,profile,start)
        b=booked[state['topic_id']]
        rows.append({'topic_id':state['topic_id'],'Tema':state['path'][-1],'Caminho':' → '.join(state['path']),
                     'Por encontro':state['recommended_questions'],'Demanda até a prova':roadmap['recommended_total'],
                     'Encontros recomendados':len(roadmap['steps']),'Questões com vaga prevista':b['questions'],
                     'Encontros com vaga prevista':b['contacts'],'Primeira vaga prevista':b['first'],
                     'Feitas em blocos registrados':state['recorded_attempts'],'Respondidas no PDF':state['answered_pdf'],
                     'Complemento por encontro':max(0,state['recommended_questions']-state['total']),
                     'Incidência relativa (%)':100*state['importance']})
    return {'rows':rows,'recommended_questions':sum(r['Demanda até a prova'] for r in rows),
            'scheduled_questions':sum(r['Questões com vaga prevista'] for r in rows),
            'unscheduled_topics':sum(r['Primeira vaga prevista'] is None for r in rows),
            'small_bank_topics':sum(s['small_bank'] for s in states)}
