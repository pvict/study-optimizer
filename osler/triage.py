"""Triagem documental para redução seletiva; independente de domínio A/B."""
from .incidence import incidence_for_topic, prepare_incidence
from .planning import _date, _number
from .models import normalize_path


def adverse_signal(observation):
    return (any(observation.get(k) is True for k in ['erros_criticos', 'erros_recorrentes'])
            or observation.get('risco_perda') == 'alto' or observation.get('cobertura_suficiente') is False
            or any(observation.get(k) is not None and observation[k] < 75 for k in ['acerto_primeira_tentativa', 'acerto_ultima_tentativa', 'acerto_recente']))


def build_triage(matching, analysis, datasets, targets, as_of, min_answers=30, min_accuracy=85, min_cards=20, blocked_paths=None):
    day = _date(as_of)
    for value, name in [(min_answers, 'Respondidas'), (min_cards, 'Cartões estudados')]:
        _number(value, name, integer=True, positive=True)
    _number(min_accuracy, 'Acerto', positive=True, maximum=100)
    # Relatórios de cortes incompatíveis ou sem data não sustentam esta lista.
    dates = [matching.qbank_date, matching.flashcards_date]
    if any(not d or not 0 <= (day-_date(d)).days <= 90 for d in dates) or len(set(dates)) != 1:
        return []
    observations = {i['row_id']: i.get('observation') for i in analysis['items']}
    classifications = {i['row_id']: i['classification']['category'] for i in analysis['items']}
    prepared = prepare_incidence(datasets, targets, as_of)
    candidates, seen = [], set()
    blocked = [tuple(normalize_path(p)) for p in (blocked_paths or []) if p]
    for source in matching.rows:
        q, f = source.qbank, source.flashcards
        if not q or not f or source.row_type != 'terminal_comparavel' or source.association.startswith('bloqueada') or f.topic_id in seen:
            continue
        if any(tuple(normalize_path(path))[:len(block)] == block for block in blocked for path in [q.path, f.path]):
            continue
        if f.studied < min_cards or q.studied < min_answers:
            continue
        observation = observations.get(source.row_id) or {}
        # Sinal adverso conhecido prevalece mesmo quando a observação envelheceu.
        if adverse_signal(observation):
            continue
        if classifications.get(source.row_id) == 'C' and observation:
            continue
        manual = classifications.get(source.row_id) in {'A', 'B'}
        accuracy = q.acerto_pdf
        if not manual and (accuracy.value is None or accuracy.operator not in {'=', '>'} or accuracy.value < min_accuracy):
            continue
        incidence = incidence_for_topic(q.path, [], [], as_of, prepared)
        # Alta em qualquer fonte preserva a prioridade de prova. Ausente vem por último.
        order = {'sem incidencia': 0, 'incidencia baixa': 1, 'incidencia media': 2, 'incidencia alta': 3, 'incidencia altissima': 4}
        relevance = max((order.get(normalize_path([s.get('native_incidence', '')])[0], {'baixa': 1, 'media': 2, 'alta': 3}.get(s['band'], 5)) for s in incidence), default=5)
        candidates.append({'topic_id': f.topic_id, 'row_id': source.row_id, 'path': f.path,
                           'studied_cards': f.studied, 'total_cards': f.total, 'answered_pdf': q.studied,
                           'accuracy_pdf': accuracy.raw, 'accuracy_value': accuracy.value, 'evidence': 'manual' if manual else 'pdf',
                           'accuracy_label': 'Acerto no PDF · tentativa não identificada',
                           'distinct_questions': observation.get('questoes_distintas') if manual else None,
                           'initial': observation.get('acerto_primeira_tentativa') if manual else None,
                           'incidence': incidence, 'incidence_order': relevance, 'report_date': matching.qbank_date,
                           'action': 'Avaliar redução seletiva dos cartões já estudados', 'applied': False})
        seen.add(f.topic_id)
    return sorted(candidates, key=lambda i: (i['incidence_order'], -i['studied_cards'], -(i['accuracy_value'] or 0), i['path']))
