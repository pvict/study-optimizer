"""Retomada em Hoje: datas reais, primeiras vagas e gravação auditável."""
from html import escape
import streamlit as st
from .action_feedback import confirm_button,notify_success
from .study_replanning import backlog_schedule,MODES
from .study_navigation_ui import go_view


def _advanced():
    st.session_state['calendar_reorganize_open']=True
    go_view('Plano de questões','Calendário')


def _date(value):
    return '/'.join(reversed(value.split('-'))) if value else '—'


def render_today_replanning(service,view):
    context=service.replanning(view['date'],view=view)
    rows=backlog_schedule(context['backlog'],context['rows'],view['date'])
    waiting=[r for r in view['agenda'].get('area_practice',[]) if r.get('status')=='waiting']
    if not rows and not waiting:
        st.session_state.pop('today_replan_preview_data',None)
        return
    pending=[r for r in rows if not r['recovery_current']]
    with st.container(key='bento-today-recovery'):
        st.subheader('Atrasos e próximas datas')
        st.html('<dl class="o-recovery-counts">'+''.join(
            '<div><dt>'+escape(label)+'</dt><dd>'+str(n)+'</dd></div>'
            for label,n in [('Temas atrasados',len(rows)),('Com data atual',len(rows)-len(pending)),('Precisam de data',len(pending))])+'</dl>')
        st.caption('Reagendar reserva uma vaga dentro da carga. O atraso só se encerra com o estudo registrado.')
        if rows:
            selected=[r['topic_id'] for r in (pending or rows)]
            label=f'Encontrar datas para {len(pending)} tema(s)' if pending else 'Rever distribuição dos temas'
            if not pending:st.caption('Todos os temas acima já têm uma reserva para hoje ou depois. Redistribuir é opcional.')
            if st.button(label,key='today_replan_preview',icon=':material/event_repeat:'):
                try:
                    preview=service.preview_replan(view['date'],90,'balanced',selected=selected,extra_questions=0)
                    st.session_state['today_replan_preview_data']=preview
                except ValueError as exc:
                    st.error(str(exc))
            with st.expander('Ver temas e datas'):
                st.dataframe([{'Tema':' › '.join(r['path']),'Atraso desde':_date(r['original_due']),
                               'Recuperação':_date(r['recovery_date']),'Situação':r['recovery_status'],
                               'Questões':r['questions']} for r in rows],hide_index=True,width='stretch')
            preview=st.session_state.get('today_replan_preview_data')
            if preview:
                stale=preview['token']!=context['token'] or preview['created_day']!=view['date']
                st.markdown('**Confira as novas datas**')
                st.caption('Primeiras vagas nos próximos 90 dias, até a prova. Mantém a meta e a divisão atuais; preserva reservas dos temas não selecionados, descansos e simulados. Não altera os flashcards da Osler.')
                if preview['rows']:
                    st.dataframe([{'Tema':' › '.join(r['path']),'Nova data':_date(r['date']),
                                   'Questões':r['questions']} for r in preview['rows']],hide_index=True,width='stretch')
                if preview['unassigned']:
                    st.warning(f"{len(preview['unassigned'])} tema(s) não couberam. Continuarão sem nova data ao aplicar; reservas anteriores desses temas serão substituídas.")
                    st.dataframe([{'Tema':' › '.join(r['path']),'Questões':r['questions'],'Motivo':r['reason']}
                                  for r in preview['unassigned']],hide_index=True,width='stretch')
                if stale:st.warning('Os dados mudaram. Encontre as datas novamente antes de aplicar.')
                if confirm_button('Aplicar estas datas',key='today_replan_apply',disabled=stale or not preview['rows'],action_key='today_replan_apply'):
                    try:
                        notify_success(service.apply_replan(preview),'Novas datas salvas.')
                        st.session_state.pop('today_replan_preview_data',None)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                if st.button('Descartar prévia',key='today_replan_discard'):
                    st.session_state.pop('today_replan_preview_data',None)
                    st.rerun()
        if waiting:
            st.warning(f'{len(waiting)} treino(s) por área sem vaga. Eles têm uma agenda separada dos temas acima.')
            from .bento_day_ui import _reschedule_area
            st.button('Reagendar treinos por área',key='today_replan_area',on_click=_reschedule_area)
        with st.expander('Outras opções de reagendamento'):
            st.button('Escolher temas, datas ou estratégia',key='today_replan_advanced',on_click=_advanced)
            recoveries=[r for r in context['active'] if r.get('mode') in MODES and 'start' in r and 'days' in r]
            if recoveries:
                last=recoveries[-1]
                st.caption('Último reagendamento: '+_date(last['start'])+'. Desfazer preserva os resultados registrados.')
                if confirm_button('Desfazer último reagendamento',key='today_replan_undo',action_key='today_replan_undo'):
                    notify_success(service.cancel_replan(last['id'],context['token']),'Reagendamento desfeito.')
                    st.session_state.pop('today_replan_preview_data',None)
                    st.rerun()
