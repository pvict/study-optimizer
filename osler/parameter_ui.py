"""Troca manual explícita, sem calibração automática ou edição dos valores."""
import json
import pandas as pd
import streamlit as st
from .algorithm_parameters import ParameterStore


def render_parameter_settings(service):
    with st.expander('Parâmetros do algoritmo e análise de calibração'):
        store=ParameterStore(service.repository); current=store.current(); versions=store.versions()
        current=st.session_state.setdefault('parameter_selection_snapshot',current)
        if st.button('Recarregar seleção de parâmetros',key='parameter_reload'):
            st.session_state.pop('parameter_selection_snapshot',None)
            st.session_state.pop('parameter_version',None); st.rerun()
        st.write(f"Versão de parâmetros em uso: {current['parameters'].version} · sem calibração pessoal.")
        st.caption('A versão 1 preserva os valores anteriores. Nenhum ajuste é feito automaticamente; só versões cadastradas podem ser escolhidas.')
        with st.form('parameter_selection'):
            options=[v['version'] for v in versions]
            chosen=st.selectbox('Versão cadastrada',options,index=options.index(current['parameters'].version),key='parameter_version')
            apply=st.form_submit_button('Usar esta versão manualmente',disabled=chosen==current['parameters'].version)
        if apply:
            store.select(chosen,current['id']); st.session_state.pop('parameter_selection_snapshot',None); st.success('Versão selecionada; histórico preservado.'); st.rerun()
        with st.expander('Valores e histórico das seleções'):
            st.json(current['parameters'].to_dict())
            if store.history(): st.dataframe(pd.DataFrame(store.history()),hide_index=True,width='stretch')
        st.caption('Use o app diariamente por 6 a 8 semanas antes de analisar calibração. O relatório descreve amostras, repetições, convicção, tempo e aderência; não altera os parâmetros.')
        st.code('python scripts/analise_calibracao.py --output analises/calibracao',language='text')
