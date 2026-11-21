"""Aplicação preparada em cópia, com publicação transacional e token de concorrência."""
from pathlib import Path
import tempfile
import sqlite3
from contextlib import closing
from .storage import Repository
from .study_agenda import StudyAgenda,planning_token
from .error_cards_service import ErrorCardsService
from .recovery import RecoveryService
from .files import write_immutable


def apply_recovery(repo,preview):
    if StudyAgenda(repo).token()!=preview['token']:raise ValueError('Os dados mudaram. Confira novamente a retomada.')
    with tempfile.TemporaryDirectory(prefix='osler-retomada-') as folder:
        stage=Repository(Path(folder))
        with repo._connection() as source,closing(sqlite3.connect(stage.db_path)) as target:source.backup(target)
        with repo._connection() as db:cutoff=db.execute('SELECT COALESCE(MAX(id),0) FROM study_plan_runs').fetchone()[0]
        cards=ErrorCardsService(stage)
        if preview['raw']:
            cards.import_html(preview['raw'],preview['filename'],preview['observed_day'],'pass',cards.token(),new_pass=True)
        snapshot=cards.latest_snapshot()
        queue=cards._context(preview['observed_day'])[2]
        topics=queue['topics']
        agenda=StudyAgenda(stage)
        RecoveryService(stage).save(preview['total'],preview['daily'],preview['limit'],preview['target'],preview['ceiling'],
            preview['start'],agenda.token(),topics,queue['snapshot_id'])
        from .adaptive_service import AdaptiveService
        service=AdaptiveService(stage);view=service.overview(preview['observed_day'])
        projected=view['agenda']['quantity_recovery']
        if projected['unassigned_questions'] or projected['unassigned_cards']:
            raise ValueError('A carga não cabe até a prova. Ajuste as metas e confira novamente.')
        context=service.replanning(preview['observed_day'],view=view)
        # Substituir apenas recuperações gerais; manter simulados, correções e treinos.
        for record in context['active']:
            if record.get('scope') is None and record.get('mode') in {'balanced','reviews','extra','custom'}:
                service.cancel_replan(record['id'],service.agenda.token())
        planned=service.preview_replan(preview['start'],90,'balanced')
        if planned['unassigned']:
            raise ValueError('Há temas atrasados sem vaga nos próximos 90 dias. Ajuste a carga e confira novamente.')
        if planned['rows']:service.apply_replan(planned)
        with stage._connection() as db:new_rows=db.execute('SELECT * FROM study_plan_runs WHERE id>? ORDER BY id',(cutoff,)).fetchall()
        from .backups import create_backup
        create_backup(repo)
        with repo._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if planning_token(db)!=preview['token']:raise ValueError('Os dados mudaram. Confira novamente a retomada.')
            for file in stage.exports.rglob('*'):
                if file.is_file():
                    target=repo.exports/file.relative_to(stage.exports);target.parent.mkdir(parents=True,exist_ok=True)
                    write_immutable(target,file.read_bytes())
            for row in new_rows:
                db.execute('INSERT INTO study_plan_runs(id,payload,digest,created_at) VALUES(?,?,?,?)',tuple(row))
    return True
