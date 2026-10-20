"""Preferências e registros curtos com histórico, sem exigir justificativas."""
import hashlib
import json

from .assessment_storage import AssessmentStore
from .planner_storage import PlannerStore
from .planning_storage import PlanningStore
from .storage import utc_now


class GuideStore:
    def __init__(self, repository):
        self.repository = repository
        AssessmentStore(repository)
        PlannerStore(repository)
        PlanningStore(repository)
        with repository._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS guide_settings (id INTEGER PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS guide_days (id INTEGER PRIMARY KEY, day TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS incidence_datasets (id INTEGER PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
            """)
            if db.execute("PRAGMA user_version").fetchone()[0] < 6:
                db.execute("PRAGMA user_version=6")

    def settings(self):
        with self.repository._connection() as db:
            row = db.execute("SELECT * FROM guide_settings ORDER BY id DESC LIMIT 1").fetchone()
            return {"id": row["id"], "settings": json.loads(row["payload"])} if row else None

    def save_settings(self, settings, expected_id):
        settings.validate()
        with self.repository._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            latest = db.execute("SELECT COALESCE(MAX(id),0) FROM guide_settings").fetchone()[0]
            if latest != expected_id:
                raise ValueError("Seu plano foi atualizado em outra tela. Reabra para salvar.")
            return db.execute("INSERT INTO guide_settings(payload,created_at) VALUES(?,?)", (json.dumps(settings.to_dict(), ensure_ascii=False), utc_now())).lastrowid

    def _append(self, table, payload):
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        with self.repository._connection() as db:
            db.execute("INSERT OR IGNORE INTO incidence_datasets(payload,digest,created_at) VALUES(?,?,?)", (encoded, digest, utc_now()))
            return db.execute(f"SELECT id FROM {table} WHERE digest=?", (digest,)).fetchone()[0]

    def save_day(self, payload):
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        with self.repository._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT id,payload FROM guide_days WHERE day=? ORDER BY id DESC LIMIT 1", (payload["day"],)).fetchone()
            if previous and json.loads(previous["payload"]) == payload:
                return previous["id"]
            # O predecessor distingue a volta a um estado antigo de um clique repetido.
            digest = hashlib.sha256(f"{previous['id'] if previous else 0}:{encoded}".encode()).hexdigest()
            return db.execute("INSERT INTO guide_days(day,payload,digest,created_at) VALUES(?,?,?,?)", (payload["day"], encoded, digest, utc_now())).lastrowid

    def save_dataset(self, payload):
        return self._append("incidence_datasets", payload)

    def datasets(self):
        with self.repository._connection() as db:
            return [{"id": r["id"], **json.loads(r["payload"])} for r in db.execute("SELECT * FROM incidence_datasets ORDER BY id")]

    def days(self):
        with self.repository._connection() as db:
            rows = db.execute("SELECT * FROM guide_days ORDER BY id").fetchall()
        latest = {}
        for row in rows:
            latest[row["day"]] = {"id": row["id"], **json.loads(row["payload"])}
        return sorted(latest.values(), key=lambda r: r["day"], reverse=True)
