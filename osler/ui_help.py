"""Orientação opcional; métricas, validações e avisos não passam por este helper."""
import streamlit as st


def explain(text):
    if st.session_state.get('show_explanations',False):
        st.caption(text)
