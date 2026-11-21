"""A escolha de dispensar é explícita e reversível, sem contabilizar respostas."""
from .action_feedback import confirm_button,confirm_submit,notify_success

import streamlit as st
from .planner_completion import can_skip_complement,partial_block_context,complete_partial_block


def _skip(service,day,topic_id,token):
    try:
        notify_success(service.skip_planner_complement(day,topic_id,token),'Alterações salvas.')
        st.session_state['adaptive_notice']='Tema liberado do dia. O desempenho e a próxima revisão continuam calculados pelos seus registros.'
    except ValueError as exc:st.session_state['adaptive_error']=str(exc)


def _restore(service,day,decision_id,token):
    try:
        notify_success(service.restore_planner_complement(day,decision_id,token),'Alterações salvas.')
        st.session_state['adaptive_notice']='Dispensa desfeita. O complemento voltou ao plano de hoje.'
    except ValueError as exc:st.session_state['adaptive_error']=str(exc)


def _complete_partial(service,day,topic_id,token):
    try:
        notify_success(complete_partial_block(service,day,topic_id,token),'Bloco concluído com quantidade parcial.')
        st.session_state['adaptive_notice']='Bloco liberado de hoje. Contamos somente as questões feitas; a próxima revisão segue seus resultados.'
    except ValueError as exc:st.session_state['adaptive_error']=str(exc)


def render_completion_choice(service,view,item,prefix=''):
    day=view['date']
    if not can_skip_complement(item,day):
        context=partial_block_context(view,item)
        confirm_button('Concluir bloco com menos questões',key=prefix+'complete_partial_'+item['topic_id'],
            disabled=context['completed']<=0,help='Registre primeiro as questões realmente feitas. Use esta opção se não houver mais questões disponíveis.',
            details=f"Concluir com {context['completed']} de {context['recommended']} questões por falta de questões no banco? As {context['remaining']} restantes serão dispensadas deste bloco. O desempenho e a próxima revisão considerarão apenas seus registros reais.",
            on_click=_complete_partial,args=(service,day,item['topic_id'],view['planning_token']),action_key='partial_block_complete')
        return
    supply=item['planner_supply']
    st.caption(f"Registradas para este bloco: {supply['completed']} questões. Planner: {supply['planner_total']} disponíveis. Se concluiu essa lista, pode dispensar as {item['questions']} complementares ou buscá-las no banco completo.")
    confirm_button('Encerrar tema hoje',key=prefix+'skip_complement_'+item['topic_id'],
              on_click=_skip,args=(service,day,item['topic_id'],view['planning_token']),action_key='planner_completion_ui_25')


def render_completions(service,view):
    decisions=view['plan'].get('planner_completions',[])
    if not decisions:return
    st.markdown('**Blocos concluídos com quantidade parcial**')
    for row in decisions:
        with st.container(border=True):
            st.write(row['path'][-1])
            if row.get('manual_partial'):
                st.caption(f"{row['required_completed']} questões registradas; {row['skipped_questions']} dispensadas por falta de questões no banco. A revisão segue seus resultados.")
            else:st.caption(f"{row['skipped_questions']} questões complementares dispensadas; não contam como respondidas. A revisão segue o rendimento e o contato registrados.")
            state=next((t for t in view['states'] if t['topic_id']==row['topic_id']),None)
            if state and state.get('next_review'):
                st.caption('Próxima revisão indicada: '+ '/'.join(reversed(state['next_review'].split('-')))+'. A vaga é calculada no Calendário.')
            confirm_button('Desfazer dispensa',key='restore_complement_'+str(row['id']),on_click=_restore,
                      args=(service,view['date'],row['id'],view['planning_token']),action_key='planner_completion_ui_40')
