"""Atualizações acumuladas não podem fabricar sessões ou apagar outros temas."""
from html import escape
import pytest

from osler.planner_import import PlannerImportService, parse_planner_html
from osler.adaptive_service import AdaptiveService
from osler.incidence import prepare_incidence
from osler.planner_snapshot import load_planner_contexts
from test_assessments import setup_assessment


def html_row(path, n=34, total=290, rate='73.5%', age='5d', pending='1', incidence='36 questões'):
    return '<tr><td><span class="ThemeTitle-test">'+escape(path[-1])+'</span><span class="ThemePath-test">'+escape(' » '.join(path[:-1]))+'</span></td>'+''.join('<td>'+escape(str(v))+'</td>' for v in [pending,rate,age,f'{n} de {total} feitas',incidence,''])+'</tr>'


def table(*rows):
    headers=['Tema','Revisões Pendentes','Acertos c/ Segurança','Dias sem Contato','Incidência Geral','Incidência Instituições','Ações']
    return ('<table><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table>').encode()


def configured(tmp_path, sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=PlannerImportService(repo)
    report=service.guide._report('qbank','2026-10-15')
    paths=[r.path for r in report.records if r.is_leaf]
    return service, paths


def test_parser_reads_real_theme_classes_zeroes_and_missing_values():
    rows=parse_planner_html(table(html_row(['Área','Grupo','A']),html_row(['Área','B'],n=0,rate='—',age='—',pending='Em dia',incidence='0 questões')))
    assert rows[0]['path']==['Área','Grupo','A']
    assert rows[0]['questions_done_snapshot']==34 and rows[0]['questions_available_snapshot']==290
    assert rows[0]['confident_accuracy_pct']==73.5 and rows[0]['days_since_contact']==5
    assert rows[1]['confident_accuracy_pct'] is None and rows[1]['days_since_contact'] is None
    assert rows[1]['pending_reviews']==0 and rows[1]['institution_incidence_questions']==0


@pytest.mark.parametrize('values',[{'n':300,'total':290},{'rate':'101%'},{'age':'talvez 5 dias'},{'n':0,'rate':'90%'}])
def test_invalid_metrics_are_not_imported(values):
    with pytest.raises(ValueError):parse_planner_html(table(html_row(['Área','A'],**values)))


def test_duplicate_path_and_wrong_table_are_rejected():
    with pytest.raises(ValueError,match='repetido'):parse_planner_html(table(html_row(['Área','A']),html_row(['Área','A'])))
    with pytest.raises(ValueError):parse_planner_html(b'<table><tr><th>Tema</th><th>Valor</th></tr><tr><td>A</td><td>2</td></tr></table>')


def test_preview_is_read_only_and_apply_updates_context_without_attempts_or_incidence(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf)
    old=service.guide.import_incidence('Tema;Valor\n'+ ' → '.join(paths[0])+';99','questoes',['Teste'],'2026-10-15')
    data=table(html_row(paths[0]));before=service.guide.datasets()
    files=sorted(str(p) for p in service.repo.exports.rglob('*'))
    preview=service.preview(data,'planner.html','2026-10-15')
    assert service.guide.datasets()==before and files==sorted(str(p) for p in service.repo.exports.rglob('*'))
    assert preview['matched_rows']==1 and preview['comparison'][0]['Contato novo']=='2026-10-10'
    saved=service.apply(preview,data)
    assert service.apply(preview,data)==saved
    datasets=service.guide.datasets()
    assert len(datasets)==len(before)+1
    assert prepare_incidence(datasets,['Teste'],'2026-10-15')[0]['id']==old
    report=service.guide._report('qbank','2026-10-15')
    contexts,warnings=load_planner_contexts(service.repo,datasets,report.file_sha256,'2026-10-15')
    row=next(iter(contexts.values()))
    assert not warnings and row['unique_questions']==34 and row['confident_accuracy_pct']==73.5
    assert row['last_contact']=='2026-10-10'
    assert not AdaptiveService(service.repo).store.active('2026-10-15')


def test_partial_file_preserves_other_topics_and_updates_only_latest_paths(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf)
    first=table(*(html_row(p) for p in paths[:2]))
    service.apply(service.preview(first,'one.html','2026-10-14'),first)
    partial=table(html_row(paths[0],n=40,age='Hoje'))
    preview=service.preview(partial,'two.html','2026-10-15')
    assert preview['preserved_topics']==1
    service.apply(preview,partial)
    report=service.guide._report('qbank','2026-10-15')
    contexts,_=load_planner_contexts(service.repo,service.guide.datasets(),report.file_sha256,'2026-10-15')
    assert sorted(r['unique_questions'] for r in contexts.values())==[34,40]


def test_apply_rejects_changed_source_or_stale_preview(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf);data=table(html_row(paths[0]))
    preview=service.preview(data,'one.html','2026-10-15')
    with pytest.raises(ValueError):service.apply(preview,table(html_row(paths[0],n=40)))
    adaptive=AdaptiveService(service.repo)
    adaptive.configure_day('2026-10-15',40,'descanso',0)
    with pytest.raises(ValueError,match='mudou|atualiz'):service.apply(preview,data)
    assert service.guide.datasets()==[]


def test_incidence_is_opt_in_and_requires_explicit_institutions(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf);data=table(html_row(paths[0]))
    with pytest.raises(ValueError):service.preview(data,'one.html','2026-10-15',include_incidence=True)
    preview=service.preview(data,'one.html','2026-10-15',include_incidence=True,institutions=['Teste'])
    service.apply(preview,data)
    prepared=prepare_incidence(service.guide.datasets(),['Teste'],'2026-10-15')
    assert prepared[0]['rows'][0]['value']==36


def test_partial_progress_cannot_silently_replace_a_complete_incidence_dataset(tmp_path,sample_pdf):
    service,paths=configured(tmp_path,sample_pdf)
    first=table(*(html_row(path,incidence='10 questões') for path in paths[:2]))
    service.apply(service.preview(first,'one.html','2026-10-14',include_incidence=True,institutions=['Teste']),first)
    partial=table(html_row(paths[0],incidence='20 questões'))
    with pytest.raises(ValueError,match='parcial'):
        service.preview(partial,'two.html','2026-10-15',include_incidence=True,institutions=['Teste'])
    preview=service.preview(partial,'two.html','2026-10-15')
    assert preview['preserved_topics']==1
