"""Fila efetiva: retrato manual mais criações ainda não absorvidas por ele.

Os eventos de questões são a fonte única das criações. Um novo HTML absorve
as sessões já existentes, inclusive correções posteriores dessas sessões.
O retrato original nunca é alterado por esta projeção.
"""
from copy import deepcopy
import json

from .models import stable_topic_id


def creation_queue(snapshot, study_events, day):
    events = [dict(r) for r in study_events]
    cutoff = snapshot.get('study_event_cutoff') if snapshot else 0
    if cutoff is None:
        # Retratos antigos precedem o campo explícito: usar a data auditada
        # de inserção, nunca a data de contato ou o dia declarado no HTML.
        inserted = snapshot.get('_source_recorded_at', '')
        cutoff = max((r['id'] for r in events if r['created_at'] <= inserted), default=0)
    base_active = bool(snapshot and snapshot['scope'] != 'inventory' and snapshot['observed_day'] <= day)
    topics = {t['topic_id']: {**deepcopy(t), 'base_count': t['count'], 'created_count': 0}
              for t in snapshot['tree']['topics']} if base_active else {}
    latest, first = {}, {}
    for row in events:
        first.setdefault(row['session_id'], row)
        latest[row['session_id']] = row
    session_ids, creation_days = [], []
    for session_id, row in latest.items():
        entry = json.loads(row['payload'])
        count = entry.get('cards_created', 0)
        absorbed = bool(snapshot and first[session_id]['id'] <= cutoff
                        and json.loads(first[session_id]['payload'])['day'] <= snapshot['observed_day'])
        if (row['action'] != 'save' or absorbed or entry['day'] > day
                or entry['kind'] != 'bloco' or not count):
            continue
        key = stable_topic_id(entry['path'])
        topic = topics.setdefault(key, {'topic_id': key, 'path': entry['path'], 'label': entry['path'][-1],
                                       'count': 0, 'base_count': 0, 'created_count': 0, 'specific': True})
        topic['count'] += count
        topic['created_count'] += count
        session_ids.append(session_id)
        creation_days.append(entry['day'])
    starts = creation_days + ([snapshot['observed_day']] if base_active else [])
    return {'topics': list(topics.values()), 'created_cards': sum(t['created_count'] for t in topics.values()),
            'created_session_ids': session_ids, 'queue_start': min(starts) if starts else None,
            'snapshot_id': snapshot['id'] if snapshot else 0, 'has_queue': bool(base_active or topics),
            'total_cards': sum(t['count'] for t in topics.values()),
            'source_total': snapshot['tree']['total'] if snapshot else 0,
            'unallocated': snapshot['tree']['unallocated'] if base_active else 0}
