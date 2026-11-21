"""Disponibilidade informada pelo usuário; não consulta a plataforma."""
import streamlit as st
from .action_feedback import confirm_button,notify_success


def _date(day): return '/'.join(reversed(day.split('-')))


def _open(day,topic_id):
    st.session_state['return_deferral_open']=(day,topic_id)
    st.session_state.pop('return_deferral_preview',None)


def _close():
    st.session_state.pop('return_deferral_open',None)
    st.session_state.pop('return_deferral_preview',None)


def _apply(service,preview):
    try:
        notify_success(service.defer_return(preview['day'],preview['topic_id'],preview['token']),'Retorno adiado.')
        st.session_state['adaptive_notice']=f"{preview['item']['path'][-1]} reservado a partir de {_date(preview['available_from'])}. Plano de hoje recalculado. Você pode desfazer em Detalhes do dia e do plano."
        _close()
    except ValueError as exc:
        st.session_state['adaptive_error']=str(exc)
        st.session_state.pop('return_deferral_preview',None)


def _undo(service,day,plan_id,token):
    try:
        notify_success(service.undo_return_deferral(day,plan_id,token),'Adiamento desfeito.')
        st.session_state['adaptive_notice']='Adiamento desfeito. Seus resultados foram preservados.'
        _close()
    except ValueError as exc: st.session_state['adaptive_error']=str(exc)


def render_return_deferral(service,view,item):
    day=view['date']; topic_id=item['topic_id']
    if not any(q['due_date']<=day for q in item.get('pending_reviews',[])): return
    st.button('Retorno indisponível hoje',key='return_defer_open_'+topic_id,on_click=_open,args=(day,topic_id),
              help='Use quando as questões de retorno deste bloco ainda não estiverem disponíveis na Osler.')
    if st.session_state.get('return_deferral_open')!=(day,topic_id): return
    stamp=(day,topic_id,view['planning_token'])
    cached=st.session_state.get('return_deferral_preview',{})
    if cached.get('stamp')!=stamp:
        try: cached={'stamp':stamp,'preview':service.preview_return_deferral(day,topic_id)}
        except ValueError as exc:
            st.error(str(exc));_close();return
        st.session_state['return_deferral_preview']=cached
    preview=cached['preview']
    with st.container(border=True):
        st.markdown('**Adiar este bloco inteiro?**')
        st.write(f"{item['path'][-1]} · reservado a partir de {_date(preview['available_from'])}.")
        if preview['replacements']:
            st.write('Entra hoje: '+', '.join(f"{i['path'][-1]} ({i['questions']} questões)" for i in preview['replacements'])+'.')
        else:
            st.write('A vaga fica livre para os blocos elegíveis, dentro da meta e dos limites atuais.')
        with st.expander('Ver plano após adiamento'):
            for row in preview['plan']['items']: st.write(f"{row['path'][-1]} · {row['questions']} questões")
            st.write('Descanso, simulados e limites diários são preservados. Se amanhã não houver espaço, o bloco segue reservado para a próxima vaga. Nenhuma questão é registrada como feita.')
        confirm_button('Adiar para amanhã',key='return_defer_apply_'+topic_id,action_key='return_defer_apply_'+topic_id,
                       details=f"{item['path'][-1]} sairá de hoje e ficará reservado a partir de {_date(preview['available_from'])}. O plano de hoje será recalculado sem registrar estudo.",
                       on_click=_apply,args=(service,preview))
        st.button('Manter hoje',key='return_defer_cancel_'+topic_id,on_click=_close)


def render_return_deferral_history(service,view):
    rows=[r for r in view['agenda'].get('return_deferrals',[]) if r['created_day']==view['date']]
    if not rows:return
    with st.expander('Retornos adiados hoje',expanded=True):
        for record in rows:
            row=record['rows'][0]
            st.write(f"{row['path'][-1]} · a partir de {_date(record['available_from'])}")
            confirm_button('Desfazer adiamento',key=f"return_defer_undo_{record['id']}",action_key=f"return_defer_undo_{record['id']}",
                           on_click=_undo,args=(service,view['date'],record['id'],view['planning_token']))
