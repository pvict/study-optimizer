from ui_actions import confirm_action
from streamlit.testing.v1 import AppTest
from osler.models import stable_topic_id
from test_error_cards_service import setup


def test_home_shows_todays_decks_and_opens_their_queue(tmp_path, monkeypatch, project_root):
    service, day, html = setup(tmp_path)
    service.import_html(html, 'cards.html', day, 'pending', service.token())
    monkeypatch.setenv('OSLER_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(project_root / 'app.py'), default_timeout=60).run()
    assert not app.exception
    assert any(h.value == 'Flashcards de hoje' for h in app.subheader)
    assert any('200 cards para fazer' in m.value for m in app.markdown)
    assert any('A · 100 cards' in item.proto.body and 'B · 100 cards' in item.proto.body for item in app.get('html'))
    app.session_state['ec_tabs'] = 'Temas'
    app.button(key='ec_open_' + day).click().run()
    assert not app.exception
    assert app.session_state['ec_tabs'] == 'Hoje'
    assert any(b.label == 'Registrar cards deste tema' for b in app.button)


def test_flashcard_ui_shows_real_lot_and_records_without_question_sessions(tmp_path,monkeypatch):
    s,day,html=setup(tmp_path);s.import_html(html,'cards.html',day,'pending',s.token())
    monkeypatch.setenv('ERROR_CARDS_TEST_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.error_cards_ui import render_error_cards
render_error_cards(Repository(os.environ['ERROR_CARDS_TEST_ROOT']))
''',default_timeout=60).run()
    assert not app.exception
    assert any('Hoje'==t.label for t in app.tabs)
    assert any('200' in m.value and 'cards' in m.value for m in app.markdown)
    button=next(b for b in app.button if b.label=='Registrar cards deste tema')
    button.click().run();assert not app.exception
    app.number_input(key='ec_covered').set_value(20)
    confirm_action(app.button(key='FormSubmitter:ec_record-Salvar bloco de cards').click().run())
    assert not app.exception and len(s.history())==1 and s.history()[0]['covered']==20
    with s.repo._connection() as db:assert db.execute('SELECT COUNT(*) FROM study_events').fetchone()[0]==0


def test_empty_flashcards_explains_import(tmp_path,monkeypatch):
    monkeypatch.setenv('ERROR_CARDS_TEST_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.error_cards_ui import render_error_cards
render_error_cards(Repository(os.environ['ERROR_CARDS_TEST_ROOT']))
''',default_timeout=60).run()
    assert not app.exception and app.file_uploader


def test_large_deck_shows_daily_adjustment_with_cards_already_done():
    app=AppTest.from_string('''
from osler.error_cards_ui import _today
_today(None, {'active':True,'budget':40,'items':[],'done_today':10,'history':[],
    'ranked':[{'path':['Área','Deck grande'],'remaining':100,'oversized':True}]})
''').run()
    assert not app.exception
    row=app.dataframe[0].value.iloc[0]
    assert row['Limite mínimo hoje']==110
    assert row['Meta habitual mínima']==91
    assert any('decks prioritários' in item.value for item in app.caption)


def test_completed_theme_still_accepts_repetitions_without_zero_range_input(tmp_path,monkeypatch):
    s,day,html=setup(tmp_path);s.import_html(html,'cards.html',day,'pending',s.token())
    topic=stable_topic_id(['Área','A']);s.record(topic,day,100,0,None,'completed',s.token())
    monkeypatch.setenv('ERROR_CARDS_TEST_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.error_cards_ui import render_error_cards
render_error_cards(Repository(os.environ['ERROR_CARDS_TEST_ROOT']))
''',default_timeout=60).run()
    app.session_state['ec_tabs']='Temas';app.run()
    app.button(key='ec_manual_'+topic).click().run()
    assert not app.exception
    confirm_action(app.button(key='FormSubmitter:ec_record-Salvar bloco de cards').click().run())
    assert not app.exception
    v=s.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert v['remaining']==100 and v['done_today']==110
