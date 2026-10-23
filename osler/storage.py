"""Originais imutáveis em disco e importações transacionais em SQLite."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .models import Report
from .files import write_immutable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Repository:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.originals = self.root / "originals"
        self.exports = self.root / "exports"
        self.originals.mkdir(parents=True, exist_ok=True)
        self.exports.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "osler.sqlite3"
        with self._connection() as db:
            schema_version = db.execute("PRAGMA user_version").fetchone()[0]
            if schema_version > 12:
                raise ValueError("Banco de versão mais recente. Atualize o aplicativo antes de abrir estes dados.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS reports (
                    file_sha256 TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL,
                    filename TEXT NOT NULL, kind TEXT NOT NULL, scope TEXT NOT NULL,
                    report_date TEXT, imported_at TEXT NOT NULL,
                    duplicate_of TEXT REFERENCES reports(file_sha256),
                    complete INTEGER NOT NULL, payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS reports_content ON reports(content_sha256);
                CREATE TABLE IF NOT EXISTS records (
                    report_id TEXT NOT NULL REFERENCES reports(file_sha256),
                    ordinal INTEGER NOT NULL, topic_id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY (report_id, ordinal)
                );
                CREATE INDEX IF NOT EXISTS records_topic ON records(topic_id);
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, event TEXT NOT NULL,
                    report_id TEXT NOT NULL REFERENCES reports(file_sha256), details TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS topic_matches (
                    id INTEGER PRIMARY KEY,
                    qbank_report TEXT NOT NULL, flashcards_report TEXT NOT NULL,
                    qbank_ordinal INTEGER NOT NULL, flashcards_ordinal INTEGER NOT NULL,
                    note TEXT NOT NULL CHECK(length(trim(note)) > 0),
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    FOREIGN KEY (qbank_report,qbank_ordinal) REFERENCES records(report_id,ordinal),
                    FOREIGN KEY (flashcards_report,flashcards_ordinal) REFERENCES records(report_id,ordinal)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS match_active_q ON topic_matches(qbank_report,flashcards_report,qbank_ordinal) WHERE active=1;
                CREATE UNIQUE INDEX IF NOT EXISTS match_active_f ON topic_matches(qbank_report,flashcards_report,flashcards_ordinal) WHERE active=1;
                CREATE TABLE IF NOT EXISTS matching_events (
                    id INTEGER PRIMARY KEY,
                    decision_id INTEGER NOT NULL REFERENCES topic_matches(id),
                    created_at TEXT NOT NULL, action TEXT NOT NULL CHECK(action IN ('aprovar','remover')),
                    details TEXT NOT NULL
                );
            """)
            if schema_version < 2:
                db.execute("PRAGMA user_version = 2")

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def original_path(self, digest: str) -> Path:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Identificador inválido de arquivo.")
        return self.originals / f"{digest}.pdf"

    def _preserve(self, data: bytes, digest: str):
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Falha de integridade: hash não corresponde ao arquivo.")
        path = self.original_path(digest)
        try:
            write_immutable(path, data)
        except FileExistsError:
            raise ValueError("Falha de integridade: original existente divergente. Nenhum arquivo foi sobrescrito.") from None

    def save_report(self, report: Report, data: bytes) -> tuple[str, str | None]:
        self._preserve(data, report.file_sha256)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT duplicate_of FROM reports WHERE file_sha256=?", (report.file_sha256,)).fetchone()
            if existing:
                db.execute("INSERT INTO audit_events(created_at,event,report_id,details) VALUES(?,?,?,?)",
                           (utc_now(), "reimportacao_ignorada", report.file_sha256, "{}"))
                return "ja_importado", existing["duplicate_of"]
            complete = report.table_pages == report.page_count - 1 and not any(f.severity == "erro" for f in report.findings)
            duplicate = db.execute("SELECT file_sha256 FROM reports WHERE content_sha256=? AND complete=1 AND duplicate_of IS NULL ORDER BY imported_at LIMIT 1",
                                   (report.content_sha256,)).fetchone() if complete else None
            duplicate_of = duplicate["file_sha256"] if duplicate else None
            payload = report.to_dict()
            payload.pop("records")
            db.execute("INSERT INTO reports VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (report.file_sha256, report.content_sha256, report.filename, report.kind, report.scope,
                        report.report_date, utc_now(), duplicate_of, int(complete), json.dumps(payload, ensure_ascii=False)))
            db.executemany("INSERT INTO records VALUES(?,?,?,?)",
                           [(report.file_sha256, i, r.topic_id, json.dumps(asdict(r), ensure_ascii=False)) for i, r in enumerate(report.records)])
            state = "equivalente" if duplicate_of else "importado"
            db.execute("INSERT INTO audit_events(created_at,event,report_id,details) VALUES(?,?,?,?)",
                       (utc_now(), state, report.file_sha256, json.dumps({"duplicate_of": duplicate_of, "rows": len(report.records)})))
            return state, duplicate_of

    def get_report(self, digest: str) -> Report:
        with self._connection() as db:
            found = db.execute("SELECT payload FROM reports WHERE file_sha256=?", (digest,)).fetchone()
            if not found:
                raise KeyError("Relatório não encontrado.")
            data = json.loads(found["payload"])
            data["records"] = [json.loads(row["payload"]) for row in db.execute("SELECT payload FROM records WHERE report_id=? ORDER BY ordinal", (digest,))]
        return Report.from_dict(data)

    def list_reports(self, include_duplicates: bool = True) -> list[dict]:
        query = "SELECT file_sha256,content_sha256,filename,kind,scope,report_date,imported_at,duplicate_of,complete FROM reports"
        if not include_duplicates:
            query += " WHERE duplicate_of IS NULL"
        with self._connection() as db:
            return [dict(row) for row in db.execute(query + " ORDER BY kind,scope,imported_at")]

    def audit_events(self) -> list[dict]:
        with self._connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM audit_events ORDER BY id")]

    def active_matches(self, qbank_id: str, flashcards_id: str) -> list[dict]:
        with self._connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM topic_matches WHERE qbank_report=? AND flashcards_report=? AND active=1 ORDER BY id",
                (qbank_id, flashcards_id))]

    def _add_match(self, qbank_id: str, flashcards_id: str, qi: int, fi: int, note: str) -> int:
        # Apenas o serviço valida a semântica; o banco garante referências e 1:1.
        try:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                cursor = db.execute("INSERT INTO topic_matches(qbank_report,flashcards_report,qbank_ordinal,flashcards_ordinal,note,created_at) VALUES(?,?,?,?,?,?)",
                                    (qbank_id, flashcards_id, qi, fi, note.strip(), utc_now()))
                decision_id = cursor.lastrowid
                details = {"qbank_report": qbank_id, "flashcards_report": flashcards_id,
                           "qbank_ordinal": qi, "flashcards_ordinal": fi, "note": note.strip()}
                db.execute("INSERT INTO matching_events(decision_id,created_at,action,details) VALUES(?,?,?,?)",
                           (decision_id, utc_now(), "aprovar", json.dumps(details, ensure_ascii=False)))
                return decision_id
        except sqlite3.IntegrityError as exc:
            raise ValueError("Associação conflitante ou registro inválido. Nenhuma decisão foi substituída.") from exc

    def _remove_match(self, decision_id: int):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT * FROM topic_matches WHERE id=? AND active=1", (decision_id,)).fetchone()
            if not current:
                raise ValueError("Associação não encontrada ou já removida.")
            db.execute("UPDATE topic_matches SET active=0 WHERE id=?", (decision_id,))
            db.execute("INSERT INTO matching_events(decision_id,created_at,action,details) VALUES(?,?,?,?)",
                       (decision_id, utc_now(), "remover", json.dumps(dict(current), ensure_ascii=False)))

    def matching_events(self, qbank_id: str | None = None, flashcards_id: str | None = None) -> list[dict]:
        query = "SELECT e.* FROM matching_events e JOIN topic_matches m ON m.id=e.decision_id"
        params = ()
        if qbank_id is not None and flashcards_id is not None:
            query += " WHERE m.qbank_report=? AND m.flashcards_report=?"
            params = (qbank_id, flashcards_id)
        with self._connection() as db:
            return [dict(row) for row in db.execute(query + " ORDER BY e.id", params)]
