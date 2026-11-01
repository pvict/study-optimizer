"""Interface local do Marco 1: biblioteca, importação, inspeção e auditoria."""
from .ui_help import explain
from .action_feedback import confirm_button,confirm_submit,notify_success
from .action_feedback import bind_actions,flush_toast

from dataclasses import asdict
import os
from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

from .exports import record_dicts, records_csv, report_json
from .extraction import ImportFailure
from .models import normalize_path
from .service import import_bytes
from .storage import Repository
from .matching_ui import render_crossing
from .assessment_ui import render_assessment
from .dashboard_ui import render_dashboard
from .planner_ui import render_planner
from .planning_ui import render_planning
from .longitudinal_ui import render_evolution
from .backups_ui import render_backups
from .workspace import active_data_dir, activate_data_dir
from .guided_ui import render_today, render_path
from .guide_settings_ui import render_guide_settings
from .reduction_ui import render_reduction
from .adaptive_ui import render_adaptive
from .study_style import apply_study_style


TYPE_LABELS = {"qbank": "Qbank", "flashcards": "Flashcards"}
SCOPE_LABELS = {"todos": "Todos os temas", "iniciados": "Somente iniciados", "desconhecido": "Escopo desconhecido"}


def _number(value) -> str:
    return f"{value:,}".replace(",", ".") if value is not None else "—"


def _date(value) -> str:
    return "/".join(reversed(value.split("-"))) if value else "Data ausente"


