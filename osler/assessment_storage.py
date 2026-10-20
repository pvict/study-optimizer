"""Histórico local de indicadores e critérios, sem substituir registros PDF."""
import hashlib
import json

from .classification import ClassifierConfig
from .observations import Observation
from .storage import utc_now


class AssessmentStore:
    def __init__(self, repository):
        self.repository = repository
        with repository._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS assessment_contexts (
                    row_id TEXT PRIMARY KEY, qbank_report TEXT NOT NULL REFERENCES reports(file_sha256),
                    flashcards_report TEXT NOT NULL REFERENCES reports(file_sha256),
                    qbank_ordinal INTEGER, flashcards_ordinal INTEGER,
                    path TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(qbank_report,qbank_ordinal) REFERENCES records(report_id,ordinal),
                    FOREIGN KEY(flashcards_report,flashcards_ordinal) REFERENCES records(report_id,ordinal)
                );
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY, row_id TEXT NOT NULL REFERENCES assessment_contexts(row_id),
                    observation_date TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL,
                    created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    UNIQUE(row_id,digest)
                );
                CREATE TABLE IF NOT EXISTS observation_events (
                    id INTEGER PRIMARY KEY, observation_id INTEGER NOT NULL REFERENCES observations(id),
                    action TEXT NOT NULL CHECK(action IN ('registrar','desconsiderar')),
                    created_at TEXT NOT NULL, details TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS classifier_policies (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, payload TEXT NOT NULL,
                    digest TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
                );
            """)
            if db.execute("PRAGMA user_version").fetchone()[0] < 3:
                db.execute("PRAGMA user_version=3")

    def revision(self, row_id):
        with self.repository._connection() as db:
            found = db.execute("SELECT revision FROM assessment_contexts WHERE row_id=?", (row_id,)).fetchone()
            return found[0] if found else 0

    def save_batch(self, matching, changes):
        row_map = {r.row_id: r for r in matching.rows}
        ids = []
        with self.repository._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for row_id, observation, expected_revision in changes:
                observation.validate()
                row = row_map[row_id]
                payload = json.dumps(observation.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
                digest = hashlib.sha256(payload.encode()).hexdigest()
                duplicate = db.execute("SELECT id,active FROM observations WHERE row_id=? AND digest=?", (row_id, digest)).fetchone()
                if duplicate and duplicate["active"]:
                    ids.append(duplicate["id"])
                    continue
                if duplicate:
                    raise ValueError("Observação idêntica já desconsiderada. Registre nova observação com nota explicativa.")
                current = db.execute("SELECT revision FROM assessment_contexts WHERE row_id=?", (row_id,)).fetchone()
                actual_revision = current[0] if current else 0
                if type(expected_revision) is not int or actual_revision != expected_revision:
                    raise ValueError("Revisão mudou desde a abertura. Atualize os dados/modelo CSV antes de salvar.")
                if not current:
                    db.execute("INSERT INTO assessment_contexts(row_id,qbank_report,flashcards_report,qbank_ordinal,flashcards_ordinal,path) VALUES(?,?,?,?,?,?)",
                               (row_id, matching.qbank_report_id, matching.flashcards_report_id, row.qbank_index, row.flashcards_index,
                                json.dumps((row.qbank or row.flashcards).path, ensure_ascii=False)))
                cursor = db.execute("INSERT INTO observations(row_id,observation_date,payload,digest,created_at) VALUES(?,?,?,?,?)",
                                    (row_id, observation.data_observacao, payload, digest, utc_now()))
                observation_id = cursor.lastrowid
                db.execute("UPDATE assessment_contexts SET revision=revision+1 WHERE row_id=?", (row_id,))
                db.execute("INSERT INTO observation_events(observation_id,action,created_at,details) VALUES(?,?,?,?)",
                           (observation_id, "registrar", utc_now(), json.dumps({"row_id": row_id, "revision": actual_revision+1})))
                ids.append(observation_id)
        return ids

    def selected(self, as_of):
        with self.repository._connection() as db:
            rows = db.execute("SELECT * FROM observations WHERE active=1 AND observation_date<=? ORDER BY observation_date,id", (as_of,)).fetchall()
        selected = {}
        for row in rows:
            selected[row["row_id"]] = {"id": row["id"], "observation": Observation(**json.loads(row["payload"]))}
        return selected

    def history(self, row_id):
        with self.repository._connection() as db:
            return [{**dict(r), "observation": json.loads(r["payload"])} for r in db.execute("SELECT * FROM observations WHERE row_id=? ORDER BY id", (row_id,))]

    def events(self):
        with self.repository._connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM observation_events ORDER BY id")]

    def revoke(self, observation_id, expected_revision):
        with self.repository._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT o.*,c.revision FROM observations o JOIN assessment_contexts c ON c.row_id=o.row_id WHERE o.id=? AND o.active=1", (observation_id,)).fetchone()
            if not row:
                raise ValueError("Observação não encontrada ou já desconsiderada.")
            if row["revision"] != expected_revision:
                raise ValueError("Revisão alterada. Atualize a tela antes de desconsiderar.")
            db.execute("UPDATE observations SET active=0 WHERE id=?", (observation_id,))
            db.execute("UPDATE assessment_contexts SET revision=revision+1 WHERE row_id=?", (row["row_id"],))
            db.execute("INSERT INTO observation_events(observation_id,action,created_at,details) VALUES(?,?,?,?)",
                       (observation_id, "desconsiderar", utc_now(), json.dumps({"row_id": row["row_id"]})))

    def save_policy(self, name, config):
        config.validate()
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Informe um nome para os critérios.")
        payload = json.dumps(config.to_dict(), sort_keys=True, allow_nan=False)
        digest = hashlib.sha256((name.strip()+payload).encode()).hexdigest()
        with self.repository._connection() as db:
            db.execute("INSERT OR IGNORE INTO classifier_policies(name,payload,digest,created_at) VALUES(?,?,?,?)", (name.strip(), payload, digest, utc_now()))
            return db.execute("SELECT id FROM classifier_policies WHERE digest=?", (digest,)).fetchone()[0]

    def policies(self):
        with self.repository._connection() as db:
            return [{**dict(r), "config": json.loads(r["payload"])} for r in db.execute("SELECT * FROM classifier_policies ORDER BY id DESC")]
