"""Um resumo de capacidade, com custo de cobertura e risco residual visíveis."""
from .ui_help import explain
from .action_feedback import confirm_button,confirm_submit,notify_success

import streamlit as st
import pandas as pd


def render_capacity_summary(service,start):
    from .planner_service import today_local
    from .planning import _date
    profile=service.store.profile()['profile']
    if start>profile['exam_date'] or (_date(start)-today_local()).days>547: return
    key=[service.agenda.token(),start,14]
    cached=st.session_state.get('capacity_comparison',{})
    if cached.get('key')!=key:
        cached={'key':key,'comparison':service.workload_comparison(start,14)}
        st.session_state['capacity_comparison']=cached
    comparison=cached['comparison']; before=comparison['fixed']; after=comparison['adaptive']
    active=comparison['mode']=='adaptive'
    with st.container(border=True):
        st.subheader('Equilíbrio dos próximos '+str(comparison['days'])+' dias')
        st.caption(comparison['start']+' a '+comparison['end']+' · mesma carga diária nos dois cenários')
        st.write(f"Revisões com risco: **{before['risk_topics']} na divisão fixa → {after['risk_topics']} com ajuste automático**.")
        if active:
            st.caption('Ajuste automático ativo · sua proporção escolhida é a referência; novos temas cedem espaço às revisões quando necessário.')
        else:
            explain('Proposta: ajustar a entrada de temas à capacidade de repetir, preservando a carga e os resultados registrados.')
            if confirm_button('Ativar ajuste automático',key='activate_capacity',type='primary',action_key='study_capacity_ui_26'):
                notify_success(service.configure_workload('adaptive',comparison['profile_id']),'Alterações salvas.')
                st.session_state.pop('capacity_comparison',None)
                st.session_state['adaptive_notice']='Ajuste automático ativado. Sua carga e a proporção de referência foram preservadas.'
                st.rerun()
        st.caption(f"Temas novos na janela: {before['new_topics']} na divisão fixa e {after['new_topics']} no ajuste automático. Menos entradas liberam espaço para consolidar o que já foi visto.")
        if after['risk_topics']: st.warning('Ainda há revisões sem espaço neste cenário. Confira os dias e use Redistribuir antes de atrasar; não aumentamos sua carga automaticamente.')
        if after['new_topics']==0 and comparison['reference_share']>0: st.info('Sem novos temas nesta janela do cenário adaptativo. Os resultados reais podem liberar capacidade; confira a cobertura dos temas antes de manter essa rotina por muito tempo.')
        with st.expander('Ver comparação e limites'):
            st.dataframe(pd.DataFrame([{'Rotina':label,'Revisões em risco':r['risk_topics'],'Questões programadas':r['planned_questions'],
                                        'Questões em temas novos':r['new_questions'],'Temas novos':r['new_topics'],
                                        'Dias com menos novos':r['adjusted_days']} for label,r in [('Fixa',before),('Adaptativa',after)]]),hide_index=True,width='stretch')
            st.caption('A previsão mantém os intervalos atuais e não presume melhora. Menos temas novos pode atrasar a cobertura; o plano será recalculado com seus resultados. A meta é um limite de carga: blocos não são inflados apenas para preencher questões.')
            st.caption('O modo fixo permanece disponível em Ajustes. Retornos identificados de questões erradas continuam em7dias, separados da revisão completa do tema.')
