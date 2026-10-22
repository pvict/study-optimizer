"""Atividade do dia e feedback do registro, com denominadores explícitos."""
import streamlit as st

from .study_feedback import day_activity,result_feedback

MODES={'novas':'Questões novas','repetidas':'Questões repetidas','mistas':'Questões mistas'}


def _date_label(value):
    return '/'.join(reversed(value.split('-')))


def _percent(value):
    return f'{value:.1f}%'.replace('.',',') if value is not None else 'Não informada'


def _entry_summary(e):
    n=e['questions']
    if e['kind']=='contato': return 'Contato sem questões'
    accuracy=(f"{e['correct']}/{n} acertos ({_percent(100*e['correct']/n)})" if e.get('correct') is not None else
              f"≈ {_percent(e['percent'])} de acerto" if e.get('percent') is not None else 'Acerto não informado')
    confidence=f"{e['confident_correct']}/{n} com convicção ({_percent(100*e['confident_correct']/n)})" if e.get('confident_correct') is not None else 'Convicção não informada'
    return f'{n} questões · {accuracy} · {confidence}'


def render_day_activity(view,go_edit=None):
    activity=day_activity(view)
    st.subheader('Feito hoje')
    if not activity['events']:
        st.info('Nenhum bloco registrado hoje. Ao salvar um resultado, ele aparece aqui.')
        return
    blocks=str(activity['blocks'])+(' bloco' if activity['blocks']==1 else ' blocos')
    contacts=f" · {activity['contacts']} contato(s) sem questões" if activity['contacts'] else ''
    st.caption(f"{blocks} · {activity['questions']} questões registradas{contacts}. Repetições contam como tentativas; totais anteriores ficam no histórico.")
    for event in activity['events']:
        e=event['entry']
        with st.container():
            left,right=st.columns([4,1],vertical_alignment='center')
            left.markdown('**'+e['path'][-1]+'**')
            left.write(_entry_summary(e))
            left.caption(' › '.join(e['path'][:-1])+' · '+(MODES[e['mode']] if e['kind']=='bloco' else 'Estudo sem questões'))
            if go_edit:
                right.button('Corrigir',key='activity_edit_'+event['session_id'],on_click=go_edit,args=(event,),width='stretch')
        st.divider()


def render_result_feedback(view,session_id):
    feedback=result_feedback(view,session_id)
    if feedback is None:
        st.info('Este lançamento foi desconsiderado ou não está disponível no histórico atual. Consulte seus registros para conferir.')
        return
    e=feedback['entry']
    st.caption(_date_label(e['day'])+' · '+(MODES[e['mode']] if e['kind']=='bloco' else 'Total anterior' if e['kind']=='acumulado' else 'Contato sem questões'))
    if e['questions']:
        a,b=st.columns(2)
        a.metric('Acertos no bloco' if e['kind']=='bloco' else 'Acerto no total informado',('≈ ' if feedback['approximate'] else '')+_percent(feedback['accuracy_pct']))
        a.caption(f"{e['correct']} de {e['questions']} questões" if e.get('correct') is not None else f"Percentual aproximado em {e['questions']} questões; contagem exata não informada.")
        b.metric('Acertos com convicção',_percent(feedback['conviction_pct']))
        if feedback['conviction_pct'] is not None: b.caption(f"{e['confident_correct']} de {e['questions']} questões")
        else: b.caption('Campo deixado em branco; não foi tratado como zero.')
    getattr(st,feedback['level'])(feedback['message'])
    if feedback['mistakes'] is not None:
        st.caption(f"Erros: {feedback['mistakes']}"+(f" · Acertos sem convicção: {feedback['guesses']}" if feedback['guesses'] is not None else ''))
    if feedback['small_block']: st.caption('Bloco menor que o mínimo de referência: este resultado, sozinho, não amplia o intervalo do tema.')
    if e['kind']=='bloco' and e['mode']!='novas': st.caption('Este é o resultado do bloco registrado. Acerto em repetidas não mede seu desempenho em questões novas.')
    st.subheader('Próximos passos para este tema')
    st.write(feedback['next_action'])
    if feedback['next_questions'] is not None:
        st.markdown(f"**Próximo bloco de referência: {feedback['next_questions']} questões.**")
        if feedback['next_contact']:
            st.write('Próximo contato indicado: '+_date_label(feedback['next_contact'])+'.')
        else: st.caption('Não há contato indicado dentro da preparação. Confira a data da prova em Ajustes.')
    pending=feedback['pending']
    if pending:
        st.info(f"{pending['questions']} respostas deste registro ainda sem convicção · retorno em {_date_label(pending['due_date'])}. Esse lote fica separado da revisão completa do tema.")
    elif e['kind']=='bloco' and feedback['conviction_pct'] is None:
        st.caption('Sem a contagem de convicção, não foi criado um lote de erros e chutes para este bloco.')
    st.caption('A quantidade é recalculada com seus registros; consulte as vagas no Calendário. Um único bloco não comprova domínio do tema.')
