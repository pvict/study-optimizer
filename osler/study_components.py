"""Apresentação pura com conteúdo escapado; não cria dados nem altera o plano."""
from html import escape
import streamlit as st
from .ui_help import explain

STATE_LABELS={'dominado':'Dominado','aprendendo':'Aprendendo','alerta':'Em alerta'}


def render_bank_scope(item,minimum):
    if 0<item['total']<minimum:
        recommended=item.get('questions',item.get('recommended_questions',item['total']))
        if recommended>item['total']:
            st.info(f"Bloco indicado: {recommended} questões. Acervo importado: {item['total']}. Busque as questões complementares no banco completo da plataforma.")
        else:st.caption(f"Acervo: {item['total']} "+('questão disponível' if item['total']==1 else 'questões disponíveis')+'.')
        explain('O tema recebe vaga mesmo abaixo do bloco mínimo; essa amostra não comprova domínio.')
    if item.get('partial_subdivision'):
        st.caption('Tema com subtemas · registro apenas neste tema.')
        explain('Não some as contagens entre o tema completo e seus subtemas.')


def render_planner_supply(item):
    supply=item.get('planner_supply')
    if not supply: return
    date='/'.join(reversed(supply['observed_date'].split('-')))
    explain(f"Revisão recomendada: {supply['recommended']} questões · Planner: {supply['planner_total']} no retrato de {date}.")
    if supply['external_part']:
        st.info(f"Planner: {supply['planner_total']} de {supply['recommended']} questões. "
                f"Busque {supply['external_remaining']} para complementar no banco completo.")
        explain(f"Já registradas: {supply['completed']} de {supply['recommended']}. A falta de questões no Planner não conta como atraso seu.")


def block_heading(item):
    n=item['questions']
    st.html('<div class="study-block-heading"><h3>'+escape(item['path'][-1])+ '</h3>'
            f'<span class="study-dose">{n} '+('questão' if n==1 else 'questões')+'</span></div>')


def block_context(item):
    phase=item.get('learning_state')
    status=('<span class="study-status study-status-'+phase+'">'+STATE_LABELS[phase]+'</span>') if phase in STATE_LABELS else ''
    if item.get('status')=='sem_registro': status='<span class="study-status study-status-aprendendo">Novo tema</span>'
    st.html('<div class="study-block-meta">'+status+'<span>'+escape(item['stage'])+'</span></div>')
