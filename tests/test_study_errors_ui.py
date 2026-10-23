from pathlib import Path

from streamlit.testing.v1 import AppTest

from osler.adaptive_service import AdaptiveService
from osler.study_errors import ErrorStore
from osler.study_models import StudyEntry
from test_assessments import setup_assessment


def test_optional_quick_error_keeps_study_and_can_be_resolved(tmp_path, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    service = AdaptiveService(repo)
    topic = service.catalog('2026-10-15')[0][0]
    service.save_entry(StudyEntry(topic['path'], '2026-10-15', 10, correct=5), session_id='test-block')
    runner = tmp_path / 'errors_app.py'
    runner.write_text(f'''from pathlib import Path
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_errors_ui import render_quick_error, render_errors, render_error_context
service = AdaptiveService(Repository(Path({str(tmp_path)!r})))
render_quick_error(service, 'test-block')
render_error_context(service, {topic['path']!r}, '2026-10-15')
render_errors(service)
''', encoding='utf-8')
    app = AppTest.from_file(str(runner), default_timeout=60).run()
    assert not app.exception
    assert not ErrorStore(repo).active('2026-10-15')
    assert any('opcional' in e.label.lower() for e in app.expander)
    app.text_input(key='quick_error_test-block_0_note').set_value('Rever o conceito que faltou')
    app.button(key='quick_error_test-block_0_save').click().run()
    assert not app.exception and not app.error
    rows = ErrorStore(repo).active('2026-10-15')
    assert len(rows) == 1 and rows[0]['source_session_id'] == 'test-block'
    assert len(service.store.active('2026-10-15')) == 1
    app.run()
    assert len(ErrorStore(repo).active('2026-10-15')) == 1
    assert any('1 erro aberto' in c.value for c in app.caption)
    app.button(key='resolve_error_' + rows[0]['error_key']).click().run()
    assert not app.exception and not ErrorStore(repo).active('2026-10-15')
    assert ErrorStore(repo).events()[-1]['action'] == 'resolve'


def test_stale_resolution_preserves_updated_error(tmp_path, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    from osler.study_errors import StudyError
    store = ErrorStore(repo)
    saved = store.save(StudyError(['Área', 'Tema'], '2026-10-15', 'chute'))
    runner = tmp_path / 'errors_stale_app.py'
    runner.write_text(f'''from pathlib import Path
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_errors_ui import render_errors
render_errors(AdaptiveService(Repository(Path({str(tmp_path)!r}))))
''', encoding='utf-8')
    app = AppTest.from_file(str(runner), default_timeout=60).run()
    assert not app.exception
    store.save(StudyError(['Área', 'Tema'], '2026-10-15', 'chute', note='Atualizado'),
               error_key=saved['error_key'], expected_version=1)
    app.button(key='resolve_error_' + saved['error_key']).click().run()
    assert not app.exception and app.error
    assert store.active('2026-10-15')[0]['note'] == 'Atualizado'
