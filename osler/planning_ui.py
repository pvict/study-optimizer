"""Cenários ajustáveis de capacidade e rotina; sem cobrança de compensação."""
from .action_feedback import confirm_button,confirm_submit,notify_success

from datetime import date
import json
import sqlite3

import pandas as pd
import streamlit as st

from .planning import DAY_TYPES, DayProfile, Measurement, RoutineConfig
from .planning_service import PlanningService, planning_csv
from .planner_service import today_local

DAY_LABELS = {"normal": "Normal", "plantao": "Plantão", "descanso": "Descanso", "minimo": "Plano mínimo"}
MEASURE_LABELS = {"revisoes_periodo": "Revisões do período", "revisoes_high_yield": "Revisões High Yield · teste separado", "cartoes_pendentes": "Cartões pendentes · outra medida"}


def _configuration(service):
    cfg = RoutineConfig.from_dict(st.session_state["routine_config"]) if "routine_config" in st.session_state else RoutineConfig(start_date=today_local().isoformat())
    with st.expander("Configurar tempo, metas e calendário", expanded=False):
        st.caption("Valores iniciais são exemplos experimentais. Ajuste à sua disponibilidade; eles não representam obrigações ou sua rotina já confirmada.")
        profiles = service.profiles()
        if profiles:
            lookup = {p["id"]: p for p in profiles}
            selected = st.selectbox("Cenário salvo", list(lookup), format_func=lambda i: f"{i} · {lookup[i]['name']}")
            if st.button("Carregar cenário salvo"):
                st.session_state["routine_config"] = lookup[selected]["config"]
                for key in list(st.session_state):
                    if key.startswith("routine_input_"):
                        del st.session_state[key]
                st.rerun()
        with st.form("routine_settings"):
            c1, c2, c3 = st.columns(3)
            start = c1.date_input("Início do cenário", value=date.fromisoformat(cfg.start_date), key="routine_input_start",format='DD/MM/YYYY')
            days = c2.number_input("Período de planejamento (dias)", 1, 366, cfg.days, key="routine_input_days")
            cap = c3.number_input("Teto experimental de cartões gerais por dia", 0, 100000, cfg.daily_limit, key="routine_input_cap")
            sec = c1.number_input("Segundos por flashcard geral", 0.1, 3600.0, float(cfg.seconds_per_general), key="routine_input_general_seconds")
            err_sec = c2.number_input("Segundos por flashcard de erro", 0.1, 3600.0, float(cfg.seconds_per_error), key="routine_input_error_seconds")
            q_min = c3.number_input("Minutos por questão comentada", 0.1, 240.0, float(cfg.minutes_per_question), key="routine_input_question_minutes")
            selected_profiles = {}
            for kind, label in DAY_LABELS.items():
                profile = cfg.profiles[kind]
                st.write(f"**Dia {label.lower()}**")
                a, b, c, d = st.columns(4)
                minutes = a.number_input(f"Tempo disponível · {label} (min)", 0.0, 1440.0, float(profile.minutes), key=f"routine_input_{kind}_minutes")
                questions = b.number_input(f"Meta de questões · {label}", 0, 100000, profile.questions, key=f"routine_input_{kind}_questions")
                general = c.number_input(f"Meta de gerais · {label}", 0, 100000, profile.general_cards, key=f"routine_input_{kind}_general")
                errors = d.number_input(f"Meta de cartões dos erros · {label}", 0, 100000, profile.error_cards, key=f"routine_input_{kind}_errors")
                selected_profiles[kind] = DayProfile(minutes, questions, general, errors)
            weekdays = {}
            columns = st.columns(4)
            for weekday, label in enumerate(["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]):
                weekdays[weekday] = columns[weekday % 4].selectbox(label, list(DAY_LABELS), index=list(DAY_LABELS).index(cfg.weekday_types.get(weekday, "normal")), format_func=DAY_LABELS.get, key=f"routine_input_week_{weekday}")
            exceptions = st.text_area("Exceções por data · uma linha AAAA-MM-DD;tipo", value="\n".join(f"{day};{kind}" for day, kind in sorted(cfg.overrides.items())), help="Tipos: normal, plantao, descanso, minimo", key="routine_input_overrides")
            c1, c2 = st.columns(2)
            interval = c1.number_input("Intervalo de provas antigas em dias (0 desativa)", 0, 366, cfg.exam_every_days, key="routine_input_exam_interval")
            exam = c2.number_input("Tempo reservado por prova antiga (min)", 1.0, 1440.0, float(cfg.exam_minutes), key="routine_input_exam_minutes")
            name = st.text_input("Nome do cenário", value="Rotina experimental", key="routine_input_name")
            apply = confirm_submit("Aplicar cenário",action_key='planning_ui_58')
            save = confirm_submit("Salvar versão do cenário",action_key='planning_ui_59')
        if apply or save:
            try:
                overrides = {}
                for line in exceptions.splitlines():
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(";")]
                    if len(parts) != 2 or parts[0] in overrides:
                        raise ValueError("Exceções exigem data;tipo, sem datas repetidas.")
                    overrides[parts[0]] = parts[1]
                updated = RoutineConfig(start.isoformat(), days, cap, sec, err_sec, q_min, selected_profiles, weekdays, overrides, interval, exam).validate()
                if save:
                    notify_success(service.save_profile(name, updated),'Alterações salvas.')
                st.session_state["routine_config"] = updated.to_dict()
                notify_success(None,'Cenário atualizado.')
                st.session_state["planning_notice"] = "Cenário atualizado; versões anteriores preservadas."
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    return cfg


def _measurements(service):
    with st.expander("Medições informadas e origem"):
        measurements = service.measurements()
        if measurements:
            st.dataframe(pd.DataFrame([{"Tipo": MEASURE_LABELS[m["kind"]], "Quantidade": m["count"], "Dias": m["horizon_days"], "Data declarada": m["observed_date"],
                                        "Aproximada": m["approximate"], "Origem": m["source"], "Observação": m["note"]} for m in measurements]), hide_index=True, width="stretch")
        st.caption("As medições podem vir de telas/cortes diferentes. High Yield é um teste separado; cartões pendentes não são revisões do período.")
        with st.form("planning_measurement"):
            kind = st.selectbox("Tipo de medição", list(MEASURE_LABELS), format_func=MEASURE_LABELS.get)
            count = st.number_input("Contagem consultada manualmente", 0, 100000000, 0)
            observed = st.date_input("Data declarada da medição", value=today_local(),format='DD/MM/YYYY')
            horizon = st.number_input("Horizonte de revisões (dias; ignorado para cartões pendentes)", 1, 366, 90)
            source = st.text_input("Origem e contexto da medição")
            approximate = st.checkbox("Contagem aproximada", value=False)
            note = st.text_area("Observações sobre o corte e denominador")
            submit = confirm_submit("Registrar medição local",action_key='planning_ui_96')
        if submit:
            try:
                notify_success(service.save_measurement(Measurement(kind, count, observed.isoformat(), source, horizon if kind != "cartoes_pendentes" else None, approximate, note)),'Alterações salvas.')
                st.session_state["planning_notice"] = "Medição preservada com origem; nenhum relatório foi alterado."
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))


