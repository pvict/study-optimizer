"""Um roteiro de estudo em linguagem cotidiana, sem formulário por assunto."""
from .action_feedback import confirm_button,confirm_submit,notify_success

from datetime import date
import sqlite3

import pandas as pd
import streamlit as st

from .guide_service import GuideService
from .planner_service import today_local


def time_label(minutes):
    hours, rest = divmod(minutes, 60)
    return f"{hours}h{rest:02d}" if hours and rest else f"{hours}h" if hours else f"{rest} min"


def _open_reduction():
    st.session_state["main_view"] = "Ferramentas"
    st.session_state["advanced_view"] = "Planejador de Suspensões"


def render_today(repo):
    service = GuideService(repo)
    settings = service.settings()["settings"]
    st.title("Vamos cuidar do estudo de hoje")
    st.write("Questões primeiro. Entenda os erros. Use flashcards em uma revisão curta.")
    if "guide_notice" in st.session_state:
        st.success(st.session_state.pop("guide_notice"))
    left, right = st.columns([1.2, 1])
    kind = left.radio("Como está o dia?", ["normal", "plantao", "descanso"], format_func={"normal": "Dia normal", "plantao": "Plantão ou cansaço", "descanso": "Descanso"}.get, horizontal=True, key="guide_kind")
    options = sorted({15, 30, 45, 60, 90, 120, 180, 240, 300, 360, settings["normal_minutes"], settings["shift_minutes"]})
    default = settings["shift_minutes"] if kind == "plantao" else settings["normal_minutes"]
    minutes = right.select_slider("Quanto tempo você tem hoje?", options, value=default, format_func=time_label, key=f"guide_minutes_{kind}")
    result = service.guide(today_local().isoformat(), minutes, kind)
    if kind == "descanso":
        st.info("Hoje é descanso. Amanhã o roteiro recomeça, sem acrescentar uma dívida ao seu dia.")
        if confirm_button("Registrar meu descanso",action_key='guided_ui_37'):
            notify_success(service.save_day(result["date"], "descanso", []),'Alterações salvas.')
            st.session_state["guide_notice"] = "Descanso registrado. Seu próximo dia continua leve."
            st.rerun()
        return
    if kind == "plantao":
        st.caption("Usei um roteiro mínimo de até 45 minutos. Fazer uma parte já conta como um dia possível.")
    topics = result["topics"]
    if topics:
        chosen = st.session_state.get("guide_topic_choice")
        focus = next((i for i in topics if i["topic_id"] == chosen), topics[0])
        with st.container(border=True):
            st.caption("ASSUNTO PARA COMEÇAR")
            st.text(focus["name"])
            st.text(focus["reason"])
            st.caption(" → ".join(focus["path"]))
            for source in focus["incidence"]:
                qualifier = "Neste tema" if source["exact"] else "No tema maior desta mesma área"
                label = source.get("native_incidence") or "Frequência da tabela recebida"
                st.text(f"{qualifier}: {source['value']} {'questões' if source['unit'] == 'questoes' else '%'} · {label}.")
            if len(topics) > 1:
                with st.expander("Prefiro estudar outro assunto hoje"):
                    for topic in topics:
                        if st.button(topic["name"], key=f"choose_{topic['topic_id']}"):
                            st.session_state["guide_topic_choice"] = topic["topic_id"]
                            st.rerun()
    else:
        focus = None
        st.info("O roteiro já funciona. Para escolher assuntos a partir dos seus dados, carregue um relatório de questões em Ferramentas → Dados e classificação.")
    st.subheader("Seu roteiro")
    descriptions = {"questoes": "Abra um bloco de questões na Osler. Tente responder antes de ler o comentário. Pare no tempo combinado; o número de questões pode variar.",
                    "erros": "Retome o que errou ou acertou por dúvida. Escreva a ideia que faltou e procure poucos cartões desses conceitos.",
                    "gerais": "Faça uma seleção curta. Não tente esvaziar toda a fila; preserve tempo para as questões e os erros.",
                    "pausa": "Distribua esse tempo entre os blocos. Levante, beba água e volte sem pressa."}
    for index, block in enumerate(result["blocks"], 1):
        with st.container(border=True):
            st.write(f"**{index}. {block['title']} · {time_label(block['minutes'])}**")
            st.write(descriptions[block["kind"]])
    st.caption("Este é um ponto de partida ajustável. Você pode parar antes; o app não empurra o que ficou para amanhã.")
    with st.expander("Quer registrar como foi o assunto? É opcional"):
        feedback = st.selectbox("Como você se sentiu nas questões?", ["nao_registrei", "dificil", "tranquilo"], format_func={"nao_registrei": "Prefiro não registrar", "dificil": "Ainda estou errando ou ficando em dúvida", "tranquilo": "Consegui explicar bem as respostas"}.get, key="guide_feedback")
    c1, c2 = st.columns(2)
    done = confirm_button("Terminei por hoje", type="primary",action_key='guided_ui_79',container=c1)
    partial = confirm_button("Consegui fazer uma parte",action_key='guided_ui_80',container=c2)
    if done or partial:
        try:
            notify_success(service.save_day(result["date"], "feito" if done else "parcial", focus["path"] if focus else [], feedback),'Alterações salvas.')
            st.session_state["guide_notice"] = "Dia registrado. Amanhã você recebe um novo ponto de partida, sem compensações automáticas."
            st.rerun()
        except (ValueError, sqlite3.Error) as exc:
            st.error(str(exc))
    if result["has_incidence"]:
        st.caption("A escolha dos assuntos considera a tabela das instituições que você trouxe. Ela orienta a prática; não mede domínio nem determina suspensão.")


