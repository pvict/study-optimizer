import pytest
from osler.study_models import StudyEntry
from osler.study_storage import StudyStore
from osler.error_cards_service import ErrorCardsService
from osler.models import stable_topic_id
from test_error_cards_service import setup
from test_error_cards import node


def qview():return {'states':[],'plan':{'items':[]}}


def test_block_created_cards_add_once_and_correction_and_void_recalculate(tmp_path):
    s,day,html=setup(tmp_path);s.import_html(html,'cards.html',day,'pending',s.token());s.configure(0,{},s.token())
    store=StudyStore(s.repo);entry=StudyEntry(['Área','A'],day,20,15,cards_created=4)
    store.save_batch([('q',entry,0)]);v=s.overview(day,question_view=qview())
    assert v['remaining']==204 and v['created_cards']==4 and v['done_today']==0
    assert v['budget']==0 and v['items']==[]
    store.save_batch([('q',entry,0)]);assert s.overview(day,question_view=qview())['remaining']==204
    store.save_batch([('q',StudyEntry(['Área','A'],day,20,15,cards_created=7),1)])
    assert s.overview(day,question_view=qview())['remaining']==207
    store.void('q',2);assert s.overview(day,question_view=qview())['remaining']==200


def test_created_cards_work_without_html_and_are_not_question_attempts(tmp_path):
    from osler.storage import Repository
    from osler.planner_service import today_local
    s=ErrorCardsService(Repository(tmp_path));store=StudyStore(s.repo);day=today_local().isoformat()
    store.save_batch([('q',StudyEntry(['Área','Tema novo'],day,10,8,cards_created=3),0)])
    v=s.overview(day,question_view=qview())
    assert v['has_queue'] and v['remaining']==3 and v['created_cards']==3 and v['snapshot'] is None
    s.record(stable_topic_id(['Área','Tema novo']),day,2,0,None,'cards',s.token())
    assert s.overview(day,question_view=qview())['remaining']==1
    assert len(store.active(day))==1 and store.active(day)[0]['entry']['questions']==10


def test_new_html_absorbs_previous_creations_and_keeps_history(tmp_path):
    s,day,html=setup(tmp_path);s.import_html(html,'cards.html',day,'pending',s.token());store=StudyStore(s.repo)
    store.save_batch([('q',StudyEntry(['Área','A'],day,10,8,cards_created=4),0)])
    fresh=(node('Área',204,branch='down')+node('A',104,20)+node('B',100,20)).encode()
    s.import_html(fresh,'fresh.html',day,'pending',s.token())
    v=s.overview(day,question_view=qview());assert v['remaining']==204 and v['created_cards']==0
    store.save_batch([('q',StudyEntry(['Área','A'],day,10,8,cards_created=5),1)])
    assert s.overview(day,question_view=qview())['remaining']==204
    store.save_batch([('q2',StudyEntry(['Área','A'],day,10,8,cards_created=2),0)])
    assert s.overview(day,question_view=qview())['remaining']==206


def test_creation_correction_does_not_consume_other_topics_after_cards_studied(tmp_path):
    s,day,html=setup(tmp_path);s.import_html(html,'cards.html',day,'pending',s.token());store=StudyStore(s.repo)
    store.save_batch([('q',StudyEntry(['Área','C'],day,10,8,cards_created=5),0)])
    s.record(stable_topic_id(['Área','C']),day,5,0,None,'cards',s.token())
    store.void('q',1);v=s.overview(day,question_view=qview())
    assert v['remaining']==200 and v['unreconciled_covered']==5 and v['done_today']==5


def test_question_updates_invalidate_old_card_form_token(tmp_path):
    s,day,html=setup(tmp_path);s.import_html(html,'cards.html',day,'pending',s.token());token=s.token()
    StudyStore(s.repo).save_batch([('q',StudyEntry(['Área','A'],day,10,8,cards_created=2),0)])
    with pytest.raises(ValueError):s.record(stable_topic_id(['Área','A']),day,1,0,None,'stale',token)


def test_older_dated_html_does_not_absorb_cards_created_on_a_later_day(tmp_path):
    from datetime import date,timedelta
    s,day,html=setup(tmp_path);store=StudyStore(s.repo)
    old=(date.fromisoformat(day)-timedelta(days=1)).isoformat()
    store.save_batch([('q',StudyEntry(['Área','A'],day,10,8,cards_created=4),0)])
    s.import_html(html,'yesterday.html',old,'pending',s.token())
    assert s.overview(day,question_view=qview())['remaining']==204
    assert s.overview(old,question_view=qview())['remaining']==200


