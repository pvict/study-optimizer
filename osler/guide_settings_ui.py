"""Poucas escolhas globais e importação de uma tabela inteira."""
import json
import sqlite3

import streamlit as st

from .guide import GuideSettings
from .guide_service import GuideService
from .guided_ui import time_label
from .incidence import parse_html_table, prepare_incidence
from .planner_service import today_local


def render_guide_settings(repo,*,incidence_only=False):
    service = GuideService(repo)
    record = service.settings()
    settings = GuideSettings(**record["settings"])
    if incidence_only:
        st.subheader('Instituições e incidências')
        st.caption('Escolha o conjunto de provas e confira as fontes usadas para priorizar os temas.')
    else:
        st.title("Ajustar meu plano")
        st.write("Estas escolhas valem para o plano inteiro. Você não precisa configurar cada assunto.")
    if "guide_settings_notice" in st.session_state:
        st.success(st.session_state.pop("guide_settings_notice"))
    times = sorted({15, 30, 45, 60, 90, 120, 180, 240, 300, 360, settings.normal_minutes, settings.shift_minutes})
    with st.form("simple_settings"):
        institutions = st.text_area("Quais provas ou instituições você quer priorizar?", value="\n".join(settings.institutions), placeholder="Uma por linha. Pode deixar para depois.", key="guide_institutions")
        normal,shift=settings.normal_minutes,settings.shift_minutes
        if not incidence_only:
            normal = st.select_slider("Tempo de estudo em um dia normal", times, value=settings.normal_minutes, format_func=time_label)
            shift = st.select_slider("Tempo em um plantão ou dia cansativo", times, value=settings.shift_minutes, format_func=time_label)
            st.caption("Meta inicial: novembro de 2027. Os tempos sugeridos podem ser alterados quando sua rotina mudar.")
        save = st.form_submit_button("Salvar instituições" if incidence_only else "Salvar meu plano", type="primary")
    if save:
        try:
            names = list(dict.fromkeys(i.strip() for i in institutions.splitlines() if i.strip()))
            service.save_settings(GuideSettings(names, normal, shift, settings.start_date, settings.target_date), record["id"])
            st.session_state["guide_settings_notice"] = "Instituições salvas. O plano usa as tabelas compatíveis com esse conjunto." if incidence_only else "Plano salvo. O roteiro de hoje já usa sua disponibilidade."
            st.rerun()
        except (ValueError, sqlite3.Error) as exc:
            st.error(str(exc))
    st.divider()
    st.subheader("O que mais cai nas suas provas")
    datasets = service.datasets()
    if datasets:
        applicable = prepare_incidence(datasets, settings.institutions, today_local().isoformat())
        current = applicable[-1] if applicable else datasets[-1]
        if applicable:
            st.success(f"Sua tabela já está carregada: {len(current['rows'])} temas, {sum(r['path'] is not None for r in current['rows'])} reconhecidos nos PDFs.")
        else:
            st.warning("A tabela está guardada, mas não está sendo usada para as provas deste plano: os nomes do conjunto são diferentes. Envie a tabela indicando as instituições selecionadas naquela consulta. Se não souber os nomes, deixe as provas do plano em branco para usar o conjunto original.")
        st.caption("Os demais nomes foram preservados para ajuste. Você não precisa completá-los para começar.")
        with st.expander("Ver de onde vieram os dados"):
            st.text("Instituições/recorte: " + ", ".join(current["institutions"]))
            st.caption(f"Tabela recebida em {current['observed_date']}. Anos e filtros não presentes no arquivo não são presumidos.")
    else:
        st.write("Você pode usar o guia agora. Quando trouxer a tabela das instituições, ela ajudará a escolher os próximos assuntos.")
    with st.expander("Acrescentar outra tabela de incidência"):
        st.write("Envie o HTML copiado manualmente da tabela. Também aceito CSV ou uma tabela de duas colunas colada abaixo. O arquivo é lido só nesta máquina.")
        uploaded = st.file_uploader("Tabela HTML, CSV ou TSV", type=["html", "htm", "csv", "tsv"], key="incidence_upload")
        pasted = st.text_area("Ou cole tema e quantidade de questões", placeholder="Tema;Questões\nNome do assunto;12", key="incidence_paste")
        text, table = pasted, None
        if uploaded:
            try:
                text = uploaded.getvalue().decode("utf-8-sig")
            except UnicodeDecodeError:
                st.error("Salve o arquivo em UTF-8 e envie novamente.")
                text = ""
        value_column = None
        if text.lstrip().startswith("<"):
            try:
                table = parse_html_table(text)
                preferred = next((i for i, h in enumerate(table["headers"]) if i and "institui" in h.lower() and "quest" in h.lower()), 1)
                st.caption(f"O arquivo contém {len(table['rows'])} linhas. Isso é o que foi recebido; não significa que toda a plataforma foi exportada.")
                value_column = st.selectbox("Coluna usada para priorizar", list(range(1, len(table["headers"]))), index=preferred-1, format_func=lambda i: table["headers"][i])
            except ValueError as exc:
                st.error(str(exc))
                text = ""
        context = st.text_input("Instituições selecionadas nessa consulta", value="; ".join(settings.institutions), placeholder="Se ainda não souber os nomes, escreva: Instituições selecionadas na Osler")
        unit = st.selectbox("O valor da coluna é", ["questoes", "percentual"], format_func={"questoes": "Quantidade de questões", "percentual": "Percentual"}.get)
        if st.button("Usar esta tabela no meu plano", disabled=not text.strip() or not context.strip()):
            try:
                service.import_incidence(text, unit, [p.strip() for p in context.split(";") if p.strip()], today_local().isoformat(), value_column)
                st.session_state["guide_settings_notice"] = "Tabela inteira processada. O guia já considera o conteúdo reconhecido."
                st.rerun()
            except (ValueError, OSError, sqlite3.Error) as exc:
                st.error(str(exc))
