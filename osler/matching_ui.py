"""Tela de cruzamento, com sugestões e decisões explícitas por par de fontes."""
import json
import sqlite3

import pandas as pd
import streamlit as st

from .matching_exports import matching_csv, matching_json, unified_records
from .matching_service import approve_match, export_matching, load_matching, revoke_match
from .models import normalize_path


def _label(entry):
    scope = "Todos os temas" if entry["scope"] == "todos" else "Somente iniciados" if entry["scope"] == "iniciados" else "Escopo desconhecido"
    date = "/".join(reversed(entry["report_date"].split("-"))) if entry["report_date"] else "Data ausente"
    return f"{scope} · {date} · {entry['filename']}"


def _choose(entries, label, key):
    by_id = {r["file_sha256"]: r for r in entries}
    default = max(entries, key=lambda r: (r["scope"] == "todos", r["report_date"] or "", r["imported_at"]))["file_sha256"]
    return st.selectbox(label, list(by_id), index=list(by_id).index(default), format_func=lambda key: _label(by_id[key]), key=key)


def _review(repo, result):
    pair = f"{result.qbank_report_id}_{result.flashcards_report_id}"
    q_free = {r.qbank_index: r.qbank for r in result.rows if r.association == "somente_qbank" and r.qbank.is_leaf}
    f_free = {r.flashcards_index: r.flashcards for r in result.rows if r.association == "somente_flashcards" and r.flashcards.is_leaf}
    st.caption("Aprovar aqui registra uma correspondência local entre assuntos. Nenhuma suspensão é realizada.")
    if q_free and f_free:
        qi = st.selectbox("Tema do Qbank", [None, *q_free], format_func=lambda i: "Selecione um tema" if i is None else " → ".join(q_free[i].path), key=f"manual_q_{pair}")
        candidates = {i: r for i, r in f_free.items() if qi is None or normalize_path(r.path)[0] == normalize_path(q_free[qi].path)[0]}
        fi = st.selectbox("Tema dos flashcards", [None, *candidates], format_func=lambda i: "Selecione um tema" if i is None else " → ".join(candidates[i].path), key=f"manual_f_{pair}")
        if qi is not None and fi is not None:
            q, f = q_free[qi], candidates[fi]
            st.write("**Confira os dois caminhos completos antes de aprovar:**")
            st.write(f"Qbank: {' → '.join(q.path)} · página {q.page} · {q.studied} respondidas · acerto PDF {q.acerto_pdf.raw}")
            st.write(f"Flashcards: {' → '.join(f.path)} · página {f.page} · {f.studied} estudados · cobertura revisada {f.percentual_revisado.raw}")
        note = st.text_area("Justificativa da associação", key=f"manual_note_{pair}", placeholder="Explique como conferiu que os dois caminhos representam o mesmo assunto.")
        if st.button("Aprovar associação", type="primary", disabled=qi is None or fi is None, key=f"approve_manual_{pair}"):
            try:
                approve_match(repo, result.qbank_report_id, result.flashcards_report_id, qi, fi, note)
                st.session_state["cross_notice"] = "Associação aprovada e registrada no histórico local."
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    else:
        st.info("Não há terminais livres nas duas fontes para uma nova associação manual.")
    active = repo.active_matches(result.qbank_report_id, result.flashcards_report_id)
    if active:
        st.divider()
        q_report, f_report = repo.get_report(result.qbank_report_id), repo.get_report(result.flashcards_report_id)
        by_id = {r["id"]: r for r in active}
        selected = st.selectbox("Associação manual registrada", list(by_id), key=f"remove_selection_{pair}",
                                format_func=lambda i: f"{' → '.join(q_report.records[by_id[i]['qbank_ordinal']].path)} ↔ {' → '.join(f_report.records[by_id[i]['flashcards_ordinal']].path)}")
        st.caption(by_id[selected]["note"])
        if st.button("Remover associação selecionada", key=f"remove_manual_{pair}"):
            try:
                revoke_match(repo, selected)
                st.session_state["cross_notice"] = "Associação removida. Histórico e fontes preservados."
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))


