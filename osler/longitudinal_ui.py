"""Comparação entre documentos e histórico de ações declaradas."""
import json

import pandas as pd
import streamlit as st

from .longitudinal import compare_reports, decision_timeline
from .planning_service import PlanningService


def render_evolution(repo):
    st.subheader("Evolução e histórico")
    entries = [r for r in repo.list_reports(False) if r["complete"] and r["report_date"]]
    pairs = [(a, b) for a in entries for b in entries if a["kind"] == b["kind"] and a["scope"] == b["scope"] and a["report_date"] < b["report_date"]]
    if not pairs:
        st.info("Ainda não há duas datas comparáveis do mesmo tipo e escopo. Importe novos PDFs manualmente para acompanhar a evolução, sem inferir mudanças a partir de uma única data.")
    else:
        by_key = {a["file_sha256"]+b["file_sha256"]: (a, b) for a, b in pairs}
        key = st.selectbox("Fontes para comparação", list(by_key), format_func=lambda k: f"{by_key[k][0]['kind']} · {by_key[k][0]['scope']} · {by_key[k][0]['report_date']} → {by_key[k][1]['report_date']}")
        a, b = by_key[key]
        try:
            result = compare_reports(repo, a["file_sha256"], b["file_sha256"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Estudados na fonte anterior", result["cover"]["old_studied"])
            c2.metric("Estudados na fonte recente", result["cover"]["new_studied"])
            c3.metric("Variação documental", result["cover"]["studied_delta"])
            st.caption(result["metric_label"])
            frame = pd.DataFrame(result["common"])
            query = st.text_input("Buscar tema na comparação")
            if query and not frame.empty:
                from .models import normalize_path
                frame = frame[frame["hierarchy"].map(lambda v: normalize_path([query])[0] in normalize_path([v])[0])]
            st.dataframe(frame.rename(columns={"hierarchy": "Hierarquia", "old_studied": "Estudados antes", "new_studied": "Estudados agora", "studied_delta": "Variação estudados", "old_total": "Acervo antes", "new_total": "Acervo agora", "old_pdf_metric": "Percentual PDF antes", "new_pdf_metric": "Percentual PDF agora", "pdf_metric_delta_pp": "Diferença exata (p.p.)"}), hide_index=True, width="stretch")
            st.caption(f"{len(result['added'])} caminhos adicionados; {len(result['removed'])} removidos. Duplicados excluídos: {result['excluded_old']} / {result['excluded_new']}.")
            with st.expander("Caminhos adicionados/removidos e limites"):
                st.json({"adicionados": result["added"], "removidos": result["removed"]})
                for warning in result["warnings"]:
                    st.write(warning)
            st.download_button("Baixar comparação JSON", json.dumps(result, ensure_ascii=False, indent=2), "comparacao.json", "application/json")
        except ValueError as exc:
            st.error(str(exc))
    st.write("**Decisões registradas**")
    timeline = decision_timeline(repo)
    if timeline:
        frame = pd.DataFrame(timeline).set_index("date")
        st.dataframe(frame, width="stretch")
        if len(frame) >= 2:
            st.line_chart(frame[["aplicado_manualmente", "reativado"]])
        st.caption("Datas e ações declaradas pelo usuário. Não mede causalidade nem efeito na agenda. Com uma data, não há curva de evolução.")
    else:
        st.caption("Nenhuma decisão de lote registrada.")
    with st.expander("Medições de carga por fonte"):
        measurements = PlanningService(repo).measurements()
        if measurements:
            st.dataframe(pd.DataFrame([{k: m[k] for k in ("kind", "count", "observed_date", "horizon_days", "source", "note")} for m in measurements]), hide_index=True, width="stretch")
            st.caption("Medições de telas/denominadores distintos não são somadas nem consideradas efeito das suspensões.")
        else:
            st.caption("Sem medições manuais.")
