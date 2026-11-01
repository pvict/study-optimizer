from dataclasses import replace
import pytest
from osler.study_models import AdaptiveProfile
from osler.topic_grouping import grouping_candidates,grouped_frontier


def fixture():
    base=['Pediatria','Neonatologia','Infecções congênitas']
    def t(name,total,leaf=True):
        path=base+([name] if name else [])
        return {'topic_id':name or 'parent','path':path,'total':total,'is_leaf':leaf,'is_practice_unit':leaf}
    ts=[t('',100,False),t('A',50),t('B',50)]
    ds=[{'id':1,'observed_date':'2026-10-20','institutions':['USP'],'unit':'questoes',
         'rows':[{'path':base,'value':7},{'path':base+['A'],'value':3},{'path':base+['B'],'value':4}]}]
    return ts,ds,AdaptiveProfile(institution_weights={'USP':1},grouping_mode='balanced')


def test_full_subtree_once_and_default_unchanged():
    ts,ds,p=fixture();cs=grouping_candidates(ts,ds,p,'2026-10-30')
    assert cs[0]['evidence'][0]['value']==7 # Never parent + children = 14.
    assert cs[0]['evidence'][0]['area_total']==7
    assert cs[0]['recommended']
    grouped=grouped_frontier(ts,p,cs)
    assert len(grouped)==1 and grouped[0]['group_members']==['A','B']
    assert len(grouped_frontier(ts,replace(p,grouping_mode='osler'),cs))==2
    assert not ts[0].get('rollup')


@pytest.mark.parametrize('case',['high','inconsistent','reserved'])
def test_protects_high_unknown_inconsistent_and_booked(case):
    ts,ds,p=fixture();blocked=[]
    if case=='high':ds[0]['rows'][1]['value']=10;ds[0]['rows'][0]['value']=14
    if case=='inconsistent':ds[0]['rows'][0]['value']=99
    if case=='reserved':blocked=['A']
    cs=grouping_candidates(ts,ds,p,'2026-10-30',blocked)
    assert not cs[0]['eligible']
    assert len(grouped_frontier(ts,p,cs))==2


def test_partial_source_is_automatic_without_zero_imputation():
    ts,ds,p=fixture();ds[0]['rows'].pop()
    cs=grouping_candidates(ts,ds,p,'2026-10-30')
    assert cs[0]['eligible'] and cs[0]['recommended'] and not cs[0]['complete_incidence']
    assert cs[0]['evidence'][0]['value']==7
    assert len(grouped_frontier(ts,p,cs))==1


@pytest.mark.parametrize('restriction',['high','reserved','contradiction','no_source'])
def test_missing_child_does_not_bypass_other_restrictions(restriction):
    ts,ds,p=fixture();ds[0]['rows'].pop();blocked=[]
    if restriction=='high':ds[0]['rows'][1]['value']=10;ds[0]['rows'][0]['value']=14
    if restriction=='reserved':blocked=['A']
    if restriction=='contradiction':ds[0]['rows'][0]['value']=2
    if restriction=='no_source':ds=[]
    cs=grouping_candidates(ts,ds,p,'2026-10-30',blocked)
    assert not cs[0]['eligible'] and not cs[0]['recommended']


def test_group_paths_validate_overlap():
    with pytest.raises(ValueError):
        AdaptiveProfile(grouping_paths=[['A','B','C'],['A','B','C','D']]).validate()


def test_service_preview_backup_reversal_and_stale_guard(tmp_path,sample_pdf):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    from osler.grouping_service import preview_grouping,apply_grouping,history
    repo,*_=setup_assessment(tmp_path,sample_pdf);s=AdaptiveService(repo)
    events=s.store.events();token=s.agenda.token()
    preview=preview_grouping(s,'balanced')
    assert s.agenda.token()==token
    apply_grouping(s,preview)
    assert s.store.profile()['profile']['grouping_mode']=='balanced'
    record=history(s)[-1]
    from pathlib import Path
    assert Path(record['preview']['backup']).is_file()
    assert record['preview']['before_calendar']==preview['before_calendar']
    with pytest.raises(ValueError):apply_grouping(s,preview)
    apply_grouping(s,preview_grouping(s,'osler'))
    assert s.store.profile()['profile']['grouping_mode']=='osler'
    assert s.store.events()==events


