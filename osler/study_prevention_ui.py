"""Das pendências laranja à comparação e a um plano preventivo reversível."""
from .ui_help import explain
from .action_feedback import confirm_button,confirm_submit,notify_success

from datetime import timedelta
import hashlib,json
import pandas as pd
import streamlit as st
from .planner_service import today_local
from .study_prevention import PREVENTION_MODES


def open_prevention(day):
    today=today_local()
    from .planning import _date
    selected=_date(day)
    st.session_state['prevention_enabled']=True
    st.session_state['calendar_selected']=day
    st.session_state['prevention_start']=max(today,selected-timedelta(days=13))
    st.session_state['prevention_days']=14
    st.session_state.pop('prevention_preview',None)


def render_prevention(service):
    if not st.toggle('Planejar pendências com antecedência',key='prevention_enabled'): return
    today=today_local()
    profile=service.store.profile()['profile']
    from .planning import _date
    latest=min(today+timedelta(days=547),_date(profile['exam_date']))
    if latest<today:
        st.info('Atualize a data da prova em Ajustes para planejar novas revisões.')
        return
    with st.container(border=True):
        st.subheader('Prevenir atrasos nas próximas semanas')
        explain('Compare antes de mudar a rotina. O cenário supõe execução dos blocos; datas e riscos serão recalculados com seus resultados.')
        left,right=st.columns(2)
        start=left.date_input('Analisar a partir de',value=today,min_value=today,max_value=latest,key='prevention_start',format='DD/MM/YYYY')
        days=right.number_input('Dias para analisar',1,90,14,key='prevention_days')
        token=service.agenda.token()
        cache_key=[token,start.isoformat(),int(days)]
        cache=st.session_state.get('prevention_context_cache',{})
        if cache.get('key')!=cache_key:
            with st.spinner('Conferindo as próximas revisões…'):
                cache={'key':cache_key,'context':service.prevention_context(start.isoformat(),int(days))}
                st.session_state['prevention_context_cache']=cache
        context=cache['context']
        st.caption(f"Janela: {context['start']} a {context['end']} · {len(context['candidates'])} temas com risco previsto.")
        if context['candidates']:
            mode=st.radio('Como abrir espaço?',list(PREVENTION_MODES),format_func=PREVENTION_MODES.get,key='prevention_mode')
            st.caption({'balanced':'Mantém sua carga e proporção. Prioriza os escolhidos quando a revisão estiver próxima e aproveita pequenas antecipações.',
                        'reviews':'Pausa novos apenas nessa janela para abrir vagas de revisão. O padrão retorna ao final.',
                        'extra':'Adiciona questões de revisão apenas nessa janela, preservando sua meta padrão.'}[mode])
            extra=st.number_input('Questões extras por dia nesta janela',1,300,20,step=5,key='prevention_extra') if mode=='extra' else 20
            all_selected=st.checkbox('Incluir todos os temas em risco',value=True,key='prevention_all')
            rows=context['candidates']
            frame=pd.DataFrame([{'Incluir':all_selected,'Tema específico':r['path'][-1],'Revisão prevista para':r['due_date'],
                                 'Sem vaga a partir de':r['first_pending']} for r in rows])
            signature=hashlib.sha256(json.dumps([cache_key,[r['topic_id'] for r in rows],all_selected]).encode()).hexdigest()[:12]
            edited=st.data_editor(frame,hide_index=True,width='stretch',key='prevention_topics_'+signature,
                                  disabled=['Tema específico','Revisão prevista para','Sem vaga a partir de'])
            selected=[r['topic_id'] for i,r in enumerate(rows) if edited.iloc[i]['Incluir']]
            option_key=hashlib.sha256(json.dumps([start.isoformat(),int(days),mode,selected,int(extra)]).encode()).hexdigest()
            if st.button('Comparar antes e depois',key='compare_prevention',disabled=not selected):
                with st.spinner('Redistribuindo e comparando os riscos…'):
                    preview=service.preview_prevention(start.isoformat(),int(days),mode,selected,int(extra))
                st.session_state['prevention_preview']={'options':option_key,'preview':preview}
            saved=st.session_state.get('prevention_preview',{})
            if saved.get('options')==option_key:
                preview=saved['preview']
                before,after=preview['before'],preview['after']
                a,b,c=st.columns(3)
                a.metric('Temas em risco',after['risk_topics'],after['risk_topics']-before['risk_topics'],delta_color='inverse')
                b.metric('Selecionados ainda em risco',preview['selected_after']['risk_topics'])
                c.metric('Questões programadas',after['planned_questions'],after['planned_questions']-before['planned_questions'])
                st.caption(f"Antes: {before['risk_topics']} temas em risco e {before['planned_questions']} questões programadas. Depois: {after['risk_topics']} temas em risco e {after['planned_questions']} questões. Tudo dentro da janela escolhida.")
                st.dataframe(pd.DataFrame([{'Tema específico':r['path'][-1],'Revisão prevista para':r['due_date'],
                                            'Sem vaga antes':r['before_first_pending'],
                                            'Após redistribuir':r['after_first_pending'] or 'Sem pendência na janela',
                                            'Próxima revisão com vaga':r['next_planned_review'] or 'Sem vaga'} for r in preview['comparison_rows']]),hide_index=True,width='stretch')
                if preview['new_risk_topics']:
                    st.warning(f"A redistribuição cria risco para {len(preview['new_risk_topics'])} outros temas. Confira antes de aplicar.")
                    st.dataframe(pd.DataFrame([{'Novo risco':r['path'][-1],'Sem vaga a partir de':r['first_pending']} for r in preview['new_risk_topics']]),hide_index=True,width='stretch')
                if preview['worsened_risk_topics']:
                    st.warning(f"{len(preview['worsened_risk_topics'])} temas que já estavam em risco passaram a aguardar mais ou a ficar sem vaga antes. Isso pode ocorrer mesmo com melhora no total.")
                    st.dataframe(pd.DataFrame([{'Tema com piora':r['path'][-1],'Dias com pendência antes':r['before_pending_days'],
                                                'Dias com pendência depois':r['pending_days'],'Maior atraso antes':r['before_max_delay_days'],
                                                'Maior atraso depois':r['max_delay_days']} for r in preview['worsened_risk_topics']]),hide_index=True,width='stretch')
                if after['risk_topics']: st.warning('Ainda há pendências previstas. Você pode mudar a estratégia, ampliar a janela ou ajustar a quantidade de temas por dia em Ajustes.')
                if after['late_topic_days']>before['late_topic_days']: st.warning('O total de pendências somadas nos dias aumentou. Alguns temas aguardariam mais tempo, mesmo que outros tenham melhorado.')
                explain('O primeiro contato continua no plano normal. Revisões podem ser antecipadas em 1–2 dias quando o intervalo permite; lotes de 7 dias aguardam seu retorno. Agendar não marca estudo como feito.')
                stale=preview['token']!=context['token']
                if stale: st.warning('Os dados mudaram. Compare novamente antes de aplicar.')
                if confirm_button('Aplicar plano preventivo',key='apply_prevention',type='primary',disabled=stale,action_key='study_prevention_ui_90'):
                    notify_success(service.apply_prevention(preview),'Agenda atualizada.')
                    st.session_state.pop('prevention_preview',None)
                    st.session_state.pop('prevention_context_cache',None)
                    st.session_state['adaptive_notice']='Plano preventivo aplicado. Os próximos blocos seguem a nova prioridade; seus resultados foram preservados.'
                    st.rerun()
        else: st.info('Nenhuma pendência prevista nessa janela. Você pode analisar outro período; não é necessário criar uma redistribuição agora.')
        active=[r for r in service.replanning()['active'] if r.get('scope')=='preventive']
        if active:
            last=active[-1]
            st.caption(f"Último plano preventivo: {last['start']} a {last['end']}. Desfazer preserva estudos e recuperações agendadas.")
            if confirm_button('Desfazer último plano preventivo',key='undo_prevention',action_key='study_prevention_ui_101'):
                notify_success(service.cancel_replan(last['id']),'Agenda atualizada.')
                st.session_state.pop('prevention_preview',None)
                st.session_state.pop('prevention_context_cache',None)
                st.session_state['adaptive_notice']='Plano preventivo desfeito. Seus resultados continuam no histórico.'
                st.rerun()
