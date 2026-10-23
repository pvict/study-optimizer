"""Visão geral local com a origem de cada indicador visível."""

import pandas as pd
import streamlit as st

from .dashboard import build_dashboard
from .matching_ui import _choose
from .planner_service import today_local


def render_dashboard(repo):
    st.subheader("Seu estudo em perspectiva")
    entries = [r for r in repo.list_reports(False) if r["complete"]]
    q, f = [r for r in entries if r["kind"] == "qbank"], [r for r in entries if r["kind"] == "flashcards"]
    if not q or not f:
        st.info("Importe relatórios de Qbank e Flashcards para abrir o painel. Use Dados e classificação abaixo.")
        return
    c1, c2 = st.columns(2)
    with c1:
        q_id = _choose(q, "Qbank do painel", "dashboard_q_id")
    with c2:
        f_id = _choose(f, "Flashcards do painel", "dashboard_f_id")
    day = today_local().isoformat()
    try:
        data = build_dashboard(repo, q_id, f_id, day)
    except ValueError as exc:
        st.error(str(exc))
        return
    q_data, f_data = data["qbank"], data["flashcards"]
    def number(value):
        return f"{value:,}".replace(",", ".") if value is not None else "Não informado"
    for col, label, value, detail in zip(st.columns(4), ["Questões respondidas", "Flashcards estudados", "Candidatos A/B", "Aplicados manualmente"],
                                       [q_data["studied"], f_data["studied"], data["classification"]["A"]+data["classification"]["B"], data["planner"]["aplicado_manualmente"]],
                                       ["Capa do Qbank selecionado", "Capa de flashcards selecionada", "Sujeitos à validação pessoal", "Somente confirmações registradas pelo usuário"]):
        col.metric(label, number(value))
        col.caption(detail)
    st.caption(f"Qbank: {q_data['report_date']} · {q_data['scope']} | Flashcards: {f_data['report_date']} · {f_data['scope']}. Totais das fontes, sem soma de níveis.")
    st.info("Agenda detalhada não disponível nos PDFs: revisões pendentes e carga futura global não foram inferidas. Use a simulação local quando informar esses dados.")
    if data["manual_measurements"]:
        with st.expander("Agenda informada manualmente · fontes separadas"):
            labels = {"cartoes_pendentes": "Cartões pendentes", "revisoes_periodo": "Revisões do período", "revisoes_high_yield": "High Yield · teste separado"}
            for column, (kind, measurement) in zip(st.columns(len(data["manual_measurements"])), data["manual_measurements"].items()):
                column.metric(labels[kind], ("≈ " if measurement["approximate"] else "")+number(measurement["count"]))
                column.caption(f"Informado em {measurement['observed_date']}" + (f" · {measurement['horizon_days']} dias" if measurement["horizon_days"] else " · cartões, não revisões"))
                column.caption(measurement["source"])
            st.caption("Cortes e denominadores podem diferir. Os números não foram somados; consulte notas e cenários em Simulação e rotina.")
    st.write("**Desempenho e cobertura por área**")
    frame = pd.DataFrame(data["areas"])
    labels = {"area": "Área", "qbank_studied": "Respondidas PDF", "qbank_total": "Questões disponíveis",
              "qbank_metric": "Acerto PDF · tentativa desconhecida", "flashcards_studied": "Cartões estudados", "flashcards_total": "Cartões disponíveis",
              "flashcards_metric": "% revisado · cobertura"}
    st.dataframe(frame.reindex(columns=labels).rename(columns=labels), hide_index=True, width="stretch")
    st.caption("Cada linha vem diretamente do nível de área. % revisado é cobertura; acerto PDF não foi atribuído à primeira ou última tentativa.")
    left, right = st.columns(2)
    with left:
        st.write("**Diagnóstico dos indicadores**")
        st.bar_chart(pd.DataFrame({"Registros": [data["classification"][c] for c in "ABCD"]}, index=["A · candidato", "B · seletivo", "C · revisão", "D · sem dados"]), color="#36c8b5")
    with right:
        st.write("**Decisões registradas**")
        st.dataframe(pd.DataFrame([{"Estado": k.replace("_", " "), "Itens": v} for k, v in data["planner"].items()]), hide_index=True, width="stretch")
        st.caption(f"{data['reevaluation_due']} itens com reavaliação vencida ou para hoje. Nenhuma ação automática.")
    with st.expander("Muitos cartões e pouca prática de questões"):
        st.caption("Sinal exploratório: pelo menos 100 cartões estudados no PDF e menos de 30 respondidas na fonte associada, ou fonte Qbank ausente. Não implica domínio nem suspensão.")
        if data["practice_gaps"]:
            st.dataframe(pd.DataFrame(data["practice_gaps"]), hide_index=True, width="stretch")
        else:
            st.caption("Nenhum registro neste recorte.")
    if not data["longitudinal_available"]:
        st.info("Há apenas uma data de relatórios. Ainda não é possível apresentar evolução longitudinal.")
    else:
        st.caption("Há múltiplas datas na biblioteca. Compare fontes equivalentes no módulo de evolução.")
