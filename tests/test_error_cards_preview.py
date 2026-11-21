from osler.error_cards_service import ErrorCardsService
from osler.models import stable_topic_id
from test_error_cards import node
from test_error_cards_service import setup


def test_preview_compares_remaining_counts_without_subtracting_old_progress_twice(tmp_path):
    service,day,html=setup(tmp_path)
    service.import_html(html,'old.html',day,'pending',service.token())
    service.record(stable_topic_id(['Área','A']),day,20,0,None,'done',service.token())
    fresh=('<div>'+node('Área',180,branch='down')+node('A',80,20)+node('B',100,20)+'</div>').encode()
    before=service._events();files=list(service.repo.exports.rglob('*'))
    preview=service.preview_html(fresh,'new.html',day,'pending')
    assert service._events()==before and list(service.repo.exports.rglob('*'))==files
    assert preview['current_remaining']==180 and preview['tree']['total']==180
    assert next(r for r in preview['comparison'] if r['Tema'].endswith('A'))['Diferença']==0
    service.import_html(fresh,'new.html',day,'pending',preview['token'])
    view=service.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert view['remaining']==180 and view['done_today']==20


def test_preview_flags_missing_root_and_duplicate_file(tmp_path):
    service,day,html=setup(tmp_path)
    original=service.import_html(html,'old.html',day,'pending',service.token())
    assert service.preview_html(html,'again.html',day,'pending')['duplicate_id']==original
    other=('<div>'+node('Outra área',5,branch='down')+node('Novo',5,20)+'</div>').encode()
    preview=service.preview_html(other,'partial.html',day,'pending')
    assert preview['missing_roots']==['Área']
    assert any(not r['No arquivo'] for r in preview['comparison'])


def test_inventory_preview_does_not_claim_the_total_is_pending(tmp_path):
    service,day,html=setup(tmp_path)
    preview=service.preview_html(html,'inventory.html',day,'inventory')
    assert preview['pending_after'] is None
    assert all(r['Diferença'] is None for r in preview['comparison'])


def test_backdated_capture_keeps_later_creations_in_the_preview_balance(tmp_path):
    from osler.study_storage import StudyStore
    from osler.study_models import StudyEntry
    service,day,html=setup(tmp_path)
    StudyStore(service.repo).save_batch([('late',StudyEntry(['Área','A'],day,10,8,cards_created=4),0)])
    preview=service.preview_html(html,'yesterday.html','2026-10-14','pending')
    assert preview['current_remaining']==4
    assert preview['pending_after']==204 and preview['retained_creations']==4
    service.import_html(html,'yesterday.html','2026-10-14','pending',preview['token'])
    actual=service.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert actual['remaining']==preview['pending_after']
