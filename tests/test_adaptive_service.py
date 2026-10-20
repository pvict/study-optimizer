import pytest

from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry
from test_assessments import setup_assessment


def test_service_updates_plan_and_preserves_pdf_baseline(tmp_path,sample_pdf):
    repo,_,matching,row=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    before=repo.get_report(matching.qbank_report_id).to_dict()
    initial=service.overview('2026-10-15',120)
    assert initial['plan']['questions']>0
    service.save_entry(StudyEntry(row.qbank.path,'2026-10-15',10,correct=3),session_id='first')
    after=service.overview('2026-10-15',120)
    state=next(t for t in after['states'] if t['path']==row.qbank.path)
    assert state['priority']=='urgente'
    assert state['performance']['exact_n']==10
    assert state['answered_pdf']==44
    assert after['plan']['done_questions']==10
    assert after['plan']['questions'] <= initial['plan']['questions']-10
    assert repo.get_report(matching.qbank_report_id).to_dict()==before


def test_csv_imports_cumulative_and_blocks_separately_and_is_idempotent(tmp_path,sample_pdf):
    repo,_,_,row=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    text='id_sessao;tema;data;tipo;modalidade;questoes;acertos;percentual\nbase;'+ ' → '.join(row.qbank.path)+';2026-10-14;acumulado;mistas;100;90;\nblock;'+ ' → '.join(row.qbank.path)+';2026-10-15;bloco;novas;10;5;\n'
    assert service.import_text(text)==2
    assert service.import_text(text)==2
    assert len(service.store.active('2026-10-15'))==2
    state=next(t for t in service.overview('2026-10-15')['states'] if t['path']==row.qbank.path)
    assert state['performance']['exact_n']==10
    assert state['baseline']['questions']==100
    with pytest.raises(ValueError): service.import_text(text+'bad;Não existe;2026-10-15;bloco;novas;10;11;\n')
    assert len(service.store.active('2026-10-15'))==2


def test_recent_poor_session_protects_reduction_and_stale_declarations(tmp_path,sample_pdf):
    from osler.practical_reduction import PracticalReductionService
    repo,_,_,row=setup_assessment(tmp_path,sample_pdf)
    reduction=PracticalReductionService(repo)
    old=reduction.overview('2026-10-15')
    service=AdaptiveService(repo)
    service.save_entry(StudyEntry(row.qbank.path,'2026-10-15',10,correct=2),session_id='poor')
    assert reduction.overview('2026-10-15')['triage']==[]
    with pytest.raises(ValueError): reduction.record('aplicado',[old['triage'][0]['topic_id']],'2026-10-15',old['signature'],old['event_id'])


def test_plan_export_does_not_pretend_90_percent_is_probability_of_approval(tmp_path,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    view=service.overview('2026-10-15')
    exported=service.export(view)
    assert exported.is_file()
    assert 'approval_probability' not in view
    assert view['profile']['target_accuracy']==90


def test_new_poor_session_also_blocks_advanced_planner_approval(tmp_path,sample_pdf):
    from test_planner import setup_plan
    repo,_,_,row,planner,bid=setup_plan(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.save_entry(StudyEntry(row.qbank.path,'2026-10-15',10,correct=2),session_id='weak')
    item=planner.get_batch(bid)['items'][0]
    planner.transition(item['id'],'aguardando_validacao','Quero avaliar',item['revision'],'2026-10-15')
    item=planner.get_batch(bid)['items'][0]
    with pytest.raises(ValueError): planner.transition(item['id'],'aprovado_usuario','Escolhi',item['revision'],'2026-10-15',confirmed=True)


def test_reduced_cards_return_to_question_review_without_fake_contact(tmp_path,sample_pdf):
    from osler.practical_reduction import PracticalReductionService
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    reduction=PracticalReductionService(repo)
    view=reduction.overview('2026-10-15')
    reduction.record('aplicado',[view['triage'][0]['topic_id']],'2026-10-15',view['signature'],view['event_id'])
    state=next(s for s in AdaptiveService(repo).overview('2026-10-30')['states'] if s['topic_id']==view['triage'][0]['topic_id'])
    assert state['priority'] in {'alta','urgente'}
    assert state['last_contact'] is None
    assert 'redução' in state['reason']


def test_existing_user_performance_is_context_without_invented_sessions(tmp_path,sample_pdf):
    from test_classification import known
    repo,assessment,matching,row=setup_assessment(tmp_path,sample_pdf)
    assessment.save_observation(matching,row.row_id,known(),0)
    service=AdaptiveService(repo)
    view=service.overview('2026-10-15')
    state=next(t for t in view['states'] if t['path']==row.qbank.path)
    assert state['performance_source']=='observacao'
    assert state['performance']['reported_percent']==pytest.approx(.82)
    assert state['performance']['exact_n']==0
    assert state['last_contact'] is None
    assert service.store.active('2026-10-15')==[]
