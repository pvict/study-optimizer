"""C4: semanas alinhadas, fontes separadas e correções auditáveis."""
import csv
from importlib import import_module, util
from io import StringIO

import pytest

from osler.adaptive_service import AdaptiveService
from osler.mock_exams import MockExam, MockExams
from osler.storage import Repository
from osler.study_errors import ErrorStore, StudyError
from osler.study_models import StudyEntry


def weekly_module():
    assert util.find_spec('osler.weekly_review'), 'Falta a revisão semanal C4'
    return import_module('osler.weekly_review')


def test_weekly_review_corrections_are_immutable_and_cas(tmp_path):
    module = weekly_module()
    repo = Repository(tmp_path)
    store = module.WeeklyReviewStore(repo)
    first = store.save('2026-10-12', {'blocked': 'Plantão', 'load_change': '', 'needs_rest': False})
    with pytest.raises(ValueError, match='outra tela|mudou|atualizad'):
        store.save('2026-10-12', {'blocked': 'Perdido'}, expected_version=0)
    second = store.save('2026-10-12', {'blocked': 'Carga', 'needs_rest': True}, expected_version=1)
    assert second['version'] == 2 and first['review']['answers']['blocked'] == 'Plantão'
    assert len(store.active()) == 1 and len(store.events()) == 2
    store.void('2026-10-12', 2)
    assert store.active() == [] and len(store.events()) == 3
    assert store.events()[0]['review']['answers']['blocked'] == 'Plantão'
    with pytest.raises(ValueError):
        store.save('2026-10-15', {'blocked': ''})


def test_weekly_summary_aligns_weekday_and_never_pools_sources(tmp_path):
    module = weekly_module()
    service = AdaptiveService(Repository(tmp_path))
    service.store.save_batch([
        ('old', StudyEntry(['Área', 'Tema'], '2026-10-05', 10, correct=5), 0),
        ('old-friday', StudyEntry(['Área', 'Tema'], '2026-10-09', 100, correct=100), 0),
        ('new', StudyEntry(['Área', 'Tema'], '2026-10-12', 10, correct=8), 0),
        ('repeat', StudyEntry(['Área', 'Tema'], '2026-10-13', 20, correct=20, mode='repetidas'), 0),
        ('approx', StudyEntry(['Área', 'Tema'], '2026-10-13', 30, percent=90), 0),
        ('snapshot', StudyEntry(['Área', 'Tema'], '2026-10-14', 1000, correct=950, kind='acumulado'), 0),
    ])
    MockExams(service.repository).save(MockExam('2026-10-14', 100, 75, areas=[{'area': 'Área', 'questions': 100, 'correct': 75}]))
    ErrorStore(service.repository).save(StudyError(['Área', 'Tema'], '2026-10-14', 'chute'))
    report = module.weekly_summary(service, '2026-10-15')
    assert report['current']['start'] == '2026-10-12'
    assert report['previous']['end'] == '2026-10-08'
    rows = {(r['area'], r['source']): r for r in report['accuracy']}
    assert rows[('Área', 'bloco_novas')]['current']['questions'] == 10
    assert rows[('Área', 'bloco_novas')]['change_pp'] == pytest.approx(30)
    assert rows[('Área', 'bloco_repetidas')]['current']['accuracy'] == 1
    assert rows[('Área', 'simulado')]['current']['questions'] == 100
    assert report['current']['open_errors'] == 1
    assert report['changes']['open_errors'] is None
    assert report['current']['adhesion']['planned_blocks'] == 0
    assert report['current']['adhesion']['rate'] is None


def test_adhesion_uses_saved_plan_and_absence_counts_mock_days(tmp_path):
    module = weekly_module()
    service = AdaptiveService(Repository(tmp_path))
    service.store.save_batch([('done', StudyEntry(['Área', 'Tema'], '2026-10-12', 10, correct=7), 0)])
    service.store.save_plan({'kind': 'daily_schedule', 'plan': {'date': '2026-10-12', 'items': [
        {'path': ['Área', 'Tema'], 'questions': 10}, {'path': ['Área', 'Outro'], 'questions': 10}]}})
    summary = module.weekly_summary(service, '2026-10-15')
    assert summary['current']['adhesion'] == {'planned_blocks': 2, 'done_blocks': 1, 'rate': .5}
    assert module.absence_notice(service, '2026-10-15')['days'] == 3
    MockExams(service.repository).save(MockExam('2026-10-14', 10, 7))
    assert module.absence_notice(service, '2026-10-15') is None


def test_empty_absence_does_not_invent_last_study(tmp_path):
    assert weekly_module().absence_notice(AdaptiveService(Repository(tmp_path)), '2026-10-15') is None


def test_consolidated_csv_preserves_versions_and_sanitizes_user_cells(tmp_path):
    assert util.find_spec('osler.consolidated_export'), 'Falta CSV consolidado C4'
    export = import_module('osler.consolidated_export')
    service = AdaptiveService(Repository(tmp_path))
    entry = StudyEntry(['=AREA()', 'Tema'], '2026-10-12', 10, correct=7, source='@origem')
    service.store.save_batch([('s1', entry, 0)])
    service.store.void('s1', 1)
    ErrorStore(service.repository).save(StudyError(['Área', 'Tema'], '2026-10-12', 'chute', note='=DANGER()'))
    MockExams(service.repository).save(MockExam('2026-10-14', 10, 6, name='+Simulado'))
    data = export.consolidated_csv(service, '2026-10-15')
    rows = list(csv.DictReader(StringIO(data.decode('utf-8-sig')), delimiter=';'))
    sessions = [r for r in rows if r['tipo'] == 'sessao']
    assert len(sessions) == 2 and all(r['ativo'] == 'nao' for r in sessions)
    assert sessions[0]['area'] == "'=AREA()" and sessions[0]['origem'] == "'@origem"
    assert next(r for r in rows if r['tipo'] == 'erro')['observacao'] == "'=DANGER()"
    assert next(r for r in rows if r['tipo'] == 'simulado')['nome'] == "'+Simulado"
    assert len(rows) == 4