def render_planning(repo):
    st.subheader("Simulação de capacidade e rotina")
    st.info("Metas cabem no tempo informado; questões, erros e depois cartões gerais. Dias difíceis não geram dívida automática para amanhã. Tempos iniciais são hipóteses ajustáveis.")
    service = PlanningService(repo)
    if "planning_notice" in st.session_state:
        st.success(st.session_state.pop("planning_notice"))
    cfg = _configuration(service)
    measures = [m for m in service.measurements() if m["kind"] != "cartoes_pendentes"]
    by_id = {m["id"]: m for m in measures}
    options = [None, *by_id]
    preferred = next((m["id"] for m in measures if m["kind"] == "revisoes_periodo"), None)
    selected = st.selectbox("Carga de revisões usada no cenário", options, index=options.index(preferred),
                            format_func=lambda i: "Somente capacidade · sem carga informada" if i is None else f"{MEASURE_LABELS[by_id[i]['kind']]} · {by_id[i]['count']:,} · {by_id[i]['horizon_days']} dias · {by_id[i]['observed_date']}", key="planning_measurement_id")
    try:
        result = service.simulate(cfg, selected)
    except ValueError as exc:
        st.error(str(exc))
        result = service.simulate(cfg)
        st.caption("A rotina e a capacidade abaixo não usam a carga incompatível; excedentes permanecem ausentes.")
    def number(value):
        return f"{value:,}".replace(",", ".") if value is not None else "Não informado"
    for col, label, value in zip(st.columns(4), ["Capacidade pelo teto", "Capacidade com reservas", "Excedente pelo teto", "Excedente com reservas"],
                                 [result["nominal_capacity"], result["time_capacity"], result["excess_at_limit"], result["excess_with_time"]]):
        col.metric(label, number(value))
    st.caption(f"Período: {cfg.days} dias a partir de {cfg.start_date}. Teto em todos os dias: {number(result['ceiling_all_days'])}; dias sem tempo disponível contribuem zero. Reservas usam as metas de questões/erros e provas que caibam.")
    st.warning("Excedente é diferença aritmética neste cenário estático. Não prevê quais revisões ocorrerão em cada dia nem o efeito de suspender cartões.")
    chart = pd.DataFrame({"Cenário": ["Pelo teto", "Após reservas"], "Revisões que cabem": [result["nominal_capacity"], result["time_capacity"]]}).set_index("Cenário")
    st.bar_chart(chart, color="#36c8b5")
    with st.expander("Sensibilidade ao tempo por cartão"):
        st.dataframe(pd.DataFrame(result["sensitivity"]).rename(columns={"seconds_per_card": "Segundos por cartão", "capacity": "Capacidade do período"}), hide_index=True, width="stretch")
    st.write("**Rotina diária proposta**")
    frame = pd.DataFrame(result["days"])
    types = st.multiselect("Tipos de dia exibidos", list(DAY_LABELS), default=list(DAY_LABELS), format_func=DAY_LABELS.get, key="planning_day_types")
    shown = frame[frame["day_type"].isin(types)]
    labels = {"date": "Data", "day_type": "Tipo de dia", "available_minutes": "Tempo disponível (min)", "questions": "Questões", "general_cards": "Cartões gerais", "error_cards": "Cartões dos erros", "exam_minutes": "Prova (min)", "planned_minutes": "Tempo proposto (min)", "remaining_minutes": "Tempo livre (min)", "warning": "Observação"}
    display = shown[list(labels)].rename(columns=labels)
    display["Tipo de dia"] = display["Tipo de dia"].map(DAY_LABELS)
    st.dataframe(display, hide_index=True, width="stretch", height=400)
    st.caption("O tempo respeita cada dia. Metas que não couberam permanecem não realizadas neste cenário; não são adicionadas ao próximo dia. Reserve provas antigas apenas em datas com tempo suficiente.")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Baixar rotina CSV", planning_csv(result), "rotina.csv", "text/csv")
    c2.download_button("Baixar cenário JSON", json.dumps(result, ensure_ascii=False, indent=2), "cenario.json", "application/json")
    if c3.button("Preservar cenário local"):
        try:
            st.success(f"Cenário preservado em {service.export(result).folder}")
        except OSError as exc:
            st.error(str(exc))
    with st.expander("Limites da simulação"):
        for warning in result["warnings"]:
            st.write(warning)
    _measurements(service)
