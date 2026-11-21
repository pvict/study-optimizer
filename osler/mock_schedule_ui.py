"""Programação separada dos resultados, com datas independentes e prévia."""
from .action_feedback import confirm_button,confirm_submit,notify_success

from datetime import date,timedelta
import pandas as pd
import streamlit as st
from .planner_service import today_local


def _clear_preview():
    st.session_state.pop('mock_schedule_preview_data',None)


def _change_occurrence():
    _clear_preview(); st.session_state.pop('mock_occurrence_date',None); st.session_state.pop('mock_occurrence_name',None)


def _date_text(day):
    return date.fromisoformat(day).strftime('%d/%m/%Y') if day else 'Sem data'


def _scheduled_rows(service):
    """Agenda de consulta; não altera datas, resultados ou carga."""
    from .mock_exams import MockExams
    results={r['exam'].get('practice_id') for r in MockExams(service.repository).active() if r['exam'].get('practice_id')}
    rows=[]
    recorded=service.recorded_mock_days()
    for row in (service.mock_schedule() or {}).get('occurrences',[]):
        rows.append({'Data':row['date'] or row['original_date'],
                     'Simulado':row.get('name') or 'Nome não informado',
                     'Tipo':'Simulado completo','Área':'Todas as áreas',
                     'Situação':'Resultado registrado' if row['date'] in recorded else
                         {'reserved':'Programado','removed':'Retirado','blocked':'Não reservado'}.get(row['status'],row['status'])})
    for row in (service.area_schedule() or {}).get('occurrences',[]):
        rows.append({'Data':row.get('date') or row.get('original_date'),
                     'Simulado':row['institution'],'Tipo':'Treino por área','Área':row['area'],
                     'Situação':'Resultado registrado' if row.get('id') in results else 'Retirado' if not row.get('date') else
                         'Não reservado' if row.get('status')=='blocked' else 'Programado'})
    return sorted(rows,key=lambda row:(row['Data'] or '',row['Tipo'],row['Simulado']))


def render_mock_schedule(service):
    with st.container(key='bento-mock-schedule'):
        st.subheader('Agenda dos simulados')
        rows=_scheduled_rows(service)
        upcoming=[r for r in rows if r['Data'] and r['Data']>=today_local().isoformat()]
        if upcoming:
            st.dataframe(pd.DataFrame([{**r,'Data':_date_text(r['Data'])} for r in upcoming]),hide_index=True,width='stretch')
            st.caption('Simulados completos e treinos por área, em ordem de data. Nomes não cadastrados aparecem como Nome não informado.')
        else: st.info('Nenhum simulado ou treino por área programado de hoje em diante.')
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
                st.dataframe(pd.DataFrame([{'Data':r['date'],'Simulado':r.get('name') or 'Nome não informado','Tipo':'Simulado completo','Data original':r['original_date'],
                                           'Situação':'Resultado registrado' if r['date'] in recorded else {'reserved':'Programado','removed':'Retirado','blocked':'Não reservado: '+r.get('reason','conflito')}[r['status']]} for r in old['occurrences']]),hide_index=True,width='stretch')
            if future:
                lookup={r['occurrence_id']:r for r in future}
                chosen=st.selectbox('Qual simulado quer ajustar?',list(lookup),format_func=lambda k:_date_text(lookup[k]['date'])+' · '+(lookup[k].get('name') or 'Simulado completo')+' · originalmente '+_date_text(k),key='mock_occurrence',on_change=_change_occurrence)
                item=lookup[chosen]
                name=st.text_input('Nome deste simulado',value=item.get('name',''),max_chars=160,key='mock_occurrence_name',on_change=_clear_preview)
                new=st.date_input('Nova data deste simulado',value=max(current,min(limit,date.fromisoformat(item['date'] or chosen))),min_value=current,max_value=limit,
                                  format='DD/MM/YYYY',key='mock_occurrence_date',on_change=_clear_preview)
                if st.button('Ver prévia da mudança',key='mock_occurrence_preview'):
                    st.session_state['mock_schedule_preview_data']=service.preview_mock_move(chosen,new.isoformat(),name=name)
                if st.button('Retirar apenas este simulado',key='mock_occurrence_remove',disabled=item['date'] is None):
                    st.session_state['mock_schedule_preview_data']=service.preview_mock_move(chosen,None)
            with st.expander('Histórico e desfazer'):
                versions=[r for r in service.agenda.records() if r.get('scope')=='mock_schedule']
                st.caption(f'{len(versions)} versões preservadas. Desfazer restaura a programação anterior; resultados permanecem.')
                reason=service.mock_schedule_undo_reason(old['id'])
                if reason: st.caption(reason)
                if confirm_button('Desfazer última alteração dos simulados',key='mock_schedule_undo',disabled=bool(reason),action_key='mock_schedule_ui_56'):
                    notify_success(service.cancel_replan(old['id'],service.agenda.token()),'Agenda atualizada.'); _clear_preview()
                    st.session_state.pop('mock_occurrence',None); st.session_state.pop('mock_occurrence_date',None); st.session_state.pop('mock_occurrence_name',None); st.rerun()
    preview=st.session_state.get('mock_schedule_preview_data')
    if not preview: return
    with st.container(key='bento-mock-schedule-preview'):
        st.markdown('**Confira antes de aplicar**')
        if not old:
            st.dataframe(pd.DataFrame([{'Data':r['date'],'Situação':'Programado' if r['status']=='reserved' else r.get('reason','Retirado')}
                                       for r in preview['occurrences']]),hide_index=True,width='stretch',height=240)
        else:
            before={r['occurrence_id']:r for r in old['occurrences']}
            st.dataframe(pd.DataFrame([{'Antes':before[r['occurrence_id']]['date'],'Depois':r['date'] or 'Retirado','Simulado':r.get('name') or 'Nome não informado','Tipo':'Simulado completo'}
                                       for r in preview['occurrences'] if r['date']!=before[r['occurrence_id']]['date'] or r.get('name')!=before[r['occurrence_id']].get('name')]),hide_index=True,width='stretch')
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
        if confirm_button('Aplicar programação dos simulados',key='mock_schedule_apply',type='primary',disabled=stale,action_key='mock_schedule_ui_82'):
            notify_success(service.apply_mock_schedule(preview),'Agenda atualizada.'); _clear_preview()
            st.session_state.pop('mock_occurrence_date',None); st.session_state.pop('mock_occurrence_name',None); st.rerun()
