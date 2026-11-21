"""Entrada da hospedagem. O app.py e o inicializador local continuam locais."""
import os

os.environ['OSLER_CLOUD'] = '1'

import streamlit as st
from osler.cloud_ui import protected_run

st.set_page_config(page_title='Osler · Meu estudo',layout='wide')


def open_app():
    from osler.ui import run
    run()


protected_run(open_app)
