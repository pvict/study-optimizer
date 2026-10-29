from conftest import open_view
"""Fluxos novos de apresentação, sem substituir testes dos serviços existentes."""
from streamlit.testing.v1 import AppTest
from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService


def open_app(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    return repo,AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()


def test_today_puts_action_before_settings_and_labels_current_screen(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=open_app(tmp_path,monkeypatch,project_root,sample_pdf)
    assert not app.exception
    assert app.title[0].value=='Olá'
    assert any(e.label=='Adiantar revisões' and not e.proto.expanded for e in app.expander)
    assert any(e.label=='Ajustar meu dia' for e in app.expander)
    assert any(b.key and b.key.startswith('study_') for b in app.button)
    actions=list(app.button)
    assert next(i for i,b in enumerate(actions) if b.key and b.key.startswith('study_'))<next(i for i,b in enumerate(actions) if b.label=='Atualizar meta de hoje')
    assert not AdaptiveService(repo).store.active('2026-10-15')


def test_status_filters_and_list_actions_use_the_correct_specific_topic(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=open_app(tmp_path,monkeypatch,project_root,sample_pdf)
    open_view(app,adaptive='Temas e estatísticas')
    app.button(key='focus_alerta').click().run()
    assert not app.exception and app.selectbox(key='statistics_focus').value=='Em alerta'
    app.selectbox(key='statistics_focus').set_value('Todos os temas').run()
    app.radio(key='statistics_layout').set_value('Lista').run()
    assert not app.exception
    first=next(b for b in app.button if b.key and b.key.startswith('list_record_'))
    selected=first.key.removeprefix('list_record_')
    first.click().run()
    assert not app.exception and app.session_state['adaptive_view']=='Registrar resultados'
    assert app.session_state['adaptive_topic']==selected
    assert not AdaptiveService(repo).store.active('2026-10-15')


def test_calendar_agenda_and_grid_keep_the_same_day_selection(tmp_path,monkeypatch,project_root,sample_pdf):
    _,app=open_app(tmp_path,monkeypatch,project_root,sample_pdf)
    open_view(app,adaptive='Calendário')
    assert not app.exception and app.radio(key='calendar_mode').value=='Semana'
    target='2026-10-16'
    app.button(key='calendar_cell_'+target).click().run()
    assert not app.exception and app.session_state['calendar_selected']==target
    for mode in ['Semana','Mês','Agenda']:
        app.radio(key='calendar_mode').set_value(mode).run()
        assert not app.exception and app.session_state['calendar_selected']==target
    from datetime import date
    app.date_input(key='calendar_reference').set_value(date(2026,11,4)).run()
    assert not app.exception and app.session_state['calendar_selected']=='2026-11-04'


def test_long_theme_and_user_markup_are_preserved_as_text():
    from html.parser import HTMLParser
    title='<script>alert(1)</script> & Tema muito longo '+('específico '*25)
    app=AppTest.from_string('from osler.study_components import block_heading\nblock_heading('+repr({'path':['Área',title],'questions':20})+')').run()
    assert not app.exception
    class Content(HTMLParser):
        def __init__(self):
            super().__init__(); self.tags=[]; self.text=[]
        def handle_starttag(self,tag,attrs): self.tags.append(tag)
        def handle_data(self,data): self.text.append(data)
    parser=Content()
    parser.feed(app.get('html')[0].value)
    assert 'script' not in parser.tags and title in ''.join(parser.text)


def test_archived_topic_with_contact_and_no_scheduled_review_is_not_mislabeled():
    from osler.study_statistics import topic_statistics
    from osler.confidence_presentation import confidence_presentation
    from test_adaptive_planning import session
    events=[session('Tema arquivado',day='2026-10-15')]
    rows=topic_statistics([],events,'Todo o período','2026-10-20')
    assert rows[0]['Último contato']=='2026-10-15' and rows[0]['Próxima revisão'] is None
    rows=confidence_presentation(rows,events,'Todo o período','2026-10-20')
    app=AppTest.from_string('from osler.study_tables_ui import _topic_list\n_topic_list('+repr(rows)+',"history",lambda *args:None)').run()
    assert not app.exception
    assert any(c.value=='Próxima revisão: Não programada' for c in app.caption)


def test_initial_topic_card_shows_queue_action_instead_of_false_review_date():
    from osler.study_statistics import topic_statistics
    from osler.confidence_presentation import confidence_presentation
    from osler.adaptive_planning import topic_states
    from osler.study_models import AdaptiveProfile
    from test_initial_review_policy import imported
    state=topic_states([imported()],[],[],{},'2026-10-15',AdaptiveProfile())[0]
    rows=topic_statistics([state],[],'Todo o período','2026-10-15')
    rows=confidence_presentation(rows,[],'Todo o período','2026-10-15',include_snapshot=True)
    app=AppTest.from_string('from osler.study_tables_ui import _topic_list\n_topic_list('+repr(rows)+',"initial",lambda *args:None,True)').run()
    assert not app.exception
    assert any(c.value=='Próxima ação: Priorizar agora' for c in app.caption)
    assert not any(c.value.startswith('Próxima revisão:') for c in app.caption)
