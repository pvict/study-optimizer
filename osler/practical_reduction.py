"""Lista pronta com dados atuais e registro explícito em uma única etapa."""
import hashlib
import json

from .reduction import reduction_overview
from .reduction_storage import ReductionStore
from .planner_service import valid_date


class PracticalReductionService:
    def __init__(self, repo):
        self.repository = repo
        self.store = ReductionStore(repo)

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
