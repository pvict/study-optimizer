"""Programação separada dos resultados, com datas independentes e prévia."""
from datetime import date,timedelta
import pandas as pd
import streamlit as st
from .planner_service import today_local


def _clear_preview():
    st.session_state.pop('mock_schedule_preview_data',None)


def _change_occurrence():
    _clear_preview(); st.session_state.pop('mock_occurrence_date',None)


def _date_text(day):
    return date.fromisoformat(day).strftime('%d/%m/%Y') if day else 'Sem data'


def render_mock_schedule(service):
    with st.container(key='bento-mock-schedule'):
        st.subheader('Datas dos simulados')
        st.caption('No dia de simulado os blocos normais são dispensados. Os próximos contatos são redistribuídos dentro da carga dos outros dias; o resultado é registrado separadamente.')
        current=today_local(); old=service.mock_schedule(); profile=service.store.profile()['profile']; recorded=service.recorded_mock_days()
        limit=min(date.fromisoformat(profile['exam_date']),current+timedelta(days=547))
        if limit<current: st.info('Confira a data da prova em Ajustes antes de programar simulados.'); return
        if not old:
            first=st.date_input('Primeiro simulado',value=min(limit,current+timedelta(days=profile['mock_cadence_days'] or 7)),min_value=current,max_value=limit,
                                format='DD/MM/YYYY',key='mock_schedule_first',on_change=_clear_preview)
            interval=st.number_input('Sugerir os seguintes a cada quantos dias?',1,365,profile['mock_cadence_days'] or 7,key='mock_schedule_interval',on_change=_clear_preview)
            if st.button('Ver datas e remanejamento',key='mock_schedule_preview',type='primary'):
                st.session_state['mock_schedule_preview_data']=service.preview_mock_schedule(first.isoformat(),int(interval))
        else:
            future=[r for r in old['occurrences'] if (r['date'] or r['occurrence_id'])>=current.isoformat() and r['date'] not in recorded]
            actual=[r for r in future if r['status']=='reserved']
            st.write('Próximo simulado: **'+_date_text(min((r['date'] for r in actual),default=None))+'**')
            st.caption(f"Intervalo inicial de {old['request']['interval']} dias, até {_date_text(old['request']['end'])}. Mudar uma ocorrência mantém as outras datas.")
            with st.expander('Ver todas as datas programadas'):
                st.dataframe(pd.DataFrame([{'Data':r['date'],'Data original':r['original_date'],
                                           'Situação':'Resultado registrado' if r['date'] in recorded else {'reserved':'Programado','removed':'Retirado','blocked':'Não reservado: '+r.get('reason','conflito')}[r['status']]} for r in old['occurrences']]),hide_index=True,width='stretch')
            if future:
                lookup={r['occurrence_id']:r for r in future}
                chosen=st.selectbox('Qual simulado quer ajustar?',list(lookup),format_func=lambda k:_date_text(lookup[k]['date'])+' · originalmente '+_date_text(k),key='mock_occurrence',on_change=_change_occurrence)
                item=lookup[chosen]
                new=st.date_input('Nova data deste simulado',value=max(current,min(limit,date.fromisoformat(item['date'] or chosen))),min_value=current,max_value=limit,
                                  format='DD/MM/YYYY',key='mock_occurrence_date',on_change=_clear_preview)
                if st.button('Ver prévia da mudança',key='mock_occurrence_preview'):
                    st.session_state['mock_schedule_preview_data']=service.preview_mock_move(chosen,new.isoformat())
                if st.button('Retirar apenas este simulado',key='mock_occurrence_remove',disabled=item['date'] is None):
                    st.session_state['mock_schedule_preview_data']=service.preview_mock_move(chosen,None)
            with st.expander('Histórico e desfazer'):
                versions=[r for r in service.agenda.records() if r.get('scope')=='mock_schedule']
                st.caption(f'{len(versions)} versões preservadas. Desfazer restaura a programação anterior; resultados permanecem.')
                reason=service.mock_schedule_undo_reason(old['id'])
                if reason: st.caption(reason)
                if st.button('Desfazer última alteração dos simulados',key='mock_schedule_undo',disabled=bool(reason)):
                    service.cancel_replan(old['id'],service.agenda.token()); _clear_preview()
                    st.session_state.pop('mock_occurrence',None); st.session_state.pop('mock_occurrence_date',None); st.rerun()
    preview=st.session_state.get('mock_schedule_preview_data')
    if not preview: return
    with st.container(key='bento-mock-schedule-preview'):
        st.markdown('**Confira antes de aplicar**')
        if not old:
            st.dataframe(pd.DataFrame([{'Data':r['date'],'Situação':'Programado' if r['status']=='reserved' else r.get('reason','Retirado')}
                                       for r in preview['occurrences']]),hide_index=True,width='stretch',height=240)
        else:
            before={r['occurrence_id']:r for r in old['occurrences']}
            st.dataframe(pd.DataFrame([{'Antes':before[r['occurrence_id']]['date'],'Depois':r['date'] or 'Retirado'}
                                       for r in preview['occurrences'] if r['date']!=before[r['occurrence_id']]['date']]),hide_index=True,width='stretch')
        st.caption(f"Remanejamento comparado de {_date_text(preview['window_start'])} a {_date_text(preview['window_end'])}. A série inteira reserva capacidade; as datas abaixo são previsões de próximos contatos e serão recalculadas após seus resultados.")
        changes=preview['topic_changes']
        if preview.get('area_conflicts'):
            st.warning('Treinos por área coincidem com os simulados completos abaixo. O dia exclusivo tem prioridade; mova esses treinos na aba Treinos por área. Eles não somarão carga ao dia do simulado.')
            st.dataframe(pd.DataFrame([{'Data':r['date'],'Instituição':r['institution'],'Área':r['area']} for r in preview['area_conflicts']]),hide_index=True,width='stretch')
        if changes:
            st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Antes':r['before_date'],'Depois':r['after_date'] or 'Sem vaga neste horizonte',
                                       'Questões previstas':r['after_questions'],'Prioridade':r['priority']} for r in changes]),hide_index=True,width='stretch',height=280)
        else: st.caption('Nenhum próximo contato com data alterada neste horizonte. Nenhum estudo será marcado como feito.')
        if preview['unassigned']: st.warning(f"{len(preview['unassigned'])} temas perderam a vaga neste horizonte. Continuam na fila; a mudança não aumenta sua meta automaticamente.")
        stale=preview['token']!=service.agenda.token()
        if stale: st.info('Os dados mudaram. Monte uma nova prévia antes de aplicar.')
        if st.button('Aplicar programação dos simulados',key='mock_schedule_apply',type='primary',disabled=stale):
            service.apply_mock_schedule(preview); _clear_preview()
            st.session_state.pop('mock_occurrence_date',None); st.rerun()
