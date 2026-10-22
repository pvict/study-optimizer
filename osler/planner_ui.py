"""Seleção e acompanhamento de decisões do usuário; nenhuma ação na Osler."""
from datetime import date
import json
import sqlite3

import pandas as pd
import streamlit as st

from .assessment_service import result_records
from .classification import ClassifierConfig
from .matching_service import load_matching
from .matching_ui import _choose
from .models import normalize_path
from .planner_exports import checklist_csv, checklist_markdown, checklist_records
from .planner_service import PlannerService, today_local
from .planner_storage import TRANSITIONS

STATUS_LABELS = {"sugerido": "Sugerido", "aguardando_validacao": "Aguardando validação", "aprovado_usuario": "Aprovado pelo usuário",
                 "aplicado_manualmente": "Aplicado manualmente na Osler", "reativado": "Reativado", "cancelado": "Cancelado"}


def _batches(service):
    batches = service.list_batches()
    st.write("**Lotes e checklists**")
    if not batches:
        st.info("Nenhum lote criado. Selecione candidatos e crie um lote sugerido.")
        return
    names = {b["id"]: b["name"] for b in batches}
    batch_id = st.selectbox("Lote para consultar", list(names), format_func=lambda i: f"{i:02d} · {names[i]}", key="planner_batch_id")
    batch = service.get_batch(batch_id)
    records = checklist_records(batch)
    display = pd.DataFrame(records)[["item_id", "hierarquia", "estado", "categoria", "cartoes_avaliaveis", "data_aplicacao", "data_reavaliacao"]].copy()
    display["estado"] = display["estado"].map(STATUS_LABELS)
    display[["data_aplicacao", "data_reavaliacao"]] = display[["data_aplicacao", "data_reavaliacao"]].fillna("")
    st.dataframe(display.rename(columns={"item_id": "Item", "hierarquia": "Hierarquia", "estado": "Estado", "categoria": "Categoria", "cartoes_avaliaveis": "Cartões avaliáveis", "data_aplicacao": "Aplicação", "data_reavaliacao": "Reavaliação"}), hide_index=True, width="stretch")
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("Checklist CSV", checklist_csv(batch), f"lote_{batch_id:02d}.csv", "text/csv")
    c2.download_button("Checklist para imprimir", checklist_markdown(batch), f"lote_{batch_id:02d}.md", "text/markdown")
    c3.download_button("Lote JSON auditável", json.dumps(batch, ensure_ascii=False, indent=2), f"lote_{batch_id:02d}.json", "application/json")
    if c4.button("Preservar checklist local"):
        try:
            st.success(f"Checklist preservado em {service.export(batch_id).folder}")
        except OSError as exc:
            st.error(str(exc))
    by_id = {i["id"]: i for i in batch["items"]}
    item_id = st.selectbox("Item para registrar decisão", list(by_id), format_func=lambda i: " → ".join(by_id[i]["snapshot"]["flashcards_path"]), key=f"planner_item_{batch_id}")
    item = by_id[item_id]
    st.caption(f"Estado atual: {STATUS_LABELS[item['status']]} · revisão {item['revision']}. Análise preservada de {batch['analysis_date']}.")
    with st.expander("Indicadores e justificativa preservados"):
        st.json(item["snapshot"])
    with st.form(f"planner_notes_{item_id}_{item['revision']}"):
        note = st.text_area("Observação do item (opcional)", value=item["note"])
        reeval = st.text_input("Data de reavaliação (AAAA-MM-DD, opcional)", value=item["reevaluation_date"] or "")
        save = st.form_submit_button("Salvar observação e reavaliação")
    if save:
        try:
            service.update_item(item_id, note or "Reavaliação atualizada pelo usuário.", reeval.strip() or None, item["revision"])
            st.session_state["planner_notice"] = "Observação registrada com histórico."
            st.rerun()
        except (ValueError, sqlite3.Error) as exc:
            st.error(str(exc))
    options = [s for s in STATUS_LABELS if s in TRANSITIONS[item["status"]]]
    if options:
        target = st.selectbox("O que você quer registrar?", options, format_func=STATUS_LABELS.get, key=f"action_target_{item_id}_{item['revision']}")
        actions = {"aguardando_validacao": "Quero avaliar este tema", "aprovado_usuario": "Quero fazer essa redução", "aplicado_manualmente": "Já fiz essa mudança na Osler", "reativado": "Já reativei na Osler", "cancelado": "Tirar deste lote"}
        with st.form(f"planner_action_{item_id}_{item['revision']}"):
            action_date = st.date_input("Data da decisão ou ação realizada", value=today_local(), max_value=today_local(),format='DD/MM/YYYY')
            reason = st.text_area("Quer deixar uma observação? (opcional)")
            if target in {"aplicado_manualmente", "reativado"}:
                st.caption("Use este botão somente depois de realizar a ação pessoalmente na Osler.")
            submitted = st.form_submit_button(actions[target])
        if submitted:
            try:
                service.transition(item_id, target, reason or f"Usuário escolheu: {actions[target]}.", item["revision"], action_date.isoformat(), confirmed=True)
                st.session_state["planner_notice"] = "Etapa registrada localmente. Confira o histórico e a data de reavaliação."
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    with st.expander("Histórico de decisões deste item"):
        st.dataframe(pd.DataFrame([e for e in service.events() if e["item_id"] == item_id]), hide_index=True, width="stretch")


