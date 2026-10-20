"""Carga informada e candidatos existentes; não estima efeito de suspender cartões."""
import json
from .guide_service import GuideService
from .assessment_service import AssessmentService
from .incidence import incidence_for_topic, prepare_incidence
from .matching_service import load_matching
from .planner_service import PlannerService
from .planning import _date, _number
from .planning_service import PlanningService
from .triage import build_triage, adverse_signal
from .study_signals import poor_study_paths


def reduction_overview(repo, as_of, daily_limit=500, config=None, min_answers=30, min_accuracy=85, min_cards=20):
    _date(as_of)
    _number(daily_limit, 'Referência diária', integer=True, positive=True, maximum=100000)
    guide = GuideService(repo)
    result = guide.guide(as_of)
    measurements = [m for m in PlanningService(repo).measurements()
                    if m['kind'] == 'revisoes_periodo' and m['observed_date'] <= as_of]
    workload = max(measurements, key=lambda m: (m['observed_date'], m['id']), default=None)
    comparison = None
    if workload:
        comparison = {'daily_limit': daily_limit, 'average': workload['count']/workload['horizon_days'],
                      'needed_reviews': max(0, workload['count']-daily_limit*workload['horizon_days'])}
    planner = PlannerService(repo)
    items = planner.store.all_items()
    active = {i['topic_key']: i for i in items if i['status'] not in {'cancelado', 'reativado'}}
    candidates, triage = [], []
    analysis = result['classification']
    if analysis:
        matching = load_matching(repo, analysis['qbank_report_id'], analysis['flashcards_report_id'])
        if config is not None:
            analysis = AssessmentService(repo).analyze(matching, as_of, config)
        selected = AssessmentService(repo).store.selected(as_of)
        with repo._connection() as db:
            contexts = {r['row_id']: json.loads(r['path']) for r in db.execute('SELECT row_id,path FROM assessment_contexts')}
        blocked = [contexts[key] for key, value in selected.items() if key in contexts and adverse_signal(value['observation'].to_dict())]
        blocked += [d['path'] for d in guide.days() if d['feedback'] == 'dificil' and 0 <= (_date(as_of)-_date(d['day'])).days <= 14]
        blocked += poor_study_paths(repo,as_of)
        triage = build_triage(matching, analysis, guide.datasets(), result['settings']['institutions'], as_of,
                              min_answers, min_accuracy, min_cards, blocked)
        for topic in triage:
            topic['legacy_status'] = active.get(topic['topic_id'], {}).get('status')
        sources = {r.row_id: r for r in matching.rows}
        prepared = prepare_incidence(guide.datasets(), result['settings']['institutions'], as_of)
        for item in analysis['items']:
            classification = item['classification']
            source = sources[item['row_id']]
            if not item['eligible'] or classification['category'] not in {'A', 'B'} or not source.flashcards or not source.flashcards.is_leaf:
                continue
            existing = active.get(source.flashcards.topic_id)
            observation = item['observation'] or {}
            candidates.append({'row_id': item['row_id'], 'path': source.flashcards.path,
                               'category': classification['category'], 'cards': classification['cards_involved'],
                               'initial': observation.get('acerto_primeira_tentativa'), 'last': observation.get('acerto_ultima_tentativa'),
                               'questions': observation.get('questoes_distintas'), 'observed_date': observation.get('data_observacao'),
                               'needs_error_check': any(observation.get(k) is None for k in ['erros_criticos', 'erros_recorrentes']),
                               'status': existing['status'] if existing else None, 'batch_id': existing['batch_id'] if existing else None,
                               'item_id': existing['id'] if existing else None,
                               'incidence': incidence_for_topic(source.qbank.path if source.qbank else source.flashcards.path,
                                                                [], [], as_of, prepared)})
    candidates.sort(key=lambda i: (i['status'] == 'aplicado_manualmente', i['category'], i['path']))
    return {'workload': workload, 'comparison': comparison, 'candidates': candidates, 'triage': triage,
            'applied_items': sum(i['status'] == 'aplicado_manualmente' for i in items),
            'measured_reduction': None, 'sources': result['sources'], 'stats': analysis['stats'] if analysis else {}}
