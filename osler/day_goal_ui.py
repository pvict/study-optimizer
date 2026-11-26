"""Um único editor de meta efetiva para Hoje e Calendário."""
import streamlit as st

from .action_feedback import confirm_button,notify_success
from .day_goal_service import goal_summary


def render_day_goal(service,view,day,prefix='today'):
    record=service.store.day(day,view['profile']['max_questions'])
    current=goal_summary(view)
    qkey='day_questions' if prefix=='today' else 'calendar_goal_'+day
    rkey='day_rest' if prefix=='today' else 'calendar_rest_'+day
    tag=(day,record['revision'],current['total'])
    init=prefix+'_goal_init'
    if st.session_state.get(init)!=tag or qkey not in st.session_state or rkey not in st.session_state:
        st.session_state[qkey]=current['total'] or record['settings']['questions']
        st.session_state[rkey]=record['settings']['kind']=='descanso'
        st.session_state[init]=tag
    with st.form('day_goal' if prefix=='today' else 'calendar_day_'+day):
        manual=view['plan'].get('manual_extra_questions',0)
        q=st.number_input('Meta total de questões',min_value=1,max_value=1000+manual,key=qkey,
                          help='Inclui questões dos temas, treino por área e revisões externas reservadas.')
        rest=st.checkbox('Hoje é dia de descanso' if prefix=='today' else 'Descanso',key=rkey)
        submit=st.form_submit_button('Ver prévia da meta',key=prefix+'_goal_preview')
    preview_key=prefix+'_goal_preview_data_'+day
    if submit:
        try:st.session_state[preview_key]=service.preview_day_goal(day,int(q),'descanso' if rest else 'normal')
        except ValueError as exc:
            st.session_state.pop(preview_key,None)
            st.error(str(exc))
    preview=st.session_state.get(preview_key)
    if not preview:return
    st.markdown('**Confira a distribuição**')
    st.dataframe([{'Atividade':label,'Antes':preview['before'][field],'Depois':preview['after'][field]}
        for label,field in [('Meta total','total'),('Revisões externas','external'),
                            ('Treino por área','area'),('Temas do app','themes')]],hide_index=True,width='stretch')
    st.caption('Vale somente para '+ '/'.join(reversed(day.split('-')))+'.')
    remaining=max(0,preview['after']['themes']-preview['after']['done']-preview['after']['planned'])
    if remaining:
        st.info(f"{remaining} questões não foram distribuídas.")
    old=preview.get('replaces_recovery_limit')
    if old is not None and old!=preview['after']['total'] and not rest:
        st.info(f"O limite da retomada muda de {old} para {preview['after']['total']} somente neste dia.")
    with st.expander('Ver temas e detalhes da distribuição'):
        a={i['topic_id']:i for i in preview['before']['items']}
        b={i['topic_id']:i for i in preview['after']['items']}
        st.dataframe([{'Tema':' › '.join((b.get(k) or a[k])['path']),
                       'Antes':a.get(k,{}).get('questions',0),'Depois':b.get(k,{}).get('questions',0)}
                      for k in dict.fromkeys([*a,*b])],hide_index=True,width='stretch')
        st.caption('A meta reserva capacidade. A quantidade planejada depende dos temas elegíveis, '
                   'dos limites de cada bloco e do máximo de temas. Pendências seguem na fila; resultados são preservados.')
    stale=(preview['token']!=service.agenda.token() or preview['request']['questions']!=int(q) or
           preview['request']['kind']!=('descanso' if rest else 'normal'))
    if stale:st.warning('Os dados mudaram. Confira a prévia novamente antes de aplicar.')
    if confirm_button('Aplicar meta deste dia',key=prefix+'_goal_apply',disabled=stale,
        action_key=prefix+'_goal_apply_'+day,details=f"{day}: meta total de {preview['after']['total']} questões. Vale somente nesta data."):
        try:
            notify_success(service.apply_day_goal(preview),'Meta deste dia atualizada.')
            st.session_state.pop(preview_key,None)
            st.session_state.pop('day_form_snapshot',None)
            st.session_state.pop('calendar_snapshot_'+day,None)
            st.rerun()
        except ValueError as exc:st.error(str(exc))
    if st.button('Descartar prévia',key=prefix+'_goal_discard'):
        st.session_state.pop(preview_key,None)
        st.rerun()
