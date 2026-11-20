"""Troca manual explícita, sem calibração automática ou edição dos valores."""
from .action_feedback import confirm_button,confirm_submit,notify_success

import sqlite3
import pandas as pd
import streamlit as st
from .algorithm_parameters import ParameterStore
from .calibration_analysis import analyze_database
from .planner_service import today_local
from .ui_help import explain


def _render_calibration(db_path):
    if not st.button('Ver acerto por intervalo',key='parameter_show_calibration'):
        return
    with st.spinner('Lendo histórico de revisões…'):
        try:
            report=analyze_database(db_path,today_local().isoformat())
        except (OSError,sqlite3.Error,ValueError):
            st.error('Falha ao ler o histórico de estudos para a análise.')
            return
    rows=[{'De (dias)':r['lag_min_days'],'Até (dias)':r['lag_max_days'],
           'Acerto (%)':r['value'],'Acertos':r['correct'],'Questões':r['n_attempts'],
           'Sessões':r['n_sessions'],'Tema/dias':r['n_topicdays'],
           'Amostra':'Pequena' if r['warning']=='Dados insuficientes' else 'Descritiva',
           'Acerto inicial':r['initial_band'],'Origem':r['mode'].capitalize(),
           'Vínculo':'Explícito' if r['linkage']=='review_of' else 'Por tema',
           'Faixa Wilson (95%)':f"{r['wilson_low_pct']:.1f}–{r['wilson_high_pct']:.1f}%".replace('.',','),
          }
          for r in report['rows'] if r['measurement']=='repeat_accuracy' and r['n_sessions']]
    if not rows:
        st.info('Nenhuma revisão repetida elegível nas faixas de 2 a 35 dias.')
        return
    counts=report['repeat_pair_counts']
    st.caption(f"{counts['included']} de {counts['matched']} pares de estudo e revisão entraram nas faixas.")
    st.dataframe(rows,hide_index=True,width='stretch',column_config={
        'Acerto (%)':st.column_config.NumberColumn(format='%.1f%%'),
        'Tema/dias':st.column_config.NumberColumn(help='Número de combinações distintas de tema e dia.'),
    })
    st.caption('O desempenho anterior influencia a data agendada. As diferenças entre faixas descrevem o histórico.')
    explain('As faixas incluem os dois limites. Amostra pequena indica menos de 30 questões ou menos de cinco combinações de tema e dia. Vínculo por tema associa a revisão ao bloco anterior mais próximo.')


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
            apply=confirm_submit('Usar esta versão manualmente',disabled=chosen==current['parameters'].version,action_key='parameter_ui_20')
        if apply:
            notify_success(store.select(chosen,current['id']),'Alterações salvas.'); st.session_state.pop('parameter_selection_snapshot',None); st.success('Versão selecionada; histórico preservado.'); st.rerun()
        with st.expander('Valores e histórico das seleções'):
            st.json(current['parameters'].to_dict())
            if store.history(): st.dataframe(pd.DataFrame(store.history()),hide_index=True,width='stretch')
        _render_calibration(service.repository.db_path)
        with st.expander('Exportar relatório pelo terminal'):
            st.caption('O relatório completo inclui repetições, convicção, tempo e aderência.')
            st.code('python scripts/analise_calibracao.py --output analises/calibracao',language='text')
