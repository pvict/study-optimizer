"""Medições e cenários locais imutáveis em versões."""
from dataclasses import asdict
import hashlib
import json

from .storage import utc_now


class PlanningStore:
    def __init__(self, repository):
        self.repository = repository
        with repository._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS planning_measurements (
                    id INTEGER PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS routine_profiles (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
                );
            """)
            if db.execute("PRAGMA user_version").fetchone()[0] < 5:
                db.execute("PRAGMA user_version=5")

    def save_measurement(self, measurement):
        measurement.validate()
        payload = json.dumps(asdict(measurement), sort_keys=True, ensure_ascii=False, allow_nan=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.repository._connection() as db:
            db.execute("INSERT OR IGNORE INTO planning_measurements(payload,digest,created_at) VALUES(?,?,?)", (payload, digest, utc_now()))
            return db.execute("SELECT id FROM planning_measurements WHERE digest=?", (digest,)).fetchone()[0]

    def measurements(self):
        with self.repository._connection() as db:
            return [{**dict(r), **json.loads(r["payload"])} for r in db.execute("SELECT * FROM planning_measurements ORDER BY id DESC")]

    def save_profile(self, name, config):
        config.validate()
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Informe o nome do cenário.")
        payload = json.dumps(config.to_dict(), sort_keys=True, ensure_ascii=False, allow_nan=False)
        digest = hashlib.sha256((name.strip()+payload).encode()).hexdigest()
        with self.repository._connection() as db:
            db.execute("INSERT OR IGNORE INTO routine_profiles(name,payload,digest,created_at) VALUES(?,?,?,?)", (name.strip(), payload, digest, utc_now()))
            return db.execute("SELECT id FROM routine_profiles WHERE digest=?", (digest,)).fetchone()[0]

    def profiles(self):
        with self.repository._connection() as db:
            return [{**dict(r), "config": json.loads(r["payload"])} for r in db.execute("SELECT * FROM routine_profiles ORDER BY id DESC")]
