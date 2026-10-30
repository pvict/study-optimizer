"""Painel de atenção: interações sem banco, rede ou migração."""
from streamlit.testing.v1 import AppTest
from test_study_attention import state,dataset,DAY,PATH


def app(states=None,datasets=None):
    test=AppTest.from_string('''
import streamlit as st
from types import SimpleNamespace
from osler.study_attention_ui import render_attention
service=SimpleNamespace(guide=SimpleNamespace(datasets=lambda:st.session_state['datasets']))
def record(topic_id,questions): st.session_state['record_target']=(topic_id,questions)
render_attention(service,st.session_state['view'],'2026-10-29',record)
''',default_timeout=30)
    test.session_state['view']={'states':states if states is not None else [state()],
                                'profile':{'institution_weights':{'USP':1}}}
    test.session_state['datasets']=datasets if datasets is not None else [dataset()]
    return test.run()


def test_overview_sources_unknown_contact_and_science_are_present():
    test=app(); assert not test.exception
    assert any('temas para olhar' in m.value for m in test.markdown)
    table=test.dataframe[0].value
    assert len(table)==1 and '12 questões' in table.iloc[0]['Incidência bruta']
    assert 'tabela #1' in table.iloc[0]['Fonte da incidência']
    assert table.iloc[0]['Último contato']=='Desconhecido'
    assert test.expander[0].label=='Como ler os dados e a ordem' and not test.expander[0].proto.expanded


def test_search_complete_table_and_register_exact_selected_topic():
    states=[state(str(i),path=PATH[:-1]+['Tema '+str(i)]) for i in range(40)]
    test=app(states); assert not test.exception
    # Todos também inclui temas sem incidência; a busca não trunca em um top-N.
    test.get('segmented_control')[0].set_value('Todos').run()
    assert len(test.dataframe[0].value)==40
    test.text_input(key='attention_search').set_value('Tema 39').run()
    assert len(test.dataframe[0].value)==1
    test.button(key='attention_record').click().run()
    assert test.session_state['record_target']==('39',20)


def test_open_topic_routes_to_existing_statistics_and_clears_residual_filters():
    test=app(); test.session_state['statistics_mode']='Repetidas'
    test.button(key='attention_open').click().run()
    assert not test.exception and test.session_state['adaptive_view']=='Temas e estatísticas'
    assert test.session_state['statistics_search']==' → '.join(PATH)
    assert test.session_state['statistics_area']==PATH[0]
    assert test.session_state['statistics_focus']=='Todos os temas'
    assert test.session_state['topics_tabs']=='Desempenho dos temas'
    assert 'statistics_mode' not in test.session_state


def test_empty_catalog_and_empty_search_have_actionable_honest_messages():
    test=app([]); assert not test.exception and not test.dataframe
    assert any('Importe um relatório' in c.value for c in test.caption)
    test=app(); test.text_input(key='attention_search').set_value('sem resultado').run()
    assert not test.exception and not test.dataframe
    assert 'Limpe a busca' in test.info[0].value
