"""Entrada manual e triagem A–D, com fontes e versões visíveis."""
from datetime import date
import json
import sqlite3

import pandas as pd
import streamlit as st

from .assessment_service import AssessmentService, classification_csv, eligible, result_records
from .classification import ClassifierConfig, DEFAULT_WEIGHTS
from .matching_service import load_matching
from .matching_ui import _choose
from .planner_service import today_local
from .observations import COUNTS, ENUMS, FLAGS, OBSERVATION_FIELDS, parse_observation

CATEGORY_LABELS = {"A": "A · candidato forte à suspensão", "B": "B · avaliar redução seletiva", "C": "C · manter revisão prioritária", "D": "D · dados insuficientes"}
INPUT_LABELS = {"questoes_distintas": "Questões distintas", "respostas_totais": "Respostas totais",
                "acerto_primeira_tentativa": "Acerto na primeira tentativa (%)", "acerto_ultima_tentativa": "Acerto na última tentativa (%)",
                "acerto_recente": "Acerto recente (%)", "cartoes_estudados": "Cartões estudados (informação manual)",
                "cartoes_ativos": "Cartões ativos", "cartoes_pendentes": "Cartões pendentes", "cartoes_futuros": "Cartões futuros",
                "cartoes_selecionaveis": "Cartões selecionáveis", "erros_criticos": "Há erros críticos?", "erros_recorrentes": "Há erros recorrentes?",
                "cobertura_suficiente": "A amostra cobre suficientemente o tema?", "relevancia_residencia": "Relevância para residência",
                "incidencia_provas": "Incidência em provas", "dificuldade": "Dificuldade", "risco_perda": "Risco de perda de conhecimento",
                "confianca_flashcards": "Confiança subjetiva nos flashcards (1 a 5)"}


def _policies(service):
    config = ClassifierConfig(**st.session_state.get("assessment_config", {})).validate()
    with st.expander("Critérios e pesos configuráveis"):
        st.caption("Limites experimentais e ajustáveis. Eles não foram validados cientificamente para decidir suspensões.")
        policies = service.store.policies()
        if policies:
            by_id = {p["id"]: p for p in policies}
            selected = st.selectbox("Versão salva de critérios", list(by_id), format_func=lambda i: f"{i} · {by_id[i]['name']}")
            if st.button("Carregar critérios salvos"):
                st.session_state["assessment_config"] = by_id[selected]["config"]
                for key in list(st.session_state):
                    if key.startswith("cfg_"):
                        del st.session_state[key]
                st.rerun()
        with st.form("assessment_policy_form"):
            labels = {"min_questions": "Mínimo de questões distintas", "a_initial": "Inicial mínimo para A (%)", "a_last": "Última mínima para A/B (%)",
                      "b_initial": "Inicial mínimo para B (%)", "b_improvement": "Melhora mínima para B (pontos percentuais)",
                      "c_recent": "Desempenho recente abaixo de (%) pede revisão", "max_age_days": "Validade dos indicadores (dias)",
                      "volume_reference": "Referência de volume de cartões", "wilson_floor": "Limite inferior de Wilson para priorizar (%)"}
            columns = st.columns(3)
            values = {}
            for i, (name, label) in enumerate(labels.items()):
                integer = name in {"min_questions", "max_age_days", "volume_reference"}
                values[name] = columns[i % 3].number_input(label, min_value=1 if integer else 0.0,
                                                          value=int(getattr(config, name)) if integer else float(getattr(config, name)),
                                                          step=1 if integer else 1.0, key=f"cfg_{name}")
            coverage = st.number_input("Mínimo de peso sustentado por dados disponíveis (%)", min_value=1.0, max_value=100.0,
                                       value=100*config.min_weight_coverage, key="cfg_coverage")
            weights = {}
            for i, name in enumerate(DEFAULT_WEIGHTS):
                weights[name] = columns[i % 3].number_input(f"Peso: {name}", min_value=0.0, value=float(config.weights.get(name, 0)), step=1.0, key=f"cfg_weight_{name}")
            name = st.text_input("Nome da versão de critérios", value="Critérios de estudo", key="cfg_name")
            apply = st.form_submit_button("Aplicar critérios nesta sessão")
            save = st.form_submit_button("Salvar versão dos critérios")
        if apply or save:
            try:
                updated = ClassifierConfig(**values, min_weight_coverage=coverage/100, weights=weights).validate()
                if save:
                    service.store.save_policy(name, updated)
                st.session_state["assessment_config"] = updated.to_dict()
                st.session_state["assessment_notice"] = "Critérios atualizados; versões anteriores preservadas." if save else "Critérios aplicados nesta sessão."
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    return config


