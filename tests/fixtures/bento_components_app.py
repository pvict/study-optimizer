"""Prévia visual de primitivas; dados sintéticos, sem Repository ou gravação."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import streamlit as st
from osler.study_style import apply_study_style
from osler.bento import eyebrow,chip,ring,bar

st.set_page_config(page_title='Componentes Bento — teste sintético',layout='wide')
apply_study_style()
st.title('Componentes — cenário sintético')
st.caption('Prévia de teste. Nenhum dado ou estudo do usuário.')
with st.container(key='bento-hero-cirurgia'):
    st.html(eyebrow('Clínica Cirúrgica · 20 questões','cirurgia'))
    st.html('<h3 class="o-title">Cicatrização e Avaliação de Feridas</h3>')
    st.html(chip('',state='alerta')+' '+chip('',state='aprendendo'))
    st.html(bar(.7,'cirurgia',target=.9,label='14 acertos em20 questões sintéticas'))
    st.button('Registrar este bloco',type='primary',icon=':material/edit_note:')
with st.container(key='bento-progress'):
    # st.html1.66 sanitiza SVG; o renderer Markdown nativo aceita SVG estático.
    st.markdown(ring(40,60),unsafe_allow_html=True)
    st.html(bar(None,label='Acerto desconhecido'))