def test_legacy_snapshot_absorbs_only_earlier_recorded_sessions(tmp_path):
    import json
    from osler.study_storage import _encoded
    s,day,html=setup(tmp_path);store=StudyStore(s.repo)
    store.save_batch([('old',StudyEntry(['Área','A'],day,10,8,cards_created=4),0)])
    sid=s.import_html(html,'legacy.html',day,'pending',s.token())
    with s.repo._connection() as db:
        payload=json.loads(db.execute('SELECT payload FROM study_plan_runs WHERE id=?',(sid,)).fetchone()[0])
        payload.pop('study_event_cutoff')
        db.execute('UPDATE study_plan_runs SET payload=?,created_at=? WHERE id=?',(_encoded(payload),'2026-10-15T10:00:00+00:00',sid))
        db.execute('UPDATE study_events SET created_at=?',('2026-10-15T09:00:00+00:00',))
    store.save_batch([('new',StudyEntry(['Área','A'],day,10,8,cards_created=3),0)])
    with s.repo._connection() as db:db.execute('UPDATE study_events SET created_at=? WHERE session_id=?',('2026-10-15T11:00:00+00:00','new'))
    v=s.overview(day,question_view=qview())
    assert v['remaining']==203 and v['created_session_ids']==['new']


def test_inventory_does_not_become_pending_when_new_cards_are_created(tmp_path):
    s,day,html=setup(tmp_path);s.import_html(html,'inventory.html',day,'inventory',s.token())
    StudyStore(s.repo).save_batch([('q',StudyEntry(['Área','A'],day,10,8,cards_created=4),0)])
    v=s.overview(day,question_view=qview())
    assert v['remaining']==4 and v['source_total']==200 and len(v['topics'])==1


def test_prior_day_view_keeps_its_snapshot_instead_of_later_import(tmp_path):
    from datetime import date,timedelta
    s,day,html=setup(tmp_path);old=(date.fromisoformat(day)-timedelta(days=1)).isoformat()
    sid=s.import_html(html,'old.html',old,'pending',s.token())
    fresh=(node('Área',190,branch='down')+node('A',90,20)+node('B',100,20)).encode()
    s.import_html(fresh,'new.html',day,'pending',s.token())
    v=s.overview(old,question_view=qview())
    assert v['snapshot']['id']==sid and v['remaining']==200


def test_created_cards_cannot_be_added_to_aggregate_or_contact():
    for kind in ('acumulado','contato'):
        with pytest.raises(ValueError):StudyEntry(['Tema'],'2026-10-15',10,8,kind=kind,cards_created=2).validate()


def test_specific_topic_guard_and_optional_csv_and_export(tmp_path,sample_pdf):
    import csv
    from io import StringIO
    from osler.adaptive_service import AdaptiveService
    from osler.consolidated_export import consolidated_csv
    from test_assessments import setup_assessment
    repo,*_=setup_assessment(tmp_path,sample_pdf);service=AdaptiveService(repo)
    topics,_=service.catalog('2026-10-15',include_parents=True)
    parent=next(t for t in topics if not t['is_leaf'])
    with pytest.raises(ValueError):service.save_entry(StudyEntry(parent['path'],'2026-10-15',10,8,cards_created=2))
    leaf=next(t for t in topics if t['is_leaf'])
    text='id_sessao;tema;data;questoes;acertos;cards_criados\nq;'+' → '.join(leaf['path'])+';2026-10-15;10;8;3\n'
    service.import_text(text);service.import_text(text)
    assert len(service.store.active('2026-10-15'))==1
    rows=list(csv.DictReader(StringIO(consolidated_csv(service,'2026-10-15').decode('utf-8-sig')),delimiter=';'))
    assert rows[0]['cards_criados']=='3'


@pytest.mark.parametrize('value',[-1,1.5,True,5001])
def test_created_cards_require_a_bounded_nonnegative_integer(value):
    with pytest.raises(ValueError):StudyEntry(['Tema'],'2026-10-15',10,8,cards_created=value).validate()
