"""Verificação de compatibilidade antes de abrir um banco recuperado."""
from contextlib import closing
import json
import sqlite3

from .models import Report

SCHEMA = {
    2: {"reports": "file_sha256 content_sha256 filename kind scope report_date imported_at duplicate_of complete payload",
        "records": "report_id ordinal topic_id payload", "audit_events": "id created_at event report_id details",
        "topic_matches": "id qbank_report flashcards_report qbank_ordinal flashcards_ordinal note created_at active",
        "matching_events": "id decision_id created_at action details"},
    3: {"assessment_contexts": "row_id qbank_report flashcards_report qbank_ordinal flashcards_ordinal path revision",
        "observations": "id row_id observation_date payload digest created_at active", "observation_events": "id observation_id action created_at details",
        "classifier_policies": "id name payload digest created_at"},
    4: {"planner_batches": "id name note qbank_report_id flashcards_report_id analysis_date config created_at",
        "planner_items": "id batch_id row_id topic_key snapshot status revision note reevaluation_date approved_date applied_date reactivated_date action_date updated_at",
        "planner_events": "id item_id action previous_status new_status action_date created_at details"},
    5: {"planning_measurements": "id payload digest created_at", "routine_profiles": "id name payload digest created_at"},
    6: {"guide_settings": "id payload created_at", "guide_days": "id day payload digest created_at", "incidence_datasets": "id payload digest created_at"},
    7: {"reduction_actions": "id payload digest created_at"},
    8: {"study_events": "id session_id version action payload created_at", "study_profiles": "id payload created_at", "study_plan_runs": "id payload digest created_at"},
    9: {"study_days": "day revision payload updated_at"},
    10: {"exam_targets": "id target_id version action payload created_at"},
    11: {"study_errors": "id error_key version action topic_path day source_session_id cause note critical flashcard_hint created_at",
         "mock_exams": "id exam_key version action payload created_at",
         "mock_exam_areas": "id mock_exam_id area questions correct",
         "mock_exam_topics": "id mock_exam_id path questions correct"},
    12: {"algorithm_parameters":"version payload created_at","algorithm_selections":"id parameter_version created_at",
         "weekly_reviews":"id week_key version action payload created_at"},
}


def check_database(path):
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Banco falhou na verificação de integridade.")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if not 2 <= version <= 12:
                raise ValueError("Versão do banco não suportada.")
            for required_version, tables in SCHEMA.items():
                if required_version > version:
                    continue
                for table, fields in tables.items():
                    columns = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                    if not set(fields.split()).issubset(columns):
                        raise ValueError(f"Estrutura SQLite incompatível: {table}.")
            reports = db.execute("SELECT file_sha256,payload FROM reports").fetchall()
            for digest, payload in reports:
                data = json.loads(payload)
                data["records"] = [json.loads(r[0]) for r in db.execute("SELECT payload FROM records WHERE report_id=? ORDER BY ordinal", (digest,))]
                Report.from_dict(data)
            if version>=10:
                from .exam_goals import ExamTarget
                for payload, in db.execute('SELECT payload FROM exam_targets'):
                    ExamTarget(**json.loads(payload)).validate()
            if version>=11:
                from .study_errors import StudyError
                from .mock_exams import MockExam
                for row in db.execute('SELECT topic_path,day,cause,note,source_session_id,critical,flashcard_hint FROM study_errors'):
                    path,day,cause,note,source,critical,hint=row
                    if critical not in (0,1): raise ValueError('Marcação de erro inválida no backup.')
                    StudyError(json.loads(path),day,cause,note,source,bool(critical),hint).validate()
                for event_id,payload in db.execute('SELECT id,payload FROM mock_exams'):
                    mock=MockExam(**json.loads(payload)).validate()
                    areas=[dict(zip(('area','questions','correct'),r)) for r in db.execute(
                        'SELECT area,questions,correct FROM mock_exam_areas WHERE mock_exam_id=? ORDER BY id',(event_id,))]
                    topics=[{'path':json.loads(r[0]),'questions':r[1],'correct':r[2]} for r in db.execute(
                        'SELECT path,questions,correct FROM mock_exam_topics WHERE mock_exam_id=? ORDER BY id',(event_id,))]
                    if areas!=mock.areas or topics!=mock.topics: raise ValueError('Detalhes de simulado incompatíveis no backup.')
            if version>=12:
                from .algorithm_parameters import AlgorithmParameters
                for parameter_version,payload in db.execute('SELECT version,payload FROM algorithm_parameters'):
                    p=AlgorithmParameters(**json.loads(payload)).validate()
                    if p.version!=parameter_version: raise ValueError('Versão de parâmetros incompatível.')
                from .weekly_review import validate_weekly
                for week_key,payload in db.execute('SELECT week_key,payload FROM weekly_reviews'):
                    validate_weekly(week_key,json.loads(payload))
            return version, [r[0] for r in reports]
    except (sqlite3.Error, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("Estrutura ou conteúdo do banco incompatível com o aplicativo.") from exc