def _library(repo: Repository):
    st.subheader("Sua biblioteca de relatórios")
    explain("Cada arquivo é preservado. Relatórios equivalentes ficam identificados e não são somados.")
    entries = repo.list_reports()
    if not entries:
        st.info("Nenhum relatório importado. Abra a aba Importar relatórios para começar.")
        return
    rows = []
    for item in entries:
        report = repo.get_report(item["file_sha256"])
        rows.append({"Tipo": TYPE_LABELS[report.kind], "Escopo": SCOPE_LABELS[report.scope], "Data": _date(report.report_date),
                     "Arquivo": report.filename, "Páginas": report.page_count, "Linhas": len(report.records),
                     "Temas terminais": sum(r.is_leaf for r in report.records),
                     "Importação": "Equivalente a outro" if item["duplicate_of"] else "Conteúdo independente",
                     "Validação": "Há achados para revisão" if report.status == "revisar" else "Verificações documentais OK"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",column_config={"Arquivo":st.column_config.TextColumn(width="large"),"Validação":st.column_config.TextColumn(width="large")})
    with st.expander("Ver nomes completos e fontes"):
        for row in rows:
            st.text(row['Arquivo'])
            st.caption(f"{row['Tipo']} · {row['Escopo']} · {row['Data']} · {row['Validação']}")
    dates = {item["report_date"] for item in entries if item["report_date"]}
    if len(dates) < 2:
        st.info("Há uma única data de relatório. Importe outra data para comparar os relatórios ao longo do tempo.")
    st.caption("Originais preservados · alterações na Osler continuam manuais.")


def _import_tab(repo: Repository):
    st.subheader("Importar relatórios")
    st.write("Selecione os PDFs exportados manualmente. O tipo, o filtro e a data serão lidos do conteúdo.")
    uploads = st.file_uploader("Relatórios PDF", type=["pdf"], accept_multiple_files=True, key="pdf_uploads")
    if confirm_button("Importar arquivos selecionados", type="primary", disabled=not uploads,action_key='ui_72',details='Arquivos: '+', '.join(u.name for u in uploads or [])+'. Os originais serão preservados e os dados ficarão disponíveis no app.'):
        for upload in uploads or []:
            with st.spinner(f"Validando {upload.name}…"):
                try:
                    result = notify_success(import_bytes(repo, upload.getvalue(), upload.name),'Importação processada.')
                    if result.state == "ja_importado":
                        st.info(f"{upload.name}: arquivo já importado. Dados anteriores preservados.")
                    elif result.state == "equivalente":
                        st.info(f"{upload.name}: tabelas equivalentes a um relatório existente. Os dois originais foram preservados.")
                    else:
                        st.success(f"{upload.name}: {len(result.report.records)} linhas importadas.")
                    if result.report.status == "revisar":
                        st.warning("Há achados de validação. Consulte a aba Validação e auditoria antes de usar os dados.")
                except (ImportFailure, ValueError, OSError, sqlite3.Error) as exc:
                    st.error(f"{upload.name}: {exc}")
        st.button("Atualizar biblioteca", on_click=lambda: None)
    explain("Originais em data/originals · CSVs e JSONs em data/exports · Nenhuma conexão com a Osler.")


def _inspect(report, repo: Repository):
    st.subheader(f"{TYPE_LABELS[report.kind]} · {SCOPE_LABELS[report.scope]}")
    st.caption(f"Data do relatório: {_date(report.report_date)} · {report.filename}")
    columns = st.columns(4)
    labels = ["Questões no acervo" if report.kind == "qbank" else "Cartões no acervo",
              "Respondidas na capa" if report.kind == "qbank" else "Estudados na capa", "Temas terminais", "Páginas extraídas"]
    values = [report.summary.get("total"), report.summary.get("estudados"), sum(r.is_leaf for r in report.records), report.table_pages]
    for col, label, value in zip(columns, labels, values):
        col.metric(label, _number(value))
    explain("Totais de acervo e estudo vêm da capa deste relatório. A tabela pode ter um recorte menor. Pais e filhos não são somados.")
    if report.kind == "qbank":
        st.info("Acerto PDF: tentativa não identificada. Primeira tentativa, última tentativa e número de questões distintas permanecem ausentes.")
    else:
        st.info("% revisado indica cobertura de revisão, não acerto. Cartões ativos, pendentes e futuros permanecem ausentes.")
    frame = pd.DataFrame(record_dicts(report))
    c1, c2, c3 = st.columns([2, 1.3, 1.4])
    search = c1.text_input("Buscar na hierarquia", placeholder="Ex.: Cicatrização", key="topic_search")
    area = c2.selectbox("Grande área", ["Todas", *sorted(frame["area"].unique())], key="area_filter")
    view = c3.selectbox("Registros", ["Somente terminais", "Todos os níveis", "Somente estudados"], key="row_filter")
    filtered = frame
    if search:
        query = normalize_path([search])[0]
        filtered = filtered[filtered["hierarquia"].map(lambda x: query in normalize_path([x])[0])]
    if area != "Todas":
        filtered = filtered[filtered["area"] == area]
    if view == "Somente terminais":
        filtered = filtered[filtered["registro_terminal"]]
    elif view == "Somente estudados":
        filtered = filtered[filtered["questoes_respondidas" if report.kind == "qbank" else "cartoes_estudados"] > 0]
    labels = {"hierarquia": "Hierarquia", "questoes_disponiveis": "Questões", "questoes_respondidas": "Respondidas",
              "cartoes_total": "Cartões", "cartoes_estudados": "Estudados", "percentual_visto_texto": "% visto",
              "acerto_pdf_texto": "Acerto PDF", "percentual_revisado_texto": "% revisado", "pagina": "Página", "registro_terminal": "Terminal"}
    fields = ["hierarquia", *( ["questoes_disponiveis", "questoes_respondidas"] if report.kind == "qbank" else ["cartoes_total", "cartoes_estudados"]),
              "percentual_visto_texto", "acerto_pdf_texto" if report.kind == "qbank" else "percentual_revisado_texto", "pagina", "registro_terminal"]
    st.caption(f"{len(filtered)} registros exibidos · percentuais originais, incluindo limites como <1%")
    st.dataframe(filtered[fields].rename(columns=labels), key="records_table", hide_index=True, width="stretch", height=460)
    buttons = st.columns(3)
    buttons[0].download_button("Baixar CSV completo", records_csv(report), f"{report.kind}_{report.scope}_{report.report_date or 'sem_data'}.csv", "text/csv")
    buttons[1].download_button("Baixar JSON auditável", report_json(report), f"{report.kind}_{report.scope}.json", "application/json")
    original = repo.original_path(report.file_sha256)
    if original.exists():
        buttons[2].download_button("Baixar PDF original", original.read_bytes(), report.filename, "application/pdf")
    with st.expander("Conferir totais, metadados e rastreabilidade"):
        st.json({"data_relatorio": report.report_date, "metadados_pdf": report.metadata, "sha256_original": report.file_sha256,
                 "sha256_conteudo": report.content_sha256, "resumo": report.summary})


def _validation(report, repo: Repository):
    st.subheader("Validação e auditoria")
    if report:
        errors = sum(f.severity == "erro" for f in report.findings)
        warnings = sum(f.severity == "aviso" for f in report.findings)
        st.write(f"Relatório selecionado: **{errors} erros · {warnings} avisos**")
        lookup = {row.topic_id: " → ".join(row.path) for row in report.records}
        if report.findings:
            st.dataframe(pd.DataFrame([{"Nível": f.severity, "Código": f.code, "Descrição": f.message,
                                        "Página": f.page, "Tema": lookup.get(f.topic_id, "")} for f in report.findings]),
                         hide_index=True, width="stretch")
        st.info("Achados informativos explicam limites dos dados. Avisos e erros pedem revisão. A validação documental não comprova domínio de um tema.")
    else:
        st.info("Importe um relatório para visualizar os achados.")
    with st.expander("Histórico local de importações"):
        events = repo.audit_events()
        if events:
            st.dataframe(pd.DataFrame(events), hide_index=True, width="stretch")
        else:
            st.caption("Nenhuma importação registrada.")


def run():
    st.set_page_config(page_title="Osler · Meu estudo", layout="wide")
    apply_study_style()
    project_root = Path(__file__).resolve().parents[1]
    try:
        root = Path(st.session_state.get("active_data_dir") or active_data_dir(project_root))
    except ValueError as exc:
        st.error(str(exc))
        return
    try:
        repo = Repository(root)
    except (ValueError, sqlite3.Error, OSError) as exc:
        st.error(f"Não foi possível abrir a pasta de dados: {exc}. A pasta anterior não foi substituída.")
        preserved = project_root/"data"
        if root.resolve() != preserved.resolve() and (preserved/"osler.sqlite3").is_file():
            if confirm_button("Abrir pasta original preservada",action_key='ui_175'):
                try:
                    activate_data_dir(project_root, preserved)
                    st.session_state.clear()
                    st.session_state["active_data_dir"] = str(preserved)
                    notify_success(None,'Pasta original aberta; dados preservados.')
                    st.rerun()
                except (ValueError, OSError) as recovery_error:
                    st.error(str(recovery_error))
        return
    bind_actions(repo)
    from .study_navigation_ui import render_navigation
    view=render_navigation()
    if view == "Plano de questões":
        render_adaptive(repo)
        flush_toast()
        return
    if view == "Diminuir revisões":
        from .error_cards_ui import render_flashcards
        render_flashcards(repo)
        flush_toast()
        return
    _advanced_tools(repo, project_root)
    flush_toast()


def _advanced_tools(repo, project_root):
    st.title("Arquivos e ferramentas")
    st.caption("Seus relatórios, importações e cópias de segurança.")
    all_entries = repo.list_reports()
    entries = repo.list_reports(include_duplicates=False)
    def open_backup(): st.session_state['advanced_view']='Backup e restauração'
    def open_library(): st.session_state['advanced_view']='Dados e classificação'
    with st.container(key='bento-files-navigation'):
        left,right=st.columns(2)
        left.button('Biblioteca e importação',key='files_library',on_click=open_library,width='stretch',icon=':material/folder_open:')
        right.button('Backup e restauração',key='open_backup',on_click=open_backup,width='stretch',icon=':material/backup:')
    content=st.container()
    advanced_controls=st.expander("Avançado · selecionar relatório ou ferramenta")
    show_equivalent = advanced_controls.checkbox("Mostrar relatórios equivalentes", value=False)
    options = all_entries if show_equivalent else entries
    report = None
    if options:
        by_id = {item["file_sha256"]: item for item in options}
        selected = advanced_controls.selectbox("Relatório para inspecionar", list(by_id),
                                         format_func=lambda key: f"{TYPE_LABELS[by_id[key]['kind']]} · {SCOPE_LABELS[by_id[key]['scope']]} · {_date(by_id[key]['report_date'])}", key="inspect_report_id")
        report = repo.get_report(selected)
        if by_id[selected]["duplicate_of"]:
            st.info("Conteúdo equivalente a outro relatório; original preservado.")
    legacy={'Painel','Planejador de Suspensões','Simulação e rotina','Roteiro simples','Meu caminho','Preferências do roteiro','Reduções anteriores'}
    view = advanced_controls.selectbox("Abrir ferramenta", ["Dados e classificação", "Painel", "Planejador de Suspensões", "Simulação e rotina", "Evolução", "Backup e restauração", "Roteiro simples", "Meu caminho", "Preferências do roteiro","Reduções anteriores"],format_func=lambda v:v+' (legado)' if v in legacy else v,key="advanced_view")
    with content:
        _file_tool(repo,project_root,report,view,legacy)


def _file_tool(repo,project_root,report,view,legacy):
    if view in legacy: st.caption('Recurso legado · preservado para consulta e continuidade dos registros anteriores.')
    if view=='Reduções anteriores':
        from .practical_reduction_ui import render_legacy_details
        from .reduction_ui import _open_tool
        render_legacy_details(repo,_open_tool)
        return
    if view == "Roteiro simples":
        render_today(repo)
        return
    if view == "Meu caminho":
        render_path(repo)
        return
    if view == "Preferências do roteiro":
        render_guide_settings(repo)
        return
    if view == "Painel":
        render_dashboard(repo)
    elif view == "Planejador de Suspensões":
        render_planner(repo)
    elif view == "Simulação e rotina":
        render_planning(repo)
    elif view == "Evolução":
        render_evolution(repo)
    elif view == "Backup e restauração":
        render_backups(repo, project_root)
    if view == "Dados e classificação":
        _data_tabs(repo, report)


def _data_tabs(repo, report):
    library, upload = st.tabs(["Biblioteca", "Importar relatórios"])
    with library:
        with st.container(key='bento-files-library'):
            _library(repo)
    with upload:
        with st.container(key='bento-files-import'):
            _import_tab(repo)
    with st.expander('Avançado · inspecionar e conferir dados'):
        inspect, audit, crossing, assessment = st.tabs(["Inspecionar dados", "Validação e auditoria", "Cruzamento", "Classificação"])
    with inspect:
        if report:
            _inspect(report, repo)
        else:
            st.info("Importe um relatório para inspecionar a tabela extraída.")
    with audit:
        _validation(report, repo)
    with crossing:
        render_crossing(repo)
    with assessment:
        st.caption('Classificação A–D · legado')
        render_assessment(repo)
