import hashlib,json
from pathlib import Path
import pytest
from osler.adaptive_planning import topic_states
from osler.study_models import AdaptiveProfile
from osler.study_statistics import topic_statistics
from test_adaptive_planning import topic,session


def context(n=34,percent=73.5,contact='2026-10-10'):
    return {'observed_date':'2026-10-15','unique_questions':n,'confident_accuracy_pct':percent,
            'pending_reviews':1,'last_contact':contact,'available_questions':100,'dataset_id':1}


def state(snapshot,entries=None,as_of='2026-10-15'):
    t={**topic(answered=20),'planner_snapshot':snapshot}
    return topic_states([t],entries or [],[],{},as_of,AdaptiveProfile())[0]


def test_accumulated_safety_is_not_new_attempt_evidence_or_mastery():
    t=state(context(100,100))
    assert t['performance']['exact_n']==0 and t['confidence']['exact_n']==0
    assert t['planner_safety']['confident_accuracy_pct']==100
    assert t['learning_state']!='dominado'
    assert t['last_contact']=='2026-10-10' and t['days_without_contact']==5
    assert t['available_new']==0
    row=topic_statistics([t],[],'Dia','2026-10-15')[0]
    assert row['Questões']==0 and row['Acerto (%)'] is None
    assert row['Segurança acumulada Osler (%)']==100
    assert row['Questões distintas Osler']==100


def test_low_safety_affects_priority_without_changing_new_question_posterior():
    entries=[session(n=20,correct=19,day='2026-10-14')]
    low=state(context(100,50),entries)
    high=state(context(100,95),entries)
    assert low['priority']=='urgente' and low['low_accuracy']
    assert low['score']>high['score']
    assert low['performance']==high['performance']
    assert low['performance']['exact_n']==20
    assert low['last_contact']=='2026-10-14'


def test_snapshot_precedence_for_bank_and_no_same_day_double_count():
    entries=[session(n=5,correct=4,day='2026-10-15'),session(n=3,correct=2,day='2026-10-16')]
    t=state(context(),entries,as_of='2026-10-16')
    assert t['available_new']==100-34-3
    assert t['bank_balance_uncertain']
    future=state({**context(),'observed_date':'2026-10-17'},[],as_of='2026-10-16')
    assert future.get('planner_safety') is None
    assert future['available_new']==80


def test_snapshot_loader_requires_confirmed_semantics_hash_and_safe_paths(tmp_path):
    from osler.planner_snapshot import load_planner_contexts
    from osler.storage import Repository
    repo=Repository(tmp_path)
    folder=repo.exports/'planner'/'test'; folder.mkdir(parents=True)
    payload={'observed_date':'2026-10-15','source_sha256':'abc','rows':[{
        'path':['Área','Tema'],'questions_done_snapshot':34,'questions_available_snapshot':100,
        'confident_accuracy_pct':73.5,'pending_reviews':1,'days_since_contact':5}]}
    raw=json.dumps(payload).encode(); (folder/'snapshot.json').write_bytes(raw)
    ds={'id':1,'source_kind':'manual_osler_planner_export','qbank_report_id':'pdf',
        'observed_date':'2026-10-15','source_sha256':'abc','source_path':str(folder.relative_to(repo.root)),
        'planner_snapshot':'snapshot.json','snapshot_sha256':hashlib.sha256(raw).hexdigest(),
        'planner_semantics':{'questions':'unique','accuracy':'latest_confident_including_reviews','contact':'any_question_including_reviews'}}
    result,warnings=load_planner_contexts(repo,[ds],'pdf','2026-10-15')
    assert not warnings
    assert result[('area','tema')]['unique_questions']==34
    assert result[('area','tema')]['last_contact']=='2026-10-10'
    assert load_planner_contexts(repo,[{**ds,'planner_semantics':{}}],'pdf','2026-10-15')[0]=={}
    assert load_planner_contexts(repo,[ds],'pdf','2026-10-14')[0]=={}
    assert load_planner_contexts(repo,[ds],'other-pdf','2026-10-15')[0]=={}
    assert load_planner_contexts(repo,[{**ds,'source_path':'../outside'}],'pdf','2026-10-15')[1]
    (folder/'snapshot.json').write_bytes(b'{}')
    assert load_planner_contexts(repo,[ds],'pdf','2026-10-15')[1]


def test_snapshot_in_catalog_and_ui_does_not_inflate_period_totals(tmp_path,monkeypatch,project_root,sample_pdf):
    from test_assessments import setup_assessment
    from osler.guide_service import GuideService
    from osler.adaptive_service import AdaptiveService
    from osler.planner_snapshot import SEMANTICS
    from streamlit.testing.v1 import AppTest
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    guide=GuideService(repo)
    report=guide._report('qbank','2026-10-15')
    target=next(r for r in report.records if r.is_leaf and r.studied)
    folder=repo.exports/'planner'/'fixture'; folder.mkdir(parents=True)
    content={'observed_date':'2026-10-15','source_sha256':'fixture','rows':[{
        'path':target.path,'questions_done_snapshot':34,'questions_available_snapshot':100,
        'confident_accuracy_pct':73.5,'pending_reviews':1,'days_since_contact':5}]}
    raw=json.dumps(content).encode(); (folder/'snapshot.json').write_bytes(raw)
    guide.store.save_dataset({'institutions':['Teste'],'observed_date':'2026-10-15','unit':'questoes','rows':[],
        'source_kind':'manual_osler_planner_export','planner_semantics':SEMANTICS,
        'qbank_report_id':report.file_sha256,'source_path':str(folder.relative_to(repo.root)),
        'planner_snapshot':'snapshot.json','snapshot_sha256':hashlib.sha256(raw).hexdigest(),'source_sha256':'fixture'})
    warnings=AdaptiveService(repo).overview('2026-10-15')['warnings']
    assert any('saldo' in w.lower() for w in warnings)
    assert not any('PDF sem data' in w for w in warnings)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    app.radio(key='adaptive_view').set_value('Temas e estatísticas').run()
    assert not app.exception
    frame=next(d.value for d in app.dataframe if 'Convicção (%)' in d.value.columns)
    assert frame['Convicção (%)'].dropna().tolist()==[73.5]
    assert frame.loc[frame['Convicção (%)'].notna(),'Questões no histórico'].tolist()==[34]
    app.radio(key='statistics_source').set_value('Blocos registrados no app').run()
    frame=next(d.value for d in app.dataframe if 'Questões' in d.value.columns)
    assert frame['Questões'].sum()==0
    assert not AdaptiveService(repo).store.active('2026-10-15')
