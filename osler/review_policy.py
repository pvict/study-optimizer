"""Triagem inicial descritiva: exposição e segurança não são estabilidade calibrada."""
from math import ceil

POLICY_VERSION='4.0'


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
    # Compromissos vencidos precedem candidatos. Na fila inicial, valor esperado de prática pesa antes da idade.
    due=state.get('allocation_due',state.get('next_review'))
    committed=state.get('review_committed',True) or bool(state.get('pending_reviews'))
    hard_due=bool(committed and due and due<=day)
    return (not hard_due,{'urgente':0,'alta':1,'normal':2}[state['priority']] if hard_due else 0,
            due if hard_due else '9999-12-31',not state.get('manual_adverse',False),-state['score'],state['path'])
