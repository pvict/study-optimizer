"""Estratégia em detalhes, com impacto visível antes de aplicar."""
import pandas as pd
import streamlit as st
from .balanced_reviews import STRATEGIES


def _show(preview):
    before,after=preview['before'],preview['after']
    st.write('**Confira as mudanças**')
    st.write(f"Meta padrão: {before['max_questions']} → {after['max_questions']} questões/dia. Meta de hoje: {before['today_target']} → {after['today_target']}. Blocos restantes: {before['today_questions']} → {after['today_questions']} questões. Resultados, instituições, metas por área e simulados serão preservados.")
    a={r['topic_id']:r for r in before['today']}; b={r['topic_id']:r for r in after['today']}
    st.dataframe(pd.DataFrame([{'Tema':(b.get(k) or a[k])['path'][-1],
        'Questões antes':a.get(k,{}).get('questions',0),'Questões depois':b.get(k,{}).get('questions',0)} for k in dict.fromkeys([*a,*b])]),hide_index=True,width='stretch')
    with st.expander('Doses, intervalos, prioridades e datas'):
        st.caption('Todos os temas cujo cálculo muda. Datas devidas não são garantia de vaga.')
        st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],
            'Questões antes':r['before']['theme_recommended_questions'],'Questões depois':r['after']['theme_recommended_questions'],
            'Intervalo antes (dias)':r['before']['review_interval_days'],'Intervalo depois (dias)':r['after']['review_interval_days'],
            'Devida antes':r['before']['theme_review_due'],'Devida depois':r['after']['theme_review_due'],
            'Prioridade antes':r['before']['priority'],'Prioridade depois':r['after']['priority'],
            'Estado antes':r['before']['learning_state'],'Estado depois':r['after']['learning_state']} for r in preview['state_changes']]),hide_index=True,width='stretch')
        st.caption('Próximos contatos comparados até '+preview['window_end']+'. Depois dessa janela, os cálculos também seguirão a estratégia escolhida.')
        st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Antes':r['before_date'] or 'Sem vaga na janela',
            'Depois':r['after_date'] or 'Sem vaga na janela','Questões antes':r['questions'],'Questões depois':r['after_questions']} for r in preview['contacts']]),hide_index=True,width='stretch')


def render_review_strategy(service):
    record=service.store.profile(); current=record['configured_profile']['review_strategy']
    with st.expander('Como o app calcula as revisões'):
        st.write('Estratégia atual: '+STRATEGIES[current]+'. Acertos e amostra orientam doses e intervalos. A convicção mantém seus retornos específicos. As regras precisam de validação com seu histórico.')
        selected=st.radio('Estratégia de revisão',list(STRATEGIES),index=list(STRATEGIES).index(current),
            format_func=STRATEGIES.get,key='review_strategy_'+str(record['id']))
        if st.button('Ver prévia da estratégia',key='review_strategy_preview',disabled=selected==current):
            try: st.session_state['review_strategy_preview_data']=service.preview_review_strategy(selected)
            except ValueError as exc: st.error(str(exc))
        preview=st.session_state.get('review_strategy_preview_data')
        if preview and preview['strategy']==selected and preview['profile_id']==record['id']:
            _show(preview); stale=preview['token']!=service.agenda.token()
            if stale: st.info('Os dados mudaram. Recalcule a prévia antes de aplicar.')
            if st.button('Aplicar estratégia',type='primary',key='review_strategy_apply',disabled=stale or selected==current):
                try: service.apply_review_strategy(preview)
                except ValueError as exc: st.error(str(exc)); return
                st.session_state.pop('review_strategy_preview_data',None)
                st.session_state.pop('adaptive_profile_snapshot',None)
                st.session_state['adaptive_notice']='Estratégia de revisão atualizada conforme a prévia. Resultados preservados.'
                st.rerun()
        history=service.review_strategy_history()
        if history:
            with st.expander('Última alteração aplicada'):
                _show(history[-1]['preview'])
                st.caption('Para voltar à anterior, selecione-a acima e confira uma nova prévia. Isso preserva ajustes feitos depois.')
