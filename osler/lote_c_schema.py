"""Schema 12: estrutura de calibração e revisão semanal, sem resultados fictícios."""
import json
from .algorithm_parameters import V1
from .storage import utc_now


def migrate_lote_c(db):
    if not db.in_transaction: db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS algorithm_parameters(version INTEGER PRIMARY KEY,payload TEXT NOT NULL,created_at TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS algorithm_selections(id INTEGER PRIMARY KEY,parameter_version INTEGER NOT NULL REFERENCES algorithm_parameters(version),created_at TEXT NOT NULL)')
    db.execute("CREATE TABLE IF NOT EXISTS weekly_reviews(id INTEGER PRIMARY KEY,week_key TEXT NOT NULL,version INTEGER NOT NULL,action TEXT NOT NULL CHECK(action IN ('save','void')),payload TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(week_key,version))")
    db.execute('INSERT OR IGNORE INTO algorithm_parameters(version,payload,created_at) VALUES(?,?,?)',(1,json.dumps(V1.to_dict(),sort_keys=True),utc_now()))
    if db.execute('PRAGMA user_version').fetchone()[0]<12: db.execute('PRAGMA user_version=12')
