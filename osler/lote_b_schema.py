"""Migração aditiva dos registros opcionais do lote B."""


def migrate_lote_b(db):
    # A migração de provas pode ter aberto uma transação nesta mesma conexão.
    if not db.in_transaction: db.execute('BEGIN IMMEDIATE')
    db.execute('''CREATE TABLE IF NOT EXISTS study_errors (
        id INTEGER PRIMARY KEY,error_key TEXT NOT NULL,version INTEGER NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('save','void','resolve')),
        topic_path TEXT NOT NULL,day TEXT NOT NULL,source_session_id TEXT,
        cause TEXT NOT NULL,note TEXT NOT NULL,critical INTEGER NOT NULL CHECK(critical IN (0,1)),
        flashcard_hint TEXT,created_at TEXT NOT NULL,UNIQUE(error_key,version))''')
    db.execute('''CREATE TABLE IF NOT EXISTS mock_exams (
        id INTEGER PRIMARY KEY,exam_key TEXT NOT NULL,version INTEGER NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('save','void')),payload TEXT NOT NULL,
        created_at TEXT NOT NULL,UNIQUE(exam_key,version))''')
    db.execute('''CREATE TABLE IF NOT EXISTS mock_exam_areas (
        id INTEGER PRIMARY KEY,mock_exam_id INTEGER NOT NULL REFERENCES mock_exams(id),
        area TEXT NOT NULL,questions INTEGER NOT NULL,correct INTEGER NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS mock_exam_topics (
        id INTEGER PRIMARY KEY,mock_exam_id INTEGER NOT NULL REFERENCES mock_exams(id),
        path TEXT NOT NULL,questions INTEGER NOT NULL,correct INTEGER NOT NULL)''')
    if db.execute('PRAGMA user_version').fetchone()[0]<11: db.execute('PRAGMA user_version=11')
