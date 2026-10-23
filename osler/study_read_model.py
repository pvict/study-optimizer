"""Consultas de eventos sem inicializar stores ou executar migrações."""
import json


def read_events(repo,table):
    if table not in {'study_events','study_errors','mock_exams','study_plan_runs','weekly_reviews'}: raise ValueError('Tabela não permitida.')
    with repo._connection() as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone(): return []
        rows=[dict(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY id')]
    for row in rows:
        if 'payload' in row: row['data']=json.loads(row['payload'])
        if 'topic_path' in row: row['path']=json.loads(row['topic_path'])
    return rows


def latest_active(rows,key):
    latest={}
    for r in rows: latest[r[key]]=r
    return [r for r in latest.values() if r.get('action','save')=='save']


def waived_days(plans,as_of):
    canceled={r['data']['plan_id'] for r in plans if r['data'].get('kind')=='reschedule.cancel'}
    overrides={}
    for r in plans:
        p=r['data']
        if p.get('kind')=='reschedule.apply' and r['id'] not in canceled and p.get('created_day','0001-01-01')<=as_of:
            overrides.update(p.get('overrides',{}))
    return {d for d,p in overrides.items() if p.get('mode') in {'mock_day','final_rest','final_review'}}
