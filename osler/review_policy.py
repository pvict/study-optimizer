"""Triagem inicial descritiva: exposição e segurança não são estabilidade calibrada."""
from math import ceil
from .planning import _date

POLICY_VERSION='4.5'


def initial_interval(snapshot,profile,incidence_strength):
    p=profile.parameters
    rate=snapshot.get('confident_accuracy_pct') if snapshot else None
    n=snapshot.get('unique_questions',0) if snapshot else 0
    base=p.first_interval
    if rate is not None and n>=p.initial_min_sample:
        base=p.initial_low_interval if rate<100*p.failure_threshold else p.initial_mid_interval if rate<100*p.intermediate_threshold else p.initial_near_interval if rate<profile.target_accuracy else p.initial_good_interval
        if n<p.sufficient_sample: base=min(base,p.second_interval)
    if snapshot and snapshot.get('pending_reviews'): base=min(base,p.first_interval)
    return min(profile.max_contact_gap,max(1,ceil(base/(1+p.incidence_factor*max(0,min(1,incidence_strength))))))


def domain_evidence(seen,snapshot,confirmed_mastery,low_accuracy,target=90):
    if not seen: return 'Não visto'
    if confirmed_mastery: return 'Domínio confirmado em blocos'
    if low_accuracy: return 'Reforçar segurança'
    if snapshot and snapshot.get('confident_accuracy_pct') is not None:
        if snapshot['unique_questions']>=30 and snapshot['confident_accuracy_pct']>=target: return 'Segurança alta na Osler'
        return 'Em consolidação'
    return 'Medição pendente'


def review_order(state,day):
    # Compromissos reais precedem candidatos. Histórico com contato conhecido
    # ganha proteção ao atingir o limite de afastamento, sem virar atraso fictício.
    due=state.get('allocation_due',state.get('next_review'))
    committed=state.get('review_committed',True) or bool(state.get('pending_reviews'))
    hard_due=bool(committed and due and due<=day)
    deadline=state.get('initial_contact_deadline')
    stale_initial=bool(not committed and deadline and deadline<=day)
    adverse=bool(state.get('manual_adverse') or state.get('registered_error') or state.get('reported_difficulty'))
    # Bônus operacional proporcional à incidência: não é perda de memória
    # estimada nem evidência estatística. Um tema remoto de baixa incidência
    # não passa automaticamente à frente de uma dificuldade muito relevante.
    # Envelhecimento contínuo da fila, reavaliado em cada dia da previsão.
    # Não estima esquecimento: preserva o peso institucional e o intervalo já calculados.
    wait=max(0,(_date(day)-_date(deadline)).days) if stale_initial else 0
    score=state['score']+(state['importance']*(1+wait/max(1,state.get('review_interval_days',7))) if stale_initial else 0)
    group=0 if hard_due else 1 if adverse else 2
    return (group,{'urgente':0,'alta':1,'normal':2}[state['priority']] if hard_due else 0,
            due if hard_due else '9999-12-31',not state.get('manual_adverse',False),
            not state.get('intake_protected',False),state.get('anticipated_days',0)>0,not state.get('preventive_priority',False),
            -score,state['path'])