def render_path(repo):
    service = GuideService(repo)
    result = service.guide(today_local().isoformat())
    st.title("Seu caminho até novembro de 2027")
    st.write("A ideia é ganhar desempenho nas provas sem transformar a revisão em um segundo trabalho.")
    if result["settings"]["institutions"]:
        st.text("Provas em foco: " + ", ".join(result["settings"]["institutions"]))
    elif result["has_incidence"]:
        st.caption("O guia usa o conjunto de instituições da tabela enviada. Ao informar os nomes em Ajustar meu plano, confira se a tabela corresponde às mesmas provas.")
    else:
        st.caption("Você pode acrescentar as provas e uma tabela de incidência em Ajustar meu plano quando quiser.")
    for phase in result["phases"]:
        with st.container(border=True):
            current = phase["start"] <= result["date"] <= phase["end"]
            st.subheader(("Agora · " if current else "")+phase["title"])
            a, b = date.fromisoformat(phase["start"]), date.fromisoformat(phase["end"])
            st.caption(f"{a:%d/%m/%Y} a {b:%d/%m/%Y}")
            st.write(phase["action"])
    st.caption("As fases são um roteiro inicial. As datas serão ajustadas quando houver o calendário oficial das suas provas; não são datas de edital nem garantia de aprovação.")
    st.subheader("O que vale conferir nesta semana")
    st.write("• Você conseguiu fazer questões com correção?\n\n• Quais erros apareceram de novo?\n\n• Os flashcards couberam no tempo curto reservado?\n\n• Há espaço para um bloco de prova anterior?")
    days = service.days()
    if days:
        st.subheader("Seus últimos registros")
        labels = {"feito": "Estudei", "parcial": "Fiz uma parte", "descanso": "Descansei"}
        st.dataframe(pd.DataFrame([{"Dia": d["day"], "Como foi": labels[d["status"]], "Assunto": d["path"][-1] if d["path"] else "—"} for d in days[:14]]), hide_index=True, width="stretch")
    with st.expander("E a redução dos flashcards?"):
        st.write("O foco é liberar tempo sem abandonar conceitos frágeis. A tabela de incidência ajuda a escolher o que praticar, mas sozinha não mostra que você domina um assunto.")
        st.write("O caso de feridas continua disponível no planejador para avaliar redução seletiva. Você pode usar o guia diário sem preencher novos subtemas.")
        st.button("Ver meus temas para redução", on_click=_open_reduction)
    with st.expander("Por que esse roteiro?"):
        st.write("Questões com correção e revisão espaçada ajudam a aprender e reter. Os tempos e fases deste app são propostas ajustáveis ao seu dia.")
        st.markdown("[Revisão sobre prática de recuperação e espaçamento na educação em saúde](https://pubmed.ncbi.nlm.nih.gov/37615780/)")
