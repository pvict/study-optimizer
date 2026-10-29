"""Política local de redução seletiva; convicção e cobertura nunca viram acerto."""
from collections import defaultdict
from datetime import timedelta

from .classification import wilson_interval
from .models import normalize_path
from .planning import _date


POLICY_VERSION = 'current-reduction-v1'
PAUSE_DAYS = 7
NEW_CARDS_PROTECTION_DAYS = 14


def _recent(value, day, window):
    return bool(value and 0 <= (day - _date(value)).days <= window)


def _rate(entry):
    n = entry.get('questions', 0)
    if not n:
        return None
    return entry['correct'] / n if entry.get('correct') is not None else entry.get('percent') / 100 if entry.get('percent') is not None else None


def current_recommendations(states, sessions, as_of, recent_days=90):
    """Até três sugestões, conservando justificativas e a lista completa para auditoria.

    Os cortes de incidência e o prazo de sete dias são decisões operacionais.
    Só blocos recentes de questões novas/mistas com acertos exatos sustentam Wilson.
    """
    day = _date(as_of)
    entries = defaultdict(list)
    for event in sessions:
        e = event['entry']
        if e['day'] <= as_of:
            entries[tuple(normalize_path(e['path']))].append(e)
    suggestions, protected, conditional = [], [], []
    for state in states:
        if state.get('historical_aggregate') or not state.get('is_leaf', True):
            continue
        path_entries = entries[tuple(normalize_path(state['path']))]
        recent = [e for e in path_entries if _recent(e['day'], day, recent_days)]
        blocks = [e for e in recent if e['kind'] == 'bloco']
        primary = [e for e in blocks if e.get('mode') == 'novas' and not e.get('review_of')]
        if not primary:
            primary = [e for e in blocks if e.get('mode') == 'mistas' and not e.get('review_of')]
        exact = [e for e in primary if e.get('correct') is not None]
        n = sum(e['questions'] for e in exact)
        correct = sum(e['correct'] for e in exact)
        rate = correct / n if n else None
        lower = wilson_interval(rate * 100, n)[0] if n else None
        manual = state.get('manual_context') or {}
        manuals = [m for m in [manual, *state.get('manual_observations', [])]
                   if _recent(m.get('data_observacao'), day, recent_days)]
        safety = state.get('planner_safety') or {}
        # O planejador sabe quando blocos posteriores superaram o retrato.
        # Sem a flag (entradas antigas), conserva-se a checagem pela data.
        safety_current = state.get('planner_snapshot_current') is not False and _recent(safety.get('observed_date'), day, recent_days)
        created = sum(e.get('cards_created', 0) for e in path_entries
                      if _recent(e['day'], day, NEW_CARDS_PROTECTION_DAYS))
        reasons = []
        if state.get('reported_difficulty'):
            reasons.append('Você relatou dificuldade alta recentemente: preserve os cartões deste tema até medir o rendimento.')
        if state.get('manual_adverse') or state.get('registered_error') or state.get('open_error_count') or state.get('linked_adverse'):
            reasons.append('Há erros abertos, críticos, recorrentes ou retornos ainda não recuperados.')
        if state.get('dose_kind') == 'reinforcement':
            reasons.append('O planejamento atual indica reforço; preserve a revisão até reavaliar esse sinal.')
        if any(m.get(k) is True for m in manuals for k in ('erros_criticos', 'erros_recorrentes')):
            reasons.append('Você informou erros críticos ou recorrentes.')
        if any(m.get('risco_perda') == 'alto' for m in manuals):
            reasons.append('Você informou risco alto de perda: mantenha a revisão.')
        if any(m.get('cobertura_suficiente') is False for m in manuals):
            reasons.append('Você informou cobertura insuficiente; não extrapole o resultado para todo o tema.')
        objective_rates = []
        # Não usar convicção como taxa objetiva, nem substituir relato de primeira tentativa pelo PDF.
        objective_rates += [m[k] / 100 for m in manuals for k in ('acerto_primeira_tentativa', 'acerto_recente', 'acerto_ultima_tentativa') if m.get(k) is not None]
        performance = state.get('performance') or {}
        if performance.get('reported_n') and performance.get('reported_percent') is not None:
            objective_rates.append(performance['reported_percent'])
        for mode in ('novas', 'mistas', 'repetidas'):
            measured = [e for e in recent if e.get('mode') == mode and _rate(e) is not None]
            total = sum(e['questions'] for e in measured)
            if total:
                objective_rates.append(sum(_rate(e) * e['questions'] for e in measured) / total)
            # A média da janela não pode apagar a falha mais recente. Sem hora
            # dos blocos, qualquer bloco objetivo ruim do último dia da mesma
            # modalidade protege, inclusive amostras pequenas e retornos vinculados.
            latest_blocks = [e for e in blocks if e.get('mode') == mode and _rate(e) is not None]
            latest_day = max((e['day'] for e in latest_blocks), default=None)
            objective_rates.extend(_rate(e) for e in latest_blocks if e['day'] == latest_day)
        objective = min(objective_rates) * 100 if objective_rates else rate * 100 if rate is not None else None
        if objective is not None and objective < 85:
            reasons.append(f'Acerto objetivo recente abaixo de 85% ({objective:.1f}%).')
        if created:
            reasons.append(f'{created} cards criados em blocos nos últimos 14 dias: preserve este reforço.')
        if any(_recent(value, day, 14) for value in state.get('guide_difficulty_dates', [])):
            reasons.append('Você informou dificuldade no guia nos últimos 14 dias.')
        if safety_current and safety.get('pending_reviews', 0):
            reasons.append('Há revisões pendentes no retrato atual da Osler.')
        if safety_current and safety.get('confident_accuracy_pct') is not None and safety['confident_accuracy_pct'] < 80:
            reasons.append('Segurança acumulada abaixo de 80%; é um sinal de cautela, separado do acerto.')
        if state.get('priority') in {'alta', 'urgente'} and not state.get('initial_focus'):
            reasons.append('Tema com prioridade elevada no planejamento atual.')
        low_incidence = state.get('incidence_known') and state.get('incidence_strength') is not None and state['incidence_strength'] <= .15
        if state.get('incidence_known') and state.get('incidence_strength', 0) > .15:
            reasons.append('Incidência relativa acima do corte operacional de baixa incidência.')
        row = {'topic_id': state['topic_id'], 'path': list(state['path']), 'studied_cards': state.get('studied_cards'),
               'incidence_known': bool(state.get('incidence_known')), 'incidence_strength': state.get('incidence_strength'),
               'objective_n': n, 'objective_accuracy': objective, 'exact_accuracy_pct': rate * 100 if rate is not None else None, 'wilson_lower_pct': lower,
               'recent_cards_created': created, 'reasons': reasons, 'scope': 'seletiva',
               'evidence_dates': {'pdf': state.get('report_date'), 'manual': sorted({m['data_observacao'] for m in manuals}),
                                  'safety': safety.get('observed_date'), 'blocks': sorted({e['day'] for e in recent}),
                                  'guide_difficulty': sorted(state.get('guide_difficulty_dates', []))},
               'safety_pct': safety.get('confident_accuracy_pct'), 'safety_n': safety.get('unique_questions'),
               'review_on': (day + timedelta(days=PAUSE_DAYS)).isoformat()}
        if reasons:
            row.update(recommendation='proteger', evidence_kind='protecao')
            protected.append(row)
            continue
        strong = n >= 30 and rate >= .85 and lower >= 75 and len({e['day'] for e in exact}) >= 2
        indirect = safety_current and safety.get('unique_questions', 0) >= 20 and safety.get('confident_accuracy_pct') is not None and safety['confident_accuracy_pct'] >= 80
        if low_incidence and (strong or indirect) and (state.get('studied_cards') or 0) > 0:
            row.update(recommendation='manutencao_seletiva' if strong else 'pausa_capacidade',
                       evidence_kind='objetiva' if strong else 'indireta')
            row['reasons'] = ['Baixa incidência relativa conhecida nas fontes atuais.',
                              'Acertos exatos recentes em pelo menos dois dias; manutenção seletiva.' if strong else
                              'Segurança acumulada recuperada: indício para aliviar a carga por 7 dias, sem comprovar domínio.']
            suggestions.append(row)
        else:
            row.update(recommendation='condicional', evidence_kind='insuficiente')
            row['reasons'] = ['Faltam evidências atuais para sugerir uma pausa seletiva. PDF e percentual revisado isolados não bastam.']
            conditional.append(row)
    suggestions.sort(key=lambda t: (t['incidence_strength'], -(t['studied_cards'] or 0), t['path']))
    return {'suggestions': suggestions[:3], 'all_suggestions': suggestions, 'protected': protected,
            'conditional': conditional, 'policy_version': POLICY_VERSION, 'recent_days': recent_days,
            'measured_reduction': None}