def test_child_result_does_not_become_group_mastery_or_contact():
    from osler.adaptive_planning import topic_states
    from osler.topic_grouping import protect_group_evidence
    ts,ds,p=fixture()
    for t in ts:
        t.update(answered_pdf=0,pdf_accuracy={'value':None,'operator':None,'raw':'-'},
                 report_date='2026-10-20',studied_cards=None,planner_snapshot=None)
    from osler.study_models import StudyEntry
    e={'session_id':'a','entry':StudyEntry(ts[1]['path'],'2026-10-29',20,correct=20,confident_correct=20).to_dict()}
    cs=grouping_candidates(ts,ds,p,'2026-10-30')
    leaves=topic_states(ts[1:],[e],ds,p.institution_weights,'2026-10-30',p)
    groups=topic_states(grouped_frontier(ts,p,cs),[e],ds,p.institution_weights,'2026-10-30',p)
    protect_group_evidence(groups,leaves)
    assert groups[0]['performance']['exact_n']==0
    assert groups[0]['last_contact'] is None and not groups[0]['review_committed']
    assert leaves[0]['performance']['exact_n']+leaves[1]['performance']['exact_n']==20


def test_grouping_screen_and_preview_are_read_only(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from streamlit.testing.v1 import AppTest
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    from pathlib import Path
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    app.button(key='nav_grouping').click().run()
    assert not app.exception
    from osler.adaptive_service import AdaptiveService
    s=AdaptiveService(repo);before=s.agenda.token()
    app.segmented_control(key='grouping_mode_choice').set_value('balanced').run()
    next(b for b in app.button if b.label=='Comparar calendário').click().run()
    assert not app.exception and s.agenda.token()==before
    assert app.session_state['grouping_preview']['mode']=='balanced'
    assert app.status[0].state=='complete'
    assert any('prévia abaixo' in status.label for status in app.status)


def test_grouping_progress_and_failure_feedback(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    from osler.grouping_service import preview_grouping
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    repo,*_=setup_assessment(tmp_path,sample_pdf);service=AdaptiveService(repo)
    events=[];token=service.agenda.token()
    plain=preview_grouping(service,'balanced')
    observed=preview_grouping(service,'balanced',progress=lambda *args:events.append(args))
    assert plain==observed and token==service.agenda.token()
    for phase in ['Calendário atual','Calendário proposto']:
        values=[(done,total) for label,done,total in events if label==phase]
        assert values[0][0]==0 and values[-1][0]==values[-1][1]
        assert values==sorted(values)
    import osler.grouping_ui as ui
    def fail(*a,**kw):raise ValueError('Dados mudaram. Gere outra prévia.')
    monkeypatch.setattr(ui,'preview_grouping',fail)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    app.button(key='nav_grouping').click().run()
    next(b for b in app.button if b.label=='Comparar calendário').click().run()
    assert not app.exception and app.status[0].state=='error'
    assert any('Dados mudaram' in e.value for e in app.error)
    assert not any(b.label=='Aplicar esta divisão' for b in app.button)


def test_reversal_preserves_pending_return_from_group(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from osler.adaptive_service import AdaptiveService
    from osler.grouping_service import preview_grouping,apply_grouping
    from osler.planner_service import today_local
    from osler.study_models import StudyEntry
    repo,*_=setup_assessment(tmp_path,sample_pdf);s=AdaptiveService(repo)
    ts,ds,p=fixture();day=today_local().isoformat()
    for t in ts:
        t.update(answered_pdf=0,pdf_accuracy={'value':None,'operator':None,'raw':'-'},report_date=day,studied_cards=None,planner_snapshot=None)
    ds[0]['observed_date']=day
    monkeypatch.setattr(s,'catalog',lambda as_of,include_parents=False:(ts if include_parents else ts[1:],{}))
    monkeypatch.setattr(s.guide,'datasets',lambda:ds)
    s.store.save_profile(replace(p,grouping_mode='osler',start_date=day,review_strategy='balanced_v2'),0)
    apply_grouping(s,preview_grouping(s,'balanced'))
    s.save_entry(StudyEntry(ts[0]['path'],day,20,correct=10,confident_correct=10))
    apply_grouping(s,preview_grouping(s,'osler'))
    v=s.overview(day)
    assert len(v['review_queue'])==1
    assert any(t.get('retained_group_return') and t['topic_id']=='parent' for t in v['planning_states'])
