from copy import deepcopy
import pandas as pd

from streamlit.testing.v1 import AppTest

from osler.study_models import StudyEntry
from test_daily_swaps import service_fixture
from test_planner_snapshot import context


def history_app(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    topics[0]['planner_snapshot']=context(n=0,percent=None,contact=None)
    topics[1]['planner_snapshot']=context(n=34,percent=73.5)
    service.save_entry(StudyEntry(topics[0]['path'],'2026-10-15',17,11,mode='mistas',confident_correct=0),'recent')
    before=deepcopy(service.store.active('2026-10-15'))
    app=AppTest.from_string('''
import streamlit as st
from osler.study_tables_ui import render_topic_table
render_topic_table(st.session_state.service,lambda *args:None)
''',default_timeout=60)
    app.session_state['service']=service
    return app.run(),service,before


def test_imported_view_also_shows_recent_app_counts_without_adding_denominators(tmp_path,monkeypatch):
    app,service,before=history_app(tmp_path,monkeypatch)
    assert not app.exception
    frame=next(d.value for d in app.dataframe if 'Tema' in d.value and 'Estado' in d.value)
    assert 'Questões no app' in frame and 'Questões no histórico' in frame
    row=frame.loc[frame['Tema']=='A'].iloc[0]
    assert row['Questões no app']==17 and row['Questões no histórico']==0
    assert abs(row['Acerto no app (%)']-100*11/17)<.01
    assert row['Convicção (%)']==0
    assert len([c for c in frame.columns if c.startswith('Convicção') and c.endswith('(%)')])==1
    assert service.store.active('2026-10-15')==before
    app.radio(key='statistics_source').set_value('Blocos registrados no app').run()
    frame=next(d.value for d in app.dataframe if 'Questões' in d.value)
    assert frame['Questões'].sum()==17


def test_history_list_shows_app_results_and_unknown_imported_confidence_separately(tmp_path,monkeypatch):
    app,_,_=history_app(tmp_path,monkeypatch)
    app.text_input(key='statistics_search').set_value('A').run()
    app.radio(key='statistics_layout').set_value('Lista').run()
    assert not app.exception
    assert any('17' in m.value and 'no app' in m.value and '64.7%' in m.value for m in app.markdown)
    originals=next(d.value for d in app.dataframe if 'Convicção na Osler (%)' in d.value)
    row=originals.loc[originals['Tema']=='A'].iloc[0]
    assert row['Convicção no app (%)']==0 and pd.isna(row['Convicção na Osler (%)'])