def render_planner(repo):
    st.subheader("Planejador de Suspensões")
    st.info("Selecione e valide os conceitos pessoalmente. Criar lote mantém os itens como sugeridos; aplicação e reativação exigem confirmação da ação realizada por você.")
    service = PlannerService(repo)
    if "planner_notice" in st.session_state:
        st.success(st.session_state.pop("planner_notice"))
    entries = [r for r in repo.list_reports(False) if r["complete"]]
    q, f = [r for r in entries if r["kind"] == "qbank"], [r for r in entries if r["kind"] == "flashcards"]
    if not q or not f:
        st.info("Importe Qbank e Flashcards para selecionar candidatos.")
        return
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        q_id = _choose(q, "Qbank do planejador", "planner_q_id")
    with c2:
        f_id = _choose(f, "Flashcards do planejador", "planner_f_id")
    day = c3.date_input("Data da seleção", value=today_local(), max_value=today_local(), key="planner_asof",format='DD/MM/YYYY').isoformat()
    cfg = ClassifierConfig(**st.session_state.get("assessment_config", {})).validate()
    try:
        matching = load_matching(repo, q_id, f_id)
        analysis = service.assessments.analyze(matching, day, cfg)
    except (ValueError, sqlite3.Error) as exc:
        st.error(str(exc))
        return
    source_rows = {r.row_id: r for r in matching.rows}
    records = result_records(analysis)
    candidates = [r for r in records if r["elegivel"] and r["categoria"] in {"A", "B"} and source_rows[r["registro_id"]].flashcards is not None]
    if not candidates:
        st.caption("Nenhum candidato A/B com flashcards neste par. Complete os indicadores na tela de dados; percentuais do PDF não substituem a primeira tentativa.")
    else:
        frame = pd.DataFrame(candidates)
        frame["area"] = frame["registro_id"].map(lambda i: source_rows[i].flashcards.path[0])
        c1, c2, c3 = st.columns([2, 1, 1])
        search = c1.text_input("Buscar candidato", key="planner_search")
        area = c2.selectbox("Disciplina do candidato", ["Todas", *sorted(frame["area"].unique())], key="planner_area")
        category = c3.multiselect("Categoria do candidato", ["A", "B"], default=["A", "B"], key="planner_categories")
        c1, c2 = st.columns(2)
        initial = c1.slider("Faixa de acerto inicial (%)", 0, 100, (0, 100), key="planner_initial_range")
        order = c2.selectbox("Ordenar candidatos", ["Faixa de prioridade", "Maior quantidade de cartões avaliáveis", "Hierarquia"], key="planner_order")
        visible = frame[frame["categoria"].isin(category) & frame["acerto_primeira_tentativa"].between(*initial)]
        if area != "Todas":
            visible = visible[visible["area"] == area]
        if search:
            query = normalize_path([search])[0]
            visible = visible[visible["hierarquia"].map(lambda v: query in normalize_path([v])[0])]
        if order == "Maior quantidade de cartões avaliáveis":
            visible = visible.sort_values(["cartoes_avaliaveis", "hierarquia"], ascending=[False, True], na_position="last")
        elif order == "Faixa de prioridade":
            ranks = {"alta": 0, "media": 1, "baixa": 2, "pendente_validacao": 3, "sem_dados": 4}
            visible = visible.assign(_rank=visible["prioridade"].map(ranks)).sort_values(["_rank", "hierarquia"])
        else:
            visible = visible.sort_values("hierarquia")
        labels = {"hierarquia": "Hierarquia", "questoes_distintas": "Questões distintas", "acerto_primeira_tentativa": "Inicial (%)", "acerto_recente": "Recente (%)",
                  "acerto_ultima_tentativa": "Última (%)", "cartoes_estudados": "Estudados · manual", "cartoes_pendentes": "Pendentes", "cartoes_futuros": "Futuros",
                  "cartoes_avaliaveis": "Avaliáveis", "categoria": "Categoria", "prioridade": "Prioridade", "justificativa": "Justificativa", "dados_ausentes": "Dados ausentes"}
        st.dataframe(visible[list(labels)].rename(columns=labels), hide_index=True, width="stretch", height=300)
        st.caption(f"{len(visible)} candidatos exibidos. Volume é quantidade de itens para avaliar, sem estimativa de revisões eliminadas. Os critérios são os configurados nesta sessão.")
        lookup = {r["registro_id"]: r["hierarquia"] for r in candidates}
        selected = st.multiselect("Selecionar candidatos para o lote", visible["registro_id"].tolist(), format_func=lookup.get, key="planner_selection")
        with st.form("planner_create"):
            name = st.text_input("Nome do lote", value="Lote de avaliação manual")
            note = st.text_area("Finalidade do lote")
            create = st.form_submit_button("Criar lote sugerido", disabled=not selected)
        if create:
            try:
                bid = service.create_batch(matching, selected, name, note or "Temas selecionados pelo usuário para avaliação.", day, cfg)
                st.session_state["planner_notice"] = f"Lote {bid:02d} criado como sugerido, sem aprovação ou aplicação."
                st.session_state.pop("planner_selection", None)
                st.session_state["planner_batch_id"] = bid
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    st.divider()
    _batches(service)