def render_crossing(repo):
    st.subheader("Cruzamento de Qbank e flashcards")
    st.caption("Um par de fontes por vez, com correspondência exata por hierarquia e revisão manual das diferenças.")
    entries = [r for r in repo.list_reports(False) if r["complete"]]
    q_entries = [r for r in entries if r["kind"] == "qbank"]
    f_entries = [r for r in entries if r["kind"] == "flashcards"]
    if not q_entries or not f_entries:
        st.info("Importe um relatório de Qbank e de Flashcards com todas as páginas reconhecidas para cruzar os dados.")
        return
    c1, c2 = st.columns(2)
    with c1:
        q_id = _choose(q_entries, "Fonte Qbank", "cross_q_id")
    with c2:
        f_id = _choose(f_entries, "Fonte Flashcards", "cross_f_id")
    threshold = st.slider("Semelhança mínima para sugestões textuais", min_value=0.50, max_value=0.99, value=0.86, step=0.01, key="cross_threshold")
    st.caption("Sugestões procuram terminais no mesmo ancestral direto. O valor mede semelhança de texto; todas exigem aprovação manual.")
    try:
        result = load_matching(repo, q_id, f_id, threshold)
    except (ValueError, KeyError, sqlite3.Error) as exc:
        st.error(str(exc))
        return
    if "cross_notice" in st.session_state:
        st.success(st.session_state.pop("cross_notice"))
    stats = result.stats
    columns = st.columns(4)
    for col, label, value in zip(columns,
                                 ["Pares exatos", "Terminais comparáveis", "Qbank associado", "Flashcards associados"],
                                 [stats["pares_exatos"], stats["pares_terminais"], f"{stats['taxa_qbank']:.1f}%", f"{stats['taxa_flashcards']:.1f}%"]):
        col.metric(label, value)
    st.caption(f"Todos os níveis: {stats['pares_total']} pares / {stats['registros_qbank']} registros Qbank; {stats['pares_total']} pares / {stats['registros_flashcards']} registros Flashcards. {stats['pares_manuais']} associações manuais.")
    st.caption(f"Somente terminais comparáveis: {stats['pares_terminais']} / {stats['terminais_qbank']} terminais Qbank; {stats['pares_terminais']} / {stats['terminais_flashcards']} terminais Flashcards.")
    if stats["granularidades_diferentes"]:
        st.warning(f"{stats['granularidades_diferentes']} pares têm granularidades diferentes. O mesmo caminho pode ser um agregado numa fonte e um terminal na outra.")
    for finding in result.findings:
        st.warning(finding.message)
    st.info("Acerto PDF não identifica primeira ou última tentativa. % revisado é cobertura. A associação não indica domínio e não autoriza suspensão.")
    rows = unified_records(result)
    frame = pd.DataFrame(rows)
    a, b, c = st.columns([2, 1, 1.5])
    search = a.text_input("Buscar nas duas hierarquias", key="cross_search", placeholder="Ex.: Cicatrização")
    area = b.selectbox("Área do cruzamento", ["Todas", *sorted(frame["area"].unique())], key="cross_area")
    view = c.selectbox("Mostrar", ["Terminais e temas sem par", "Todos os níveis", "Terminais nas duas fontes", "Sem correspondência", "Granularidade diferente"], key="cross_view")
    filtered = frame
    if search:
        query = normalize_path([search])[0]
        # Ausências podem virar NaN na tabela. Normalizar só a cópia textual da
        # busca mantém os indicadores e as fontes ausentes sem valores inventados.
        search_paths = filtered["hierarquia_qbank"].fillna("") + " " + filtered["hierarquia_flashcards"].fillna("")
        filtered = filtered[search_paths.map(lambda path: query in normalize_path([path])[0])]
    if area != "Todas":
        filtered = filtered[filtered["area"] == area]
    if view == "Terminais e temas sem par":
        filtered = filtered[filtered["tipo_registro"] != "agregado"]
    elif view == "Terminais nas duas fontes":
        filtered = filtered[filtered["tipo_registro"] == "terminal_comparavel"]
    elif view == "Sem correspondência":
        filtered = filtered[~filtered["associacao"].isin(["exata", "manual"])]
    elif view == "Granularidade diferente":
        filtered = filtered[filtered["tipo_registro"] == "granularidade_diferente"]
    labels = {"hierarquia_qbank": "Hierarquia Qbank", "hierarquia_flashcards": "Hierarquia Flashcards", "associacao": "Associação",
              "tipo_registro": "Tipo", "questoes_respondidas": "Respondidas", "acerto_pdf_texto": "Acerto PDF",
              "cartoes_estudados": "Cartões estudados", "percentual_revisado_texto": "% revisado", "qualidade_dados": "Qualidade", "dados_ausentes": "Dados ausentes"}
    st.caption(f"{len(filtered)} linhas exibidas. Não há soma global de questões/cartões entre pais e filhos.")
    st.dataframe(filtered[list(labels)].rename(columns=labels), hide_index=True, width="stretch", height=450)
    buttons = st.columns(3)
    buttons[0].download_button("Baixar tabela unificada CSV", matching_csv(result), "tabela_unificada.csv", "text/csv", key="cross_download_csv")
    buttons[1].download_button("Baixar cruzamento JSON", matching_json(result), "cruzamento.json", "application/json", key="cross_download_json")
    if buttons[2].button("Salvar versão local", key="cross_save"):
        try:
            saved = export_matching(repo, result)
            st.success(f"Versão preservada em {saved.folder}")
        except OSError as exc:
            st.error(str(exc))
    with st.expander(f"Registros sem correspondência · Qbank {stats['sem_flashcards']} · Flashcards {stats['sem_qbank']}"):
        unmatched = frame[~frame["associacao"].isin(["exata", "manual"])]
        st.dataframe(unmatched[["hierarquia_qbank", "hierarquia_flashcards", "associacao", "tipo_registro", "qualidade_dados"]], hide_index=True, width="stretch", height=300)
        st.caption("Todos os registros sem par, incluindo agregados e hierarquias bloqueadas, estão nesta lista e no CSV completo.")
    with st.expander(f"Sugestões para revisão · {len(result.suggestions)} opções"):
        if result.suggestions:
            q_report, f_report = repo.get_report(q_id), repo.get_report(f_id)
            st.dataframe(pd.DataFrame([{"Qbank": " → ".join(q_report.records[s.qbank_index].path),
                                         "Flashcards": " → ".join(f_report.records[s.flashcards_index].path),
                                         "Semelhança textual": f"{100*s.similarity:.1f}%", "Mais de uma possibilidade": s.ambiguous}
                                        for s in result.suggestions]), hide_index=True, width="stretch")
        else:
            st.caption("Nenhuma sugestão dentro do contexto e do limite escolhidos.")
    with st.expander("Revisão manual das associações"):
        _review(repo, result)
    with st.expander("Histórico das associações deste par"):
        events = repo.matching_events(q_id, f_id)
        if events:
            st.dataframe(pd.DataFrame([{**e, "details": json.loads(e["details"])} for e in events]), hide_index=True, width="stretch")
        else:
            st.caption("Nenhuma decisão manual registrada para este par.")
