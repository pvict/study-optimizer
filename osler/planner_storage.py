"""Lotes locais e eventos preservados; nenhum acesso à plataforma de estudo."""
import json
import sqlite3

from .storage import utc_now
from .models import normalize_path
from .study_signals import study_event_token

STATES = ("sugerido", "aguardando_validacao", "aprovado_usuario", "aplicado_manualmente", "reativado", "cancelado")
TRANSITIONS = {
    "sugerido": {"aguardando_validacao", "cancelado"},
    "aguardando_validacao": {"aprovado_usuario", "cancelado"},
    "aprovado_usuario": {"aplicado_manualmente", "cancelado"},
    "aplicado_manualmente": {"reativado"}, "reativado": set(), "cancelado": set(),
}


class PlannerStore:
    def __init__(self, repository):
        self.repository = repository
        with repository._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS planner_batches (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, note TEXT NOT NULL,
                    qbank_report_id TEXT NOT NULL REFERENCES reports(file_sha256),
                    flashcards_report_id TEXT NOT NULL REFERENCES reports(file_sha256),
                    analysis_date TEXT NOT NULL, config TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS planner_items (
                    id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES planner_batches(id),
                    row_id TEXT NOT NULL, topic_key TEXT NOT NULL, snapshot TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('sugerido','aguardando_validacao','aprovado_usuario','aplicado_manualmente','reativado','cancelado')),
                    revision INTEGER NOT NULL DEFAULT 1, note TEXT NOT NULL,
                    reevaluation_date TEXT, approved_date TEXT, applied_date TEXT, reactivated_date TEXT,
                    action_date TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(batch_id,row_id)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS planner_active_topic ON planner_items(topic_key)
                    WHERE status IN ('sugerido','aguardando_validacao','aprovado_usuario','aplicado_manualmente');
                CREATE TABLE IF NOT EXISTS planner_events (
                    id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES planner_items(id),
                    action TEXT NOT NULL, previous_status TEXT, new_status TEXT NOT NULL,
                    action_date TEXT NOT NULL, created_at TEXT NOT NULL, details TEXT NOT NULL
                );
            """)
            if db.execute("PRAGMA user_version").fetchone()[0] < 4:
                db.execute("PRAGMA user_version=4")

    @staticmethod
    def _token(db):
        return (*tuple(db.execute(f"SELECT COALESCE(MAX(id),0) FROM {table}").fetchone()[0]
                     for table in ("observations", "observation_events", "matching_events")), study_event_token(db))

    def evidence_token(self):
        with self.repository._connection() as db:
            return self._token(db)

    def _check_evidence(self, db, token):
        if token is not None and self._token(db) != token:
            raise ValueError("Evidência alterada durante a validação. Atualize a tela antes de decidir.")

    @staticmethod
    def _overlap(left, right):
        a, b = normalize_path(left), normalize_path(right)
        return a[:len(b)] == b or b[:len(a)] == a

    def _no_newer_evidence(self, db, snapshot, as_of):
        observed = snapshot["observation"]["data_observacao"]
        for row in db.execute("""SELECT o.id,o.observation_date,COALESCE(f.payload,q.payload) AS payload FROM observations o
                JOIN assessment_contexts c ON c.row_id=o.row_id
                LEFT JOIN records f ON f.report_id=c.flashcards_report AND f.ordinal=c.flashcards_ordinal
                LEFT JOIN records q ON q.report_id=c.qbank_report AND q.ordinal=c.qbank_ordinal
                WHERE o.active=1 AND o.observation_date<=? AND
                (o.observation_date>? OR (o.observation_date=? AND o.id>?))""",
                              (as_of, observed, observed, snapshot["observation_id"])):
            if self._overlap(snapshot["flashcards_path"], json.loads(row["payload"])["path"]):
                raise ValueError("Evidência mais recente em outro contexto ou nível. Faça nova avaliação; indicadores não foram transferidos automaticamente.")

    def create(self, metadata, items, token=None):
        try:
            with self.repository._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                self._check_evidence(db, token)
                cursor = db.execute("INSERT INTO planner_batches(name,note,qbank_report_id,flashcards_report_id,analysis_date,config,created_at) VALUES(?,?,?,?,?,?,?)",
                                    (metadata["name"], metadata["note"], metadata["qbank_report_id"], metadata["flashcards_report_id"],
                                     metadata["analysis_date"], json.dumps(metadata["config"], ensure_ascii=False), utc_now()))
                batch_id = cursor.lastrowid
                for item in items:
                    self._no_newer_evidence(db, item["snapshot"], metadata["analysis_date"])
                    for active in db.execute("SELECT snapshot FROM planner_items WHERE status IN ('sugerido','aguardando_validacao','aprovado_usuario','aplicado_manualmente')"):
                        if self._overlap(item["snapshot"]["flashcards_path"], json.loads(active["snapshot"])["flashcards_path"]):
                            raise ValueError("Tema ou ancestral/descendente já pertence a lote ativo; os caminhos se sobrepõem.")
                    cursor = db.execute("INSERT INTO planner_items(batch_id,row_id,topic_key,snapshot,status,note,action_date,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                                        (batch_id, item["row_id"], item["topic_key"], json.dumps(item["snapshot"], ensure_ascii=False, allow_nan=False),
                                         "sugerido", metadata["note"], metadata["analysis_date"], utc_now()))
                    db.execute("INSERT INTO planner_events(item_id,action,new_status,action_date,created_at,details) VALUES(?,?,?,?,?,?)",
                               (cursor.lastrowid, "criar", "sugerido", metadata["analysis_date"], utc_now(), json.dumps({"note": metadata["note"]}, ensure_ascii=False)))
                return batch_id
        except sqlite3.IntegrityError as exc:
            raise ValueError("Tema já pertence a um lote ativo ou seleção duplicada. Nenhum lote parcial foi salvo.") from exc

    @staticmethod
    def _item(row):
        return {**dict(row), "snapshot": json.loads(row["snapshot"])}

    def get_batch(self, batch_id):
        with self.repository._connection() as db:
            found = db.execute("SELECT * FROM planner_batches WHERE id=?", (batch_id,)).fetchone()
            if not found:
                raise ValueError("Lote não encontrado.")
            return {**dict(found), "config": json.loads(found["config"]),
                    "items": [self._item(r) for r in db.execute("SELECT * FROM planner_items WHERE batch_id=? ORDER BY id", (batch_id,))]}

    def item(self, item_id):
        with self.repository._connection() as db:
            found = db.execute("SELECT * FROM planner_items WHERE id=?", (item_id,)).fetchone()
            if not found:
                raise ValueError("Item não encontrado.")
            return self._item(found)

    def list_batches(self):
        with self.repository._connection() as db:
            return [dict(r) for r in db.execute("SELECT id,name,note,analysis_date,created_at FROM planner_batches ORDER BY id DESC")]

    def change(self, item_id, expected_revision, note, reevaluation_date, *, status=None, action_date=None, evidence_token=None):
        with self.repository._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._check_evidence(db, evidence_token)
            row = db.execute("SELECT * FROM planner_items WHERE id=?", (item_id,)).fetchone()
            if not row:
                raise ValueError("Item não encontrado.")
            if type(expected_revision) is not int or row["revision"] != expected_revision:
                raise ValueError("Revisão mudou. Atualize o lote antes de registrar uma decisão.")
            if status == "aprovado_usuario":
                self._no_newer_evidence(db, json.loads(row["snapshot"]), action_date)
            previous = row["status"]
            if status is not None and status not in TRANSITIONS[previous]:
                raise ValueError("Transição de estado inválida. Siga as etapas de validação e aprovação manual.")
            status = status or previous
            if action_date is not None and action_date < row["action_date"]:
                raise ValueError("Data da ação não pode preceder o último estado registrado.")
            action_date = action_date or row["action_date"]
            dates = {name: row[name] for name in ("approved_date", "applied_date", "reactivated_date")}
            for target, field in [("aprovado_usuario", "approved_date"), ("aplicado_manualmente", "applied_date"), ("reativado", "reactivated_date")]:
                if status == target and status != previous:
                    dates[field] = action_date
            db.execute("UPDATE planner_items SET status=?,revision=revision+1,note=?,reevaluation_date=?,approved_date=?,applied_date=?,reactivated_date=?,action_date=?,updated_at=? WHERE id=?",
                       (status, note, reevaluation_date, dates["approved_date"], dates["applied_date"], dates["reactivated_date"], action_date, utc_now(), item_id))
            db.execute("INSERT INTO planner_events(item_id,action,previous_status,new_status,action_date,created_at,details) VALUES(?,?,?,?,?,?,?)",
                       (item_id, "estado" if status != previous else "anotar", previous, status, action_date, utc_now(),
                        json.dumps({"note": note, "reevaluation_date": reevaluation_date, "revision": expected_revision+1}, ensure_ascii=False)))

    def events(self):
        with self.repository._connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM planner_events ORDER BY id")]

    def all_items(self):
        with self.repository._connection() as db:
            return [self._item(r) for r in db.execute("SELECT * FROM planner_items ORDER BY id")]
