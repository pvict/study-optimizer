"""Leitura sem migração de sinais recentes, disponível aos fluxos antigos."""
import json

from .planning import _date


def study_event_token(db):
    values=[]
    for table in ('study_events','study_errors'):
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
        values.append(db.execute('SELECT COALESCE(MAX(id),0) FROM '+table).fetchone()[0] if exists else 0)
    return tuple(values)


def poor_study_paths(repo,as_of):
    with repo._connection() as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='study_events'").fetchone(): return []
        latest={}
        for row in db.execute('SELECT * FROM study_events ORDER BY id'): latest[row['session_id']]=row
    paths=[]
    for event in latest.values():
        e=json.loads(event['payload'])
        if event['action']!='save' or e['kind']!='bloco' or not 0<=(_date(as_of)-_date(e['day'])).days<=14 or e['questions']<5: continue
        rate=e['confident_correct']/e['questions'] if e.get('confident_correct') is not None else e['correct']/e['questions'] if e.get('correct') is not None else e['percent']/100
        if rate<.75: paths.append(e['path'])
    # Fluxos antigos permanecem somente leitura: não migrar para consultar sinais.
    with repo._connection() as db:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='study_errors'").fetchone()
    if exists:
        from .study_errors import adverse_error_paths
        paths.extend(list(p) for p in adverse_error_paths(repo,as_of))
    return paths
