from streamlit.testing.v1 import AppTest

from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry, AdaptiveProfile
from datetime import date


def start(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    return repo,AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()


def test_today_uses_question_goal_without_time_widget_and_persists_extra(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    assert not app.exception
    assert len(app.radio(key='main_view').options)==3
    assert {'Hoje','Calendário','Evolução','Temas','Registrar','Ajustes'}<=set(app.radio(key='adaptive_view').options)
    assert not any('tempo total' in s.label.lower() for s in app.select_slider)
    assert any('0 de 60 questões registradas' in h.value for h in app.get('html'))
    app.number_input(key='day_questions').set_value(40)
    next(b for b in app.button if b.label=='Atualizar meta de hoje').click().run()
    assert not app.exception
    assert AdaptiveService(repo).overview('2026-10-15')['plan']['target_questions']==40
    selected=max(AdaptiveService(repo).overview('2026-10-15')['states'],key=lambda t:t['total'])
    app.text_input(key='extra_search').set_value(selected['path'][-1]).run()
    field=next(n for n in app.number_input if n.key.startswith('extra_count_'))
    field.set_value(5).run()
    next(b for b in app.button if b.label=='Adicionar ao meu dia').click().run()
    assert not app.exception
    assert AdaptiveService(repo).overview('2026-10-15')['plan']['target_questions']==45
    assert any('Adicionado por você' in c.value for c in app.caption)


def test_topic_table_has_real_period_controls_and_export(tmp_path,monkeypatch,project_root,sample_pdf):
    _,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    app.radio(key='adaptive_view').set_value('Temas e estatísticas').run()
    assert not app.exception
    assert app.radio(key='statistics_period').options==['Dia','Semana','Mês','Todo o período']
    for period in ['Semana','Mês','Todo o período']:
        app.radio(key='statistics_period').set_value(period).run()
        assert not app.exception
        frame=app.dataframe[0].value
        assert 'Questões' in frame.columns and 'Acerto (%)' in frame.columns
    assert any(b.label=='Baixar tabela filtrada' for b in app.get('download_button'))


def test_backdated_result_before_first_pdf_is_visible_in_period_table(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    service=AdaptiveService(repo)
    t=service.overview('2026-10-15')['states'][0]
    service.save_entry(StudyEntry(t['path'],'2026-10-01',10,8),'historical')
    app.radio(key='adaptive_view').set_value('Temas e estatísticas').run()
    app.date_input(key='statistics_date').set_value(date(2026,10,1)).run()
    assert not app.exception
    assert any(m.label=='Questões no período' and m.value=='10' for m in app.metric)


def test_returning_after_profile_change_refreshes_day_form_default(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    app.radio(key='adaptive_view').set_value('Ajustes').run()
    AdaptiveService(repo).store.save_profile(AdaptiveProfile(max_questions=80),0)
    app.radio(key='adaptive_view').set_value('Meu dia').run()
    assert not app.exception
    assert app.number_input(key='day_questions').value==80


def test_table_filter_resets_row_selection_before_actions_change_topic(tmp_path,monkeypatch,project_root,sample_pdf):
    _,app=start(tmp_path,monkeypatch,project_root,sample_pdf)
    app.radio(key='adaptive_view').set_value('Temas e estatísticas').run()
    table_id=app.dataframe[0].proto.id.split('-',2)[2]
    app.session_state[table_id]={'selection':{'rows':[0],'columns':[],'cells':[]}}
    app.run()
    assert any(b.label=='Registrar resultado deste tema' for b in app.button)
    app.text_input(key='statistics_search').set_value('Feridas').run()
    assert not app.exception
    assert not any(b.label=='Registrar resultado deste tema' for b in app.button)
