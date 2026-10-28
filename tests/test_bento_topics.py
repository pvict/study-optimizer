"""Cards de temas: bases exatas, paginação e ações, somente dados sintéticos."""
from copy import deepcopy
from html.parser import HTMLParser

import pytest
from streamlit.testing.v1 import AppTest

from osler.confidence_presentation import confidence_presentation
from osler.study_statistics import topic_statistics
from test_daily_swaps import service_fixture


PATH=['Clínica Médica','Tema']


def event(mode='novas',n=10,correct=0,percent=None,day='2026-10-15'):
    return {'entry':{'path':PATH,'day':day,'kind':'bloco','mode':mode,'questions':n,
                     'correct':correct,'percent':percent,'confident_correct':0 if correct is not None else None}}


def state():
    return {'topic_id':'topic','path':PATH,'priority':'normal','status':'diagnostico',
            'last_contact':None,'importance':None,'answered_pdf':80,'pdf_accuracy':{'raw':'95%'},
            'target_accuracy':90,'planner_safety':{'unique_questions':100,'confident_accuracy_pct':93,
                                                'observed_date':'2026-10-14'}}


def rows_for(events,mode='Todas'):
    return confidence_presentation(topic_statistics([state()],events,'Todo o período','2026-10-15',mode),
                                   events,'Todo o período','2026-10-15',mode,include_snapshot=True)


def test_all_mode_card_uses_exact_new_questions_without_pdf_repeat_mixed_or_approximate_counts():
    from osler.study_tables_ui import _topic_card_rows
    events=[event(),event('repetidas',30,30),event('mistas',20,10),event(n=50,correct=None,percent=80)]
    rows=rows_for(events);before=deepcopy(rows)
    cards=_topic_card_rows(rows,[state()],events,'Todo o período','2026-10-15','Todas')
    assert cards[0]['card_accuracy']==0
    assert cards[0]['card_exact_n']==10
    assert cards[0]['card_accuracy_label']=='Acerto em novas'
    assert cards[0]['Convicção principal (%)']==0
    assert cards[0]['Base da convicção'].startswith('App · 60 tentativas')
    assert rows==before


@pytest.mark.parametrize('mode,label,value,n',[('Repetidas','Acerto em repetidas',100,30),
                                             ('Mistas','Acerto em mistas',50,20),
                                             ('Novas','Acerto em novas',None,0)])
def test_explicit_mode_card_identifies_its_own_exact_base(mode,label,value,n):
    from osler.study_tables_ui import _topic_card_rows
    events=[event('repetidas',30,30),event('mistas',20,10),event(n=50,correct=None,percent=80)]
    cards=_topic_card_rows(rows_for(events,mode),[state()],events,'Todo o período','2026-10-15',mode)
    assert (cards[0]['card_accuracy_label'],cards[0]['card_accuracy'],cards[0]['card_exact_n'])==(label,value,n)


def list_app(rows,open_paths=()):
    app=AppTest.from_string('''
import streamlit as st
from osler.study_tables_ui import _topic_list
def record(topic_id,questions):
    st.session_state['record_target']=(topic_id,questions)
_topic_list(st.session_state['rows'],'synthetic',record,open_error_paths=st.session_state['open_paths'])
''')
    app.session_state['rows']=rows
    app.session_state['open_paths']=open_paths
    return app.run()


def test_cards_paginate_twelve_and_keep_specific_record_and_advance_actions():
    row=rows_for([event()])[0]
    rows=[{**row,'topic_id':str(i),'Tema':'Tema '+str(i),'catalog_available':i!=24} for i in range(25)]
    app=list_app(rows)
    assert not app.exception
    assert [b.key for b in app.button if b.key.startswith('list_record_')]==['list_record_'+str(i) for i in range(12)]
    app.number_input(key='statistics_list_page_synthetic').set_value(2).run()
    assert not app.exception
    assert [b.key for b in app.button if b.key.startswith('list_record_')]==['list_record_'+str(i) for i in range(12,24)]
    app.button(key='list_record_12').click().run()
    assert app.session_state['record_target']==('12',10)
    app.button(key='list_extra_12').click().run()
    assert app.session_state['extra_topic']=='12' and app.session_state['adaptive_view']=='Meu dia'
    app.number_input(key='statistics_list_page_synthetic').set_value(3).run()
    assert len([b for b in app.button if b.key.startswith('list_record_')])==1
    assert app.button(key='list_record_24').disabled and app.button(key='list_extra_24').disabled


def test_card_html_escapes_long_topic_and_shows_zero_separately_from_missing():
    from osler.study_tables_ui import _topic_card_rows
    title='<script>alert(1)</script> & '+('Tema longo '*30)
    cards=_topic_card_rows(rows_for([event()]),[state()],[event()],'Todo o período','2026-10-15')
    cards[0]['Tema']=title;cards[0]['Caminho']='Clínica Médica → '+title
    app=list_app(cards)
    assert not app.exception
    class Content(HTMLParser):
        def __init__(self):
            super().__init__();self.tags=[];self.text=[]
        def handle_starttag(self,tag,attrs):self.tags.append(tag)
        def handle_data(self,data):self.text.append(data)
    parser=Content()
    for element in app.get('html'):parser.feed(element.value)
    text=''.join(parser.text)
    assert 'script' not in parser.tags and title in text
    assert '0.0%' in text and 'n=10' in text
    missing=_topic_card_rows(rows_for([]),[state()],[],'Todo o período','2026-10-15')
    app=list_app(missing)
    assert not app.exception
    assert any('n=0' in h.value and '—' in h.value for h in app.get('html'))
    assert any('Sem acertos exatos' in c.value for c in app.caption)


def test_card_errors_action_only_exists_for_open_path_and_routes_to_normalized_topic():
    rows=rows_for([event()])
    app=list_app(rows)
    assert not any(b.label=='Ver erros' for b in app.button)
    app=list_app(rows,[('clinica medica','tema')])
    assert not app.exception
    app.session_state['study_errors_cause']='outro'
    app.session_state['study_errors_page']=3
    app.button(key='list_errors_topic').click().run()
    assert app.session_state['topics_tabs']=='Erros abertos'
    assert app.session_state['study_errors_topic']==('clinica medica','tema')
    assert app.session_state.get('study_errors_cause') is None
    assert app.session_state['study_errors_page']==1


def test_area_pills_count_and_sync_with_existing_selectbox_and_clear(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    topics[1]['path'][0]='Pediatria'
    app=AppTest.from_string('''
import streamlit as st
from osler.study_tables_ui import render_topic_table
render_topic_table(st.session_state['service'],lambda *args:None)
''',default_timeout=60)
    app.session_state['service']=service
    app.run()
    assert not app.exception
    pills=next((p for p in app.get('button_group') if p.key=='statistics_area_pills'),None)
    assert pills is not None
    assert 'Pediatria · 1' in pills.options and 'Área · 4' in pills.options
    assert app.radio(key='statistics_layout').value=='Tabela'
    pills.set_value('Pediatria').run()
    assert not app.exception and app.selectbox(key='statistics_area').value=='Pediatria'
    frame=next(d.value for d in app.dataframe if 'Estado' in d.value)
    assert list(frame['Tema'])==['B']
    app.selectbox(key='statistics_area').set_value('Área').run()
    assert next(p for p in app.get('button_group') if p.key=='statistics_area_pills').value=='Área'
    app.button(key='statistics_clear').click().run()
    assert not app.exception and app.selectbox(key='statistics_area').value=='Todas'
    assert next(p for p in app.get('button_group') if p.key=='statistics_area_pills').value=='Todas'
