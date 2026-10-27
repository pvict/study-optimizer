"""Troca pontual com prévia do tema escolhido e da reserva do tema retirado."""
import streamlit as st
from .topic_picker_ui import pick_topic,reset_picker
from .study_allocation import topic_is_new

PRIORITIES={'urgente':'Urgente','alta':'Alta','normal':'Normal'}


def _close():
    st.session_state.pop('open_swap',None)
    st.session_state.pop('swap_preview',None)
    reset_picker('swap_pick')


def _open(day,topic_id):
    _close()
    st.session_state['open_swap']=(day,topic_id)


def _apply(service,day,source,target,token,mode):
    try:
        service.swap_topic(day,source,target,token,mode)
        st.session_state['adaptive_notice']='Tema trocado. O tema retirado ficou reservado no calendário; seu histórico foi preservado.'
        _close()
    except ValueError as exc:
        st.session_state['adaptive_error']=str(exc)
        st.session_state.pop('swap_preview',None)


def _undo(service,day,slot,token):
    try:
        service.undo_swap(day,slot,token)
        st.session_state['adaptive_notice']='Troca desfeita. A reserva criada por ela também foi retirada; os estudos registrados continuam no histórico.'
        _close()
    except ValueError as exc: st.session_state['adaptive_error']=str(exc)


def _describe(topic):
    return ('Tema novo' if topic_is_new(topic) else 'Revisão / diagnóstico')+' · Prioridade '+PRIORITIES[topic['priority']].lower()


def render_swap_controls(service,day,item,scope='today',button_container=None):
    (button_container or st).button('Trocar tema',key=f'swap_open_{scope}_{item["topic_id"]}',on_click=_open,args=(day,item['topic_id']))
    if st.session_state.get('open_swap')!=(day,item['topic_id']): return
    key=(day,item['topic_id'],service.agenda.token())
    cached=st.session_state.get('swap_preview',{})
    if cached.get('key')!=key:
        with st.spinner('Buscando uma alternativa e uma vaga para o tema retirado…'):
            cached={'key':key,'options':service.swap_options(day,item['topic_id'])}
            st.session_state['swap_preview']=cached
    options=cached['options']
    original=options['original']; reservation=options['return_plan']
    st.caption(f"A troca mantém {original['questions']} questões neste bloco e vale só para hoje.")
    if reservation:
        date='/'.join(reversed(reservation['date'].split('-')))
        st.info(f"{original['path'][-1]} será remanejado a partir de {date} · primeiro bloco de {reservation['first_block_questions']} questões. A data ficará reservada no Calendário.")
        if reservation['questions']>reservation['first_block_questions']: st.caption(f"O saldo de {reservation['questions']} questões da reserva anterior será preservado, com continuação nos próximos dias conforme a carga.")
    else:
        st.warning('Não encontramos uma vaga nos próximos 90 dias antes da prova. Ajuste a rotina para remanejar este tema antes de trocar.')
    suggested,manual=st.tabs(['Sugestão do app','Escolher tema'])
    with suggested:
        chosen=options['recommended']
        if chosen:
            st.markdown('**'+chosen['path'][-1]+'**')
            st.caption(' › '.join(chosen['path'][:-1]))
            st.write(_describe(chosen))
            st.caption('Mesmo tipo de bloco; prioridade igual ou de uma categoria vizinha. Entre essas opções, buscamos a pontuação mais próxima.')
            st.button('Usar esta sugestão',key=f'swap_suggest_{scope}_{item["topic_id"]}',type='primary',disabled=reservation is None,
                      on_click=_apply,args=(service,day,item['topic_id'],chosen['topic_id'],options['token'],'recommended'))
        else: st.info('Não há outra opção do mesmo tipo e com prioridade semelhante disponível hoje. Você pode escolher manualmente.')
    with manual:
        if not options['manual']: st.info('Nenhum outro tema tem banco suficiente para este bloco fora dos estudos e reservas já existentes.')
        chosen=pick_topic(options['manual'],'swap_pick')
        if chosen:
            st.write(_describe(chosen))
            if topic_is_new(chosen)!=topic_is_new(original): st.caption('Esta escolha muda a divisão entre temas novos e revisões só neste dia.')
            due=chosen.get('theme_review_due')
            if due and due>day: st.caption('Você estará antecipando o contato com este tema.')
            st.button('Trocar por este tema',key=f'swap_manual_{scope}_{item["topic_id"]}',disabled=reservation is None,
                      on_click=_apply,args=(service,day,item['topic_id'],chosen['topic_id'],options['token'],'manual'))
    st.button('Cancelar troca',key=f'swap_cancel_{scope}_{item["topic_id"]}',on_click=_close)


def render_swap_history(service,view):
    swaps=[s for s in view['agenda'].get('swaps',[]) if s['day']==view['date']]
    if not swaps: return
    with st.expander('Trocas de hoje',expanded=True):
        for swap in swaps:
            st.write(swap['from_path'][-1]+' → '+swap['path'][-1])
            for row in view['agenda']['rows']:
                if row.get('swap_return')==swap['slot_id']:
                    st.caption(row['path'][-1]+' · reservado para '+ '/'.join(reversed(row['date'].split('-')))+f" · {row['remaining']} questões")
            st.button('Desfazer troca',key='swap_undo_'+swap['slot_id'],on_click=_undo,
                      args=(service,view['date'],swap['slot_id'],service.agenda.token()))
