"""Estilos compartilhados e fonte local; sem scripts ou recursos remotos."""
from pathlib import Path
import streamlit as st
from .bento import area_styles


def apply_study_style():
    folder=Path(__file__).parent
    css='\n'.join((folder/name).read_text(encoding='utf-8') for name in ('study.css','bento.css'))
    st.html('<style>'+css+'\n'+area_styles()+'</style>')
