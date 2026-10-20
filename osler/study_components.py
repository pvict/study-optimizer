"""Apresentação pura com conteúdo escapado; não cria dados nem altera o plano."""
from html import escape
import streamlit as st

STATE_LABELS={'dominado':'Dominado','aprendendo':'Aprendendo','alerta':'Em alerta'}


def block_heading(item):
    n=item['questions']
    st.html('<div class="study-block-heading"><h3>'+escape(item['path'][-1])+ '</h3>'
            f'<span class="study-dose">{n} '+('questão' if n==1 else 'questões')+'</span></div>')


def block_context(item):
    phase=item.get('learning_state')
    status=('<span class="study-status study-status-'+phase+'">'+STATE_LABELS[phase]+'</span>') if phase in STATE_LABELS else ''
    if item.get('status')=='sem_registro': status='<span class="study-status study-status-aprendendo">Novo tema</span>'
    st.html('<div class="study-block-meta">'+status+'<span>'+escape(item['stage'])+'</span></div>')
