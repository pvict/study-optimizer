from conftest import open_view
from streamlit.testing.v1 import AppTest

from osler.guide_service import GuideService
from osler.planning import Measurement
from osler.planning_service import PlanningService
from osler.reduction import reduction_overview
from test_assessments import setup_assessment
from test_classification import known


def reduction_app(project_root):
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    return open_view(app,main='Diminuir revisões')


def legacy_reduction_app(project_root):
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=30).run()
    open_view(app,main='Ferramentas')
    return app.selectbox(key='advanced_view').set_value('Reduções anteriores').run()


def test_reduction_separates_workload_gap_from_candidate_cards(tmp_path, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(), 0)
    planning = PlanningService(repo)
    planning.save_measurement(Measurement('revisoes_periodo', 31149, '2026-10-14', 'Usuário', 90))
    planning.save_measurement(Measurement('revisoes_high_yield', 26789, '2026-10-14', 'Outro filtro', 90))
    result = reduction_overview(repo, '2026-10-15', 150)
    assert result['workload']['count'] == 31149
    assert result['comparison']['average'] == 31149/90
    assert result['comparison']['needed_reviews'] == 17649
    assert result['comparison']['daily_limit'] == 150
    assert result['measured_reduction'] is None
    assert len(result['candidates']) == 1
    assert result['candidates'][0]['cards'] == 146
    assert result['candidates'][0]['category'] == 'B'
    assert result['applied_items'] == 0
    assert result['candidates'][0]['status'] is None


def test_incidence_and_pdf_alone_do_not_create_suspension_candidates(tmp_path, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    GuideService(repo).import_incidence('Tema;Questões\nOutro;1', 'questoes', ['A'], '2026-10-15')
    result = reduction_overview(repo, '2026-10-15')
    assert result['candidates'] == []
    assert result['workload'] is None
    assert result['comparison'] is None


def test_latest_eligible_measurement_keeps_its_own_horizon_and_date(tmp_path, sample_pdf):
    repo, *_ = setup_assessment(tmp_path, sample_pdf)
    planning = PlanningService(repo)
    planning.save_measurement(Measurement('revisoes_periodo', 500, '2026-10-14', 'Consulta antiga', 5))
    planning.save_measurement(Measurement('revisoes_periodo', 1000, '2026-10-15', 'Consulta atual', 10))
    planning.save_measurement(Measurement('revisoes_periodo', 9000, '2026-10-16', 'Consulta futura', 30))
    planning.save_measurement(Measurement('cartoes_pendentes', 2002, '2026-10-15', 'Outra tela'))
    result = reduction_overview(repo, '2026-10-15', 120)
    assert result['workload']['count'] == 1000
    assert result['workload']['horizon_days'] == 10
    assert result['comparison']['average'] == 100
    assert result['comparison']['needed_reviews'] == 0


def test_applied_item_does_not_count_as_measured_review_savings(tmp_path, sample_pdf):
    from test_planner import setup_plan, move
    repo, _, _, _, planner, batch_id = setup_plan(tmp_path, sample_pdf)
    for status in ['aguardando_validacao', 'aprovado_usuario', 'aplicado_manualmente']:
        move(planner, planner.get_batch(batch_id)['items'][0], status, confirmed=True)
    result = reduction_overview(repo, '2026-10-15')
    assert result['applied_items'] == 1
    assert result['measured_reduction'] is None
    assert result['candidates'][0]['status'] == 'aplicado_manualmente'
    assert result['candidates'][0]['batch_id'] == batch_id


def test_main_screen_exposes_reduction_without_per_topic_forms(tmp_path, monkeypatch, project_root, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(), 0)
    monkeypatch.setenv('OSLER_DATA_DIR', str(tmp_path))
    app = reduction_app(project_root)
    app.radio(key='ec_mode').set_value('Reduzir outras revisões').run()
    assert not app.exception
    assert app.session_state['main_view'] == 'Diminuir revisões'
    assert len(app.text_input) == 0
    assert len(app.number_input) == 0
    assert len(app.checkbox) == 0
    assert any('Cicatrização e Avaliação de Feridas' in str(frame.value.values) for frame in app.dataframe)
    assert not any(b.key and b.key.startswith('reduce_') for b in app.button)
    assert any('não são revisões por dia' in text.value for text in app.caption)
    assert not any(b.label == 'Já fiz essa mudança na Osler' for b in app.button)


def test_reduction_shortcut_keeps_the_existing_batch(tmp_path, monkeypatch, project_root, sample_pdf):
    from test_planner import setup_plan
    repo, _, _, _, planner, batch_id = setup_plan(tmp_path, sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR', str(tmp_path))
    app = legacy_reduction_app(project_root)
    next(b for b in app.button if b.label == 'Acompanhar esta redução').click().run()
    assert not app.exception
    assert app.session_state['main_view'] == 'Ferramentas'
    assert app.selectbox(key='planner_batch_id').value == batch_id
    assert len(planner.list_batches()) == 1
    assert planner.get_batch(batch_id)['items'][0]['status'] == 'sugerido'


def test_shortcut_selects_clicked_topic_inside_a_multiple_item_batch(tmp_path, monkeypatch, project_root, sample_pdf):
    from osler.planner_service import PlannerService
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    other = next(r for r in matching.rows if r.qbank and r.qbank.name == 'Outro')
    for source in [other, row]:
        assessment.save_observation(matching, source.row_id, known(), 0)
    planner = PlannerService(repo)
    bid = planner.create_batch(matching, [other.row_id, row.row_id], 'Dois assuntos', 'Teste', '2026-10-14')
    wanted = next(i for i in planner.get_batch(bid)['items'] if i['row_id'] == row.row_id)
    monkeypatch.setenv('OSLER_DATA_DIR', str(tmp_path))
    app = legacy_reduction_app(project_root)
    app.button(key=f'reduce_{row.row_id}').click().run()
    assert not app.exception
    assert app.selectbox(key=f'planner_item_{bid}').value == wanted['id']


def test_reduction_respects_the_same_policy_as_the_planner(tmp_path, monkeypatch, project_root, sample_pdf):
    repo, assessment, matching, row = setup_assessment(tmp_path, sample_pdf)
    assessment.save_observation(matching, row.row_id, known(), 0)
    monkeypatch.setenv('OSLER_DATA_DIR', str(tmp_path))
    app = legacy_reduction_app(project_root)
    app.session_state['assessment_config'] = {'min_questions': 100}
    app.run()
    assert not app.exception
    assert not any(b.label == 'Acompanhar esta redução' for b in app.button)
    assert not any('Cicatrização e Avaliação de Feridas' in text.value for text in app.text)