def _edit_observation(service, matching, as_of, analyzed):
    rows = {r.row_id: r for r in matching.rows if eligible(r)}
    if not rows:
        st.info("Não há subtemas elegíveis neste par.")
        return
    candidate_ids = [i["row_id"] for i in analyzed["items"] if i["eligible"] and i["classification"]["category"] in "AB"]
    default = candidate_ids[0] if candidate_ids else next(iter(rows))
    selected_id = st.selectbox("Tema para editar indicadores", list(rows), index=list(rows).index(default),
                              format_func=lambda i: " → ".join((rows[i].qbank or rows[i].flashcards).path), key="assessment_row")
    row = rows[selected_id]
    current = next(i for i in analyzed["items"] if i["row_id"] == selected_id)
    data = current["observation"] or {}
    revision = service.store.revision(selected_id)
    st.caption(f"Revisão local {revision}. Salvar cria uma observação versionada; o PDF permanece intacto.")
    if current["observation_id"]:
        st.info(f"Observação em uso: {current['observation_id']} · {data['data_observacao']} · {data['origem_da_informacao']}")
    with st.form(f"observation_form_{selected_id}_{revision}"):
        values = {}
        observed = st.date_input("Data da observação", value=date.fromisoformat(data.get("data_observacao", as_of)),format='DD/MM/YYYY')
        values["data_observacao"] = observed.isoformat()
        values["origem_da_informacao"] = st.text_input("Origem dos indicadores", value=data.get("origem_da_informacao", ""), placeholder="Ex.: consulta manual na interface oficial")
        confidence_values = ["informado_usuario", "conferido_usuario", "estimado"]
        values["nivel_de_confiabilidade"] = st.selectbox("Confiabilidade declarada", confidence_values,
                                                       index=confidence_values.index(data.get("nivel_de_confiabilidade", "informado_usuario")))
        columns = st.columns(3)
        numeric = [f for f in OBSERVATION_FIELDS if f in COUNTS or f.startswith("acerto_") or f == "confianca_flashcards"]
        for index, field in enumerate(numeric):
            values[field] = columns[index % 3].text_input(INPUT_LABELS[field], value="" if data.get(field) is None else str(data[field]))
        for index, field in enumerate([f for f in OBSERVATION_FIELDS if f in FLAGS]):
            options = [None, False, True]
            values[field] = columns[index % 3].selectbox(INPUT_LABELS[field], options, index=options.index(data.get(field)),
                                                       format_func=lambda v: "Não informado" if v is None else "Sim" if v else "Não")
        for index, (field, options_set) in enumerate(ENUMS.items()):
            options = [None, *sorted(options_set)]
            values[field] = columns[index % 3].selectbox(INPUT_LABELS[field], options, index=options.index(data.get(field)),
                                                       format_func=lambda v: "Não informado" if v is None else v)
        values["fonte_incidencia"] = st.text_input("Fonte da incidência em provas", value=data.get("fonte_incidencia", ""))
        values["nota"] = st.text_area("Observações sobre os indicadores", value=data.get("nota", ""))
        submitted = st.form_submit_button("Salvar nova observação", type="primary")
    if submitted:
        try:
            service.save_observation(matching, selected_id, parse_observation(values), revision)
            st.session_state["assessment_notice"] = "Observação salva com histórico; dados extraídos não foram alterados."
            st.rerun()
        except (ValueError, sqlite3.Error) as exc:
            st.error(str(exc))
    with st.expander("Justificativa e fontes deste tema"):
        c = current["classification"]
        st.write(CATEGORY_LABELS[c["category"]])
        for reason in c["reasons"]:
            st.write(reason)
        for evidence in c["evidence"]:
            st.caption(evidence)
        if c["wilson_low"] is not None:
            st.write(f"Wilson 95% aproximado: {c['wilson_low']:.0f}% a {c['wilson_high']:.0f}%.")
        st.caption("Dados ausentes: " + ", ".join(c["missing"]))
        for warning in c["warnings"]:
            st.caption(warning)
        st.json({"PDF_Qbank": asdict_record(row.qbank), "PDF_Flashcards": asdict_record(row.flashcards), "indicadores_manuais": current["observation"]})
    with st.expander("Histórico de indicadores deste tema"):
        history = service.store.history(selected_id)
        if history:
            st.dataframe(pd.DataFrame([{"ID": h["id"], "Ativa": bool(h["active"]), **h["observation"]} for h in history]), hide_index=True, width="stretch")
            active = [h["id"] for h in history if h["active"]]
            if active:
                chosen = st.selectbox("Observação a desconsiderar", active)
                if st.button("Desconsiderar observação"):
                    try:
                        service.revoke(chosen, revision)
                        st.session_state["assessment_notice"] = "Observação desconsiderada; histórico preservado."
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        else:
            st.caption("Sem observações manuais para este contexto.")


