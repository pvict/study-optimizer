"""Atividade do dia e feedback do registro, com denominadores explícitos."""
import streamlit as st

from .study_feedback import day_activity,result_feedback
from .study_dashboard import entry_clock

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
    cards=f" · {e['cards_created']} flashcards criados" if e.get('cards_created') else ''
    return f'{n} questões · {accuracy} · {confidence}{cards}'


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
            if clock:=entry_clock(event):
                left.caption(('Atualizado' if event['version']>1 else 'Registrado')+' às '+clock+' · Brasília')
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
        b.metric('Acertos com convicção',_percent(feedback['conviction_pct']))
    st.subheader('Próximo contato')
    if feedback['next_questions'] is not None:
        label='Próximo retorno dirigido' if feedback.get('next_review_kind')=='lot_only' else 'Próximo bloco de referência'
        st.markdown(f"**{label}: {feedback['next_questions']} questões.**")
        if feedback['next_contact']:
            st.write('Próximo contato indicado: '+_date_label(feedback['next_contact'])+'.')
        else:
            st.warning('Sem próximo contato na preparação. Confira a data da prova em Ajustes.')
        from .study_components import render_planner_supply
        render_planner_supply(feedback)
    else:
        st.write(feedback['next_action'])
    if feedback.get('theme_contact') and feedback['theme_contact']!=feedback['next_contact']:
        st.write(f"Revisão geral: {feedback['theme_questions']} questões · {_date_label(feedback['theme_contact'])}.")
    pending=feedback['pending']
    if pending:
        st.write(f"Retorno de {pending['questions']} respostas · {_date_label(pending['due_date'])}."+
                 (' Incluído no próximo bloco.' if feedback.get('coordinated_return') else ''))
    with st.expander('Detalhes do resultado e da revisão'):
        if e['questions']:
            st.write(f"{e['correct']} de {e['questions']} acertos" if e.get('correct') is not None else f"Percentual aproximado em {e['questions']} questões; contagem exata não informada.")
            st.write(f"{e['confident_correct']} de {e['questions']} com convicção" if feedback['conviction_pct'] is not None else 'Convicção não informada; não foi tratada como zero.')
        getattr(st,feedback['level'])(feedback['message'])
        if feedback['mistakes'] is not None:
            st.caption(f"Erros: {feedback['mistakes']}"+(f" · Acertos sem convicção: {feedback['guesses']}" if feedback['guesses'] is not None else ''))
        if feedback['small_block']: st.caption('Bloco menor que o mínimo de referência: este resultado, sozinho, não amplia o intervalo do tema.')
        if e['kind']=='bloco' and e['mode']!='novas': st.caption('Este é o resultado do bloco registrado. Acerto em repetidas não mede seu desempenho em questões novas.')
        st.write(feedback['next_action'])
        pending=feedback['pending']
        if pending:
            if feedback.get('coordinated_return'):
                st.info(f"Retorno coordenado em {_date_label(pending['due_date'])}: as {pending['questions']} respostas ainda sem convicção entram no mesmo bloco de {feedback['next_questions']} questões no total. Registre o lote vinculado e o complemento separadamente para preservar as contagens.")
            else:
                extra='Registre pelo lote vinculado; a agenda combina os encontros próximos no mesmo orçamento.' if view['profile'].get('review_strategy')=='balanced_v2' else 'Esse lote fica separado da revisão completa do tema.'
                st.info(f"{pending['questions']} respostas deste registro ainda sem convicção · retorno em {_date_label(pending['due_date'])}. "+extra)
        elif e['kind']=='bloco' and feedback['conviction_pct'] is None:
            st.caption('Sem a contagem de convicção, não foi criado um lote de erros e chutes para este bloco.')
        st.caption('A quantidade é recalculada com seus registros; consulte as vagas no Calendário. Um único bloco não comprova domínio do tema.')
