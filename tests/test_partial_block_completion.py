from copy import deepcopy
import pytest
from test_daily_swaps import service_fixture
from osler.study_models import StudyEntry
from osler.planner_completion import complete_partial_block,restore_complement


DAY='2026-10-15'


def prepared(tmp_path,monkeypatch):
    s,topics=service_fixture(tmp_path,monkeypatch)
    s.agenda.append({'kind':'reschedule.apply','created_day':DAY,'cutoff':0,'selected':['A'],
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':DAY,'original_due':DAY,'questions':20}],
        'overrides':{}},s.agenda.token())
    s.remember_day(s.overview(DAY))
    return s,topics


def test_partial_completion_is_reversible_and_preserves_real_results_and_returns(tmp_path,monkeypatch):
    s,topics=prepared(tmp_path,monkeypatch)
    s.save_entry(StudyEntry(topics[0]['path'],DAY,8,6,confident_correct=5),'actual')
    before=s.overview(DAY);events=deepcopy(s.store.events())
    decision=complete_partial_block(s,DAY,'A',before['planning_token'])
    after=s.overview(DAY)
    assert 'A' not in {i['topic_id'] for i in after['plan']['items']}
    assert after['plan']['done_questions']==8
    assert after['review_queue']==before['review_queue']
    a=next(t for t in before['states'] if t['topic_id']=='A')
    b=next(t for t in after['states'] if t['topic_id']=='A')
    for k in ['performance','confidence','last_contact','theme_review_due','review_interval_days']:assert a[k]==b[k]
    assert s.store.events()==events
    assert not any(r['topic_id']=='A' for r in s.replanning('2026-10-16')['backlog'])
    restore_complement(s,DAY,decision,s.agenda.token())
    assert 'A' in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}


def test_unregistered_stale_and_edited_partial_results_are_checked(tmp_path,monkeypatch):
    s,topics=prepared(tmp_path,monkeypatch)
    with pytest.raises(ValueError):complete_partial_block(s,DAY,'A',s.agenda.token())
    stale=s.agenda.token()
    s.save_entry(StudyEntry(topics[0]['path'],DAY,8,6),'actual')
    with pytest.raises(ValueError):complete_partial_block(s,DAY,'A',stale)
    complete_partial_block(s,DAY,'A',s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],DAY,4,3),'actual',1)
    assert 'A' in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}


def test_card_action_confirms_completion_and_allows_undo(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    s,topics=prepared(tmp_path,monkeypatch)
    s.save_entry(StudyEntry(topics[0]['path'],DAY,8,6),'actual')
    app=AppTest.from_string('''
import streamlit as st
from osler.planner_completion_ui import render_completion_choice,render_completions
s=st.session_state.service
view=s.overview('2026-10-15')
for item in view['plan']['items']:render_completion_choice(s,view,item)
render_completions(s,view)
''',default_timeout=30)
    app.session_state['service']=s;app.run()
    next(b for b in app.button if b.label=='Concluir bloco com menos questões').click().run()
    assert not app.exception and app.button(key='action_confirm')
    assert 'A' in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}
    app.button(key='action_confirm').click().run()
    assert not app.exception and 'A' not in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}
    next(b for b in app.button if b.label=='Desfazer dispensa').click().run()
    app.button(key='action_confirm').click().run()
    assert not app.exception and 'A' in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}


def test_overdue_partial_booking_is_closed_today_and_can_be_closed_again_after_undo(tmp_path,monkeypatch):
    s,topics=prepared(tmp_path,monkeypatch)
    s.agenda.append({'kind':'reschedule.apply','created_day':DAY,'cutoff':0,'selected':['A'],
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':DAY,'original_due':'2026-10-13','questions':20}],
        'overrides':{}},s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],DAY,8,6),'actual')
    first=complete_partial_block(s,DAY,'A',s.agenda.token())
    assert not any(r['topic_id']=='A' for r in s.replanning(DAY)['backlog'])
    assert s.overview(DAY)['plan']['planner_completions'][0]['skipped_questions']==12
    restore_complement(s,DAY,first,s.agenda.token())
    second=complete_partial_block(s,DAY,'A',s.agenda.token())
    assert first!=second
    assert 'A' not in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}


def test_mock_result_does_not_count_as_corrective_practice(tmp_path,monkeypatch):
    from osler.mock_exams import _prefix
    s,topics=prepared(tmp_path,monkeypatch)
    s.agenda.append({'kind':'reschedule.apply','created_day':DAY,'cutoff':0,'selected':['A'],
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':DAY,'original_due':DAY,'questions':20,
                 'correction':True,'source_exam_key':'example'}],'overrides':{}},s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],DAY,8,6),_prefix('example')+'topic')
    with pytest.raises(ValueError,match='Registre primeiro'):complete_partial_block(s,DAY,'A',s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],DAY,4,3),'correction')
    complete_partial_block(s,DAY,'A',s.agenda.token())
    decision=s.overview(DAY)['plan']['planner_completions'][0]
    assert decision['required_completed']==4 and decision['skipped_questions']==16


def test_new_extra_has_its_own_credit_and_is_not_hidden_by_old_completion(tmp_path,monkeypatch):
    s,topics=prepared(tmp_path,monkeypatch)
    s.save_entry(StudyEntry(topics[0]['path'],DAY,8,6),'actual')
    complete_partial_block(s,DAY,'A',s.agenda.token())
    s.add_topic(DAY,'A',10,0)
    assert 'A' in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}
    with pytest.raises(ValueError,match='Registre primeiro'):complete_partial_block(s,DAY,'A',s.agenda.token())
    s.remember_day(s.overview(DAY))
    assert any(r['topic_id']=='A' for r in s.replanning('2026-10-16')['backlog'])


def test_finishing_a_later_extra_does_not_reopen_an_independent_closed_booking(tmp_path,monkeypatch):
    s,topics=prepared(tmp_path,monkeypatch)
    s.save_entry(StudyEntry(topics[0]['path'],DAY,8,6),'actual')
    complete_partial_block(s,DAY,'A',s.agenda.token())
    s.add_topic(DAY,'A',10,0)
    s.save_entry(StudyEntry(topics[0]['path'],DAY,4,3),'extra')
    complete_partial_block(s,DAY,'A',s.agenda.token())
    s.save_entry(StudyEntry(topics[0]['path'],DAY,10,8),'extra',1)
    assert 'A' not in {i['topic_id'] for i in s.overview(DAY)['plan']['items']}