def asdict_record(row):
    if row is None:
        return None
    from dataclasses import asdict
    return asdict(row)


def render_assessment(repo):
    st.subheader("Classificação e indicadores manuais")
    entries = [r for r in repo.list_reports(False) if r["complete"]]
    q = [r for r in entries if r["kind"] == "qbank"]
    f = [r for r in entries if r["kind"] == "flashcards"]
    if not q or not f:
        st.info("Importe fontes de Qbank e Flashcards para classificar os subtemas.")
        return
    service = AssessmentService(repo)
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        q_id = _choose(q, "Qbank para classificar", "assessment_q_id")
    with c2:
        f_id = _choose(f, "Flashcards para classificar", "assessment_f_id")
    as_of = c3.date_input("Data de análise", value=today_local(), key="assessment_asof",format='DD/MM/YYYY').isoformat()
    config = _policies(service)
    try:
        matching = load_matching(repo, q_id, f_id)
        analyzed = service.analyze(matching, as_of, config)
    except (ValueError, sqlite3.Error) as exc:
        st.error(str(exc))
        return
    if "assessment_notice" in st.session_state:
        st.success(st.session_state.pop("assessment_notice"))
    st.info("A/B indicam candidatos para avaliação manual. Nenhum tema é suspenso pelo aplicativo. Campos vazios não são zero; % revisado não é acerto.")
    for col, category in zip(st.columns(4), "ABCD"):
        col.metric(CATEGORY_LABELS[category], analyzed["stats"][category])
    st.caption(f"Categorias contam apenas terminais elegíveis; {analyzed['stats']['excluidos']} agregados, bloqueados ou granularidades diferentes excluídos desses totais.")
    for finding in matching.findings:
        st.warning(finding.message)
    frame = pd.DataFrame(result_records(analyzed))
    c1, c2 = st.columns([2, 1])
    query = c1.text_input("Buscar na classificação", key="assessment_search")
    categories = c2.multiselect("Categorias exibidas", list("ABCD"), default=["A", "B"], key="assessment_categories")
    visible = frame[frame["elegivel"] & frame["categoria"].isin(categories)]
    if query:
        from .models import normalize_path
        normalized = normalize_path([query])[0]
        visible = visible[visible["hierarquia"].map(lambda v: normalized in normalize_path([v])[0])]
    ranks = {"alta": 0, "media": 1, "baixa": 2, "pendente_validacao": 3, "sem_dados": 4, "manter_revisao": 5}
    visible = visible.assign(_order=visible["prioridade"].map(ranks)).sort_values(["_order", "categoria", "hierarquia"])
    labels = {"hierarquia": "Hierarquia", "categoria": "Categoria", "prioridade": "Faixa de prioridade", "questoes_distintas": "Questões distintas",
              "acerto_primeira_tentativa": "Inicial (%)", "acerto_ultima_tentativa": "Última (%)", "cartoes_avaliaveis": "Cartões avaliáveis",
              "justificativa": "Justificativa", "dados_ausentes": "Dados ausentes"}
    st.dataframe(visible[list(labels)].rename(columns=labels), hide_index=True, width="stretch", height=350)
    st.caption("Ordenação por faixas e nome, sem escore decimal. Cartões envolvidos não equivalem a revisões eliminadas.")
    columns = st.columns(3)
    columns[0].download_button("Baixar classificação CSV", classification_csv(analyzed), "classificacao.csv", "text/csv")
    columns[1].download_button("Baixar classificação JSON", json.dumps(analyzed, ensure_ascii=False, indent=2), "classificacao.json", "application/json")
    if columns[2].button("Salvar versão da análise"):
        try:
            exported = service.export(analyzed)
            st.success(f"Versão local preservada em {exported.folder}")
        except OSError as exc:
            st.error(str(exc))
    with st.expander("Importar indicadores por CSV"):
        st.caption("Use o modelo deste par. Preencha somente as linhas desejadas, em UTF-8 e separador ;. Um erro ou conflito recusa o lote inteiro.")
        st.download_button("Baixar modelo de indicadores", service.csv_template(matching, as_of), "modelo_indicadores.csv", "text/csv")
        uploaded = st.file_uploader("CSV com indicadores manuais", type=["csv"], key="assessment_csv")
        if st.button("Importar observações CSV", disabled=uploaded is None):
            try:
                count = service.import_csv(matching, uploaded.getvalue())
                st.session_state["assessment_notice"] = f"{count} observações importadas; histórico preservado."
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    with st.expander("Editar indicadores de um subtema", expanded=True):
        _edit_observation(service, matching, as_of, analyzed)
