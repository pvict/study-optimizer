"""Lista pronta com dados atuais e registro explícito em uma única etapa."""
import hashlib
import json
from datetime import timedelta

from .reduction import reduction_overview
from .reduction_storage import ReductionStore
from .planner_service import valid_date
from .planning import _date
from .models import normalize_path
from .reduction_recommendations import current_recommendations


class PracticalReductionService:
    def __init__(self, repo):
        self.repository = repo
        self.store = ReductionStore(repo)

    def current_overview(self, as_of):
        """Leitura atual com fontes e token capturados juntos, sem alterar o histórico."""
        from .adaptive_service import AdaptiveService
        valid_date(as_of)
        adaptive = AdaptiveService(self.repository)
        # Inicializa fontes opcionais antes de capturar a leitura protegida.
        from .study_errors import ErrorStore
        from .planner_storage import PlannerStore
        ErrorStore(self.repository)
        for attempt in range(2):
            token = self.store.evidence_token()
            view = adaptive.overview(as_of)
            # Uma troca de PDF não apaga alertas informados sobre o mesmo caminho.
            # Cada origem usa a versão selecionada, sem ressuscitar a que foi corrigida.
            from .assessment_storage import AssessmentStore
            selected = AssessmentStore(self.repository).selected(as_of)
            with self.repository._connection() as db:
                contexts = {row['row_id']: json.loads(row['path']) for row in db.execute('SELECT row_id,path FROM assessment_contexts')}
            by_path = {}
            for row_id, observation in selected.items():
                key = tuple(normalize_path(contexts[row_id]))
                by_path.setdefault(key, []).append(observation['observation'].to_dict())
            difficult = {}
            for record in adaptive.guide.days():
                if record['feedback'] == 'dificil' and 0 <= (_date(as_of) - _date(record['day'])).days <= 14:
                    difficult.setdefault(tuple(normalize_path(record['path'])), []).append(record['day'])
            for state in view['states']:
                state['manual_observations'] = by_path.get(tuple(normalize_path(state['path'])), [])
                state['guide_difficulty_dates'] = difficult.get(tuple(normalize_path(state['path'])), [])
            result = current_recommendations(view['states'], view['sessions'], as_of, view['profile']['recent_days'])
            reports = {}
            for kind in ('qbank', 'flashcards'):
                report = adaptive.guide._report(kind, as_of)
                reports[kind] = {'sha256': report.file_sha256, 'report_date': report.report_date} if report else None
            sources = {'reports': reports, 'incidence': view['incidence'].get('contexts', []),
                       'profile_id': view['profile_id'], 'policy_version': result['policy_version'],
                       'recent_days': result['recent_days'], 'warnings': view.get('warnings', [])}
            legacy_history = []
            for item in PlannerStore(self.repository).all_items():
                if not (item['status'] == 'aplicado_manualmente' and item['applied_date'] and item['applied_date'] <= as_of):
                    continue
                legacy_history.append({'topic_id': item['topic_key'], 'path': item['snapshot']['flashcards_path'],
                                       'planner_item_id': item['id'], 'planner_batch_id': item['batch_id'],
                                       'revision': item['revision'], 'day': item['applied_date'],
                                       'review_on': item['reevaluation_date'] or (_date(item['applied_date']) + timedelta(days=7)).isoformat(),
                                       'origin': 'planner_legacy', 'scope': 'seletiva'})
            sources['legacy_actions'] = legacy_history
            events = [e for e in self.store.events() if e['day'] <= as_of]
            if token == self.store.evidence_token():
                break
        else:
            raise ValueError('Os dados mudaram durante a leitura. Atualize a lista.')
        signature = hashlib.sha256(json.dumps({'date': as_of, 'sources': sources, 'evidence': token,
                                               'policy': result}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        latest = {item['topic_id']: {'event_id': None, 'kind': 'aplicado', 'day': item['day'],
                                     'origin': 'planner_legacy', 'topic': item} for item in legacy_history}
        legacy_by_topic = {item['topic_id']: item for item in legacy_history}
        for event in events:
            for topic in event['topics']:
                legacy = legacy_by_topic.get(topic['topic_id'])
                if legacy and (topic.get('planner_item_id'), topic.get('revision')) != (legacy['planner_item_id'], legacy['revision']):
                    # Uma escolha local só substitui a aplicação exata que viu.
                    # Data sem hora não distingue reaplicações no mesmo dia.
                    continue
                latest[topic['topic_id']] = {'event_id': event['id'], 'kind': event['kind'], 'day': event['day'], 'topic': topic}
        protected = {t['topic_id']: t for t in result['protected']}
        reevaluate = []
        for key, item in latest.items():
            if item['kind'] != 'aplicado':
                continue
            review_on = item['topic'].get('review_on') or (_date(item['day']) + timedelta(days=7)).isoformat()
            if key in protected or as_of >= review_on:
                reevaluate.append({**item['topic'], 'review_on': review_on,
                                   'reasons': protected[key]['reasons'] if key in protected else ['A pausa de sete dias chegou ao prazo de reavaliação.']})
        all_suggestions = result['all_suggestions']
        visible = [t for t in all_suggestions if latest.get(t['topic_id'], {}).get('kind') not in {'aplicado', 'manter'}]
        result.update({'all_suggestions': visible, 'suggestions': visible[:3], 'latest': latest, 'history': events,
                       'legacy_history': legacy_history,
                       'reevaluate': reevaluate, 'sources': sources, 'evidence_token': token,
                       'signature': signature, 'date': as_of,
                       'event_id': events[-1]['id'] if events else 0})
        return result

    def record_current(self, kind, topic_ids, day, signature, expected_id):
        """Declara somente uma ação manual já realizada; nunca executa na Osler."""
        valid_date(day, past=True)
        if kind not in {'aplicado', 'manter', 'reabrir'} or not topic_ids or len(topic_ids) != len(set(topic_ids)):
            raise ValueError('Selecione temas distintos e uma ação válida.')
        events = self.store.events()
        if events:
            last = events[-1]
            if (last.get('request_signature') == signature and last['kind'] == kind and last['day'] == day
                    and sorted(t['topic_id'] for t in last['topics']) == sorted(topic_ids)
                    and last.get('previous_event_id') == expected_id):
                return last['id']
        current = self.current_overview(day)
        if current['signature'] != signature:
            raise ValueError('Os dados ou critérios mudaram. Atualize a lista antes de registrar.')
        topics = {t['topic_id']: t for t in current['all_suggestions']}
        # Conserva o vínculo quando uma escolha posterior parte de uma reabertura.
        for item in current['sources']['legacy_actions']:
            if item['topic_id'] in topics:
                topics[item['topic_id']] = {**topics[item['topic_id']], 'planner_item_id': item['planner_item_id'],
                                           'revision': item['revision']}
        if kind == 'reabrir':
            topics = {key: item['topic'] for key, item in current['latest'].items()}
        if any(key not in topics for key in topic_ids):
            raise ValueError('Um tema não tem sugestão atual disponível. Atualize a lista.')
        payload = {'kind': kind, 'day': day, 'topics': [topics[key] for key in sorted(topic_ids)],
                   'sources': current['sources'], 'request_signature': signature, 'previous_event_id': expected_id,
                   'policy_version': current['policy_version'],
                   'meaning': 'Ação seletiva declarada como realizada manualmente. Preserve High Yield e conceitos com erros; nenhuma suspensão do deck inteiro ou economia diária é inferida.'}
        return self.store.append(payload, expected_id, current['evidence_token'])

    def overview(self, as_of, daily_limit=500, config=None, min_answers=30, min_accuracy=85, min_cards=20):
        result = reduction_overview(self.repository, as_of, daily_limit, config, min_answers, min_accuracy, min_cards)
        events = self.store.events()
        latest = {}
        for event in events:
            if event['day'] <= as_of:
                for topic in event['topics']:
                    latest[topic['topic_id']] = {'event_id': event['id'], 'kind': event['kind'], 'topic': topic}
        all_topics = result['triage']
        signature = hashlib.sha256(json.dumps({'sources': result['sources'], 'topics': all_topics}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        legacy_applied = {t['topic_id'] for t in all_topics if t['legacy_status'] == 'aplicado_manualmente'}
        applied = (legacy_applied - set(latest)) | {key for key, value in latest.items() if value['kind'] == 'aplicado'}
        result.update({'triage_all': all_topics, 'triage': [t for t in all_topics if latest.get(t['topic_id'], {}).get('kind') not in {'aplicado', 'manter'}
                       and (t['topic_id'] not in legacy_applied or latest.get(t['topic_id'], {}).get('kind') == 'reabrir')],
                       'latest': latest, 'event_id': events[-1]['id'] if events else 0, 'signature': signature,
                       'applied_topics': len(applied),
                       'kept_topics': sum(v['kind'] == 'manter' for v in latest.values()),
                       'criteria': {'min_answers': min_answers, 'min_accuracy': min_accuracy, 'min_cards': min_cards}})
        return result

    def record(self, kind, topic_ids, day, signature, expected_id, *, config=None, min_answers=30, min_accuracy=85, min_cards=20):
        valid_date(day, past=True)
        if kind not in {'aplicado', 'manter', 'reabrir'} or not topic_ids or len(topic_ids) != len(set(topic_ids)):
            raise ValueError('Selecione temas distintos e uma ação válida.')
        evidence_token = self.store.evidence_token()
        current = self.overview(day, config=config, min_answers=min_answers, min_accuracy=min_accuracy, min_cards=min_cards)
        if current['signature'] != signature:
            raise ValueError('Os dados ou critérios mudaram. Atualize a lista antes de registrar.')
        topics = {t['topic_id']: t for t in current['triage_all']}
        if kind == 'reabrir':
            topics.update({key: value['topic'] for key, value in current['latest'].items()})
        if any(key not in topics for key in topic_ids):
            raise ValueError('Um tema não está mais disponível. Atualize a lista.')
        payload = {'kind': kind, 'day': day, 'topics': [topics[key] for key in sorted(topic_ids)], 'sources': current['sources'],
                   'meaning': 'Redução seletiva declarada; não informa quantidade suspensa nem revisões economizadas.'}
        return self.store.append(payload, expected_id, evidence_token)
