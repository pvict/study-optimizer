"""Estilos locais compartilhados; sem fontes, scripts ou recursos externos."""
from pathlib import Path
import streamlit as st


def apply_study_style():
    css=Path(__file__).with_name('study.css').read_text(encoding='utf-8')
    st.html('<style>'+css+'</style>')
