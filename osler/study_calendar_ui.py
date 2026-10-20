"""Calendário em cards semanais/mensais e detalhe do dia, com previsão identificada."""
import calendar
from datetime import timedelta,date
import streamlit as st
from .planner_service import today_local
from .study_replanning import past_calendar
from .study_replanning_ui import render_replanning
from .study_prevention_ui import render_prevention,open_prevention


def _select_day(day):
    st.session_state['calendar_selected']=day


def _reference_changed():
    st.session_state['calendar_selected']=st.session_state['calendar_reference'].isoformat()


def _day_summary(day,plan,context,today):
    if plan is None:
        st.caption('Fora do período disponível')
        return
    if plan.get('not_started'):
        st.caption('Antes do início · sem meta')
        return
    if plan.get('historical'):
        st.caption(f"{plan['done_questions']} feitas" if plan['done_questions'] else 'Sem estudo registrado')
    else: st.markdown('**'+('Descanso' if plan['kind']=='descanso' else f"{plan['questions']} questões")+'**')
    count=len(plan.get('delayed_topics',[])) if plan.get('historical') else len(context['backlog']) if day==today else 0
    if count: st.html(f'<div class="calendar-badge calendar-late">{count} atrasados</div>')
    booked=sum(i.get('rescheduled',False) for i in plan['items'])
    if booked: st.html(f'<div class="calendar-badge calendar-booked">{booked} recuperações</div>')
    if day>today and plan.get('topic_backlog'):
        st.html(f'<div class="calendar-badge calendar-risk">{plan["topic_backlog"]} revisões com risco de ficar sem vaga</div>')
        st.button('Ver revisões',key='calendar_risks_'+day.isoformat(),on_click=open_prevention,args=(day.isoformat(),),width='stretch')
    if plan.get('pending_planned'): st.caption(f"{plan['pending_planned']} retornos de 7 dias")
    if plan.get('pending_backlog'): st.caption(f"{plan['pending_backlog']} pendências sem vaga")
    if plan['items']: st.caption(plan['items'][0]['path'][-1]+(f" +{len(plan['items'])-1} temas" if len(plan['items'])>1 else ''))


def _date_button(day,plan,selected):
    label=['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][day.weekday()]+' · '+day.strftime('%d/%m')
    st.button(label,key='calendar_cell_'+day.isoformat(),on_click=_select_day,args=(day.isoformat(),),
              disabled=plan is None,type='primary' if day.isoformat()==selected else 'secondary',width='stretch')


def render_calendar(service,go_record):
    today=today_local()
    start_date=service.store.profile()['profile'].get('start_date')
    if start_date: st.caption('Início do cronograma: '+ '/'.join(reversed(start_date.split('-'))))
    st.caption('Previsão dinâmica · depende dos blocos realizados. Agendar não registra estudo nem acertos.')
    service.remember_day(service.overview(today.isoformat()))
    context=service.replanning()
    if any(t.get('review_committed') is False for t in context['view']['planning_states']):
        st.caption('O histórico importado forma uma fila de prioridades. Os primeiros contatos são distribuídos dentro da sua carga; não são dívidas de estudo. Alertas abaixo se referem a revisões já previstas neste cenário.')
    render_replanning(service,context)
    render_prevention(service)
    top=st.columns([1,1])
    mode=top[0].radio('Visão',['Agenda','Semana','Mês'],horizontal=True,key='calendar_mode')
    initial=min(max(today,date.fromisoformat(start_date)),today+timedelta(days=547)) if start_date else today
    if start_date and date.fromisoformat(start_date)>today+timedelta(days=547): st.caption('O início está além do horizonte atual de18meses. O calendário ainda não programa blocos nesse período.')
    reference=top[1].date_input('Ir para uma data',value=initial,min_value=today-timedelta(days=90),max_value=today+timedelta(days=547),key='calendar_reference',on_change=_reference_changed)
    end=min(today+timedelta(days=547),reference.replace(day=calendar.monthrange(reference.year,reference.month)[1])+timedelta(days=7))
    plans=service.calendar(max(1,(end-today).days+1))
    by_date={p['date']:p for p in plans}
    by_date.update(past_calendar(context['view']['planning_states'],context['view']['sessions'],service.agenda.daily_plans(),(today-timedelta(days=96)).isoformat(),today.isoformat(),context['backlog']))
    days=[reference-timedelta(days=reference.weekday())+timedelta(days=i) for i in range(7)] if mode!='Mês' else list(calendar.Calendar().itermonthdates(reference.year,reference.month))
    st.caption(reference.strftime('%m/%Y')+' · escolha um dia para ver os blocos')
    selected=st.session_state.get('calendar_selected',reference.isoformat())
    if selected not in by_date: selected=reference.isoformat()
    if mode=='Agenda':
        with st.container(key='calendar_agenda'):
            for day in days:
                plan=by_date.get(day.isoformat())
                with st.container(border=True):
                    left,right=st.columns([1,3])
                    with left: _date_button(day,plan,selected)
                    with right: _day_summary(day,plan,context,today)
    else:
        with st.container(key='calendar_grid'):
            for start in range(0,len(days),7):
                columns=st.columns(7,gap='small')
                for column,day in zip(columns,days[start:start+7]):
                    plan=by_date.get(day.isoformat())
                    with column.container(border=True):
                        _date_button(day,plan,selected)
                        _day_summary(day,plan,context,today)
    plan=by_date[selected]
    st.subheader('Blocos de '+ '/'.join(reversed(selected.split('-'))))
    if plan.get('not_started'):
        st.info('O cronograma ainda não começou neste dia. Escolha uma data a partir de '+ '/'.join(reversed(start_date.split('-')))+'.')
        return
    if plan.get('historical'):
        if not plan['has_plan']: st.info('Dia sem plano salvo. Não presumimos quais temas você deveria ter feito.')
        st.caption(f"{plan['done_questions']} questões realmente registradas nesse dia.")
        for row in plan.get('delayed_topics',[]): st.warning(row['path'][-1]+f" · {row['days_late']}dias de atraso · reorganize pela seção de atrasos acima.")
        return
    if selected>today.isoformat() and plan.get('backlog_items'):
        import pandas as pd
        st.markdown('**Revisões já previstas que podem ficar sem vaga neste cenário**')
        st.dataframe(pd.DataFrame([{'Tema específico':r['path'][-1],'Revisão prevista para':r['due_date'],
                                    'Caminho':' › '.join(r['path'])} for r in plan['backlog_items']]),hide_index=True,width='stretch')
        st.button('Redistribuir antes de atrasar',key='prevent_selected_day',on_click=open_prevention,args=(selected,))
    if plan.get('pending_planned'): st.info(f"Inclui {plan['pending_planned']} respostas sem convicção com retorno de 7 dias. É previsão de prática, não confirmação de que foram resolvidas.")
    if plan.get('pending_backlog'): st.warning(f"{plan['pending_backlog']} questões de revisão vencidas ainda não cabem nesta programação. Aumente a meta, acrescente um bloco ou redistribua os próximos dias.")
    if plan.get('topic_backlog'): st.caption(f"{plan['topic_backlog']} temas com revisão prevista ainda aguardam vaga. As datas são prioridades de planejamento, não garantia de execução dentro da carga escolhida.")
    for item in plan['items']:
        with st.container(border=True):
            left,right=st.columns([3,1])
            left.markdown('**'+item['path'][-1]+f" · {item['questions']} questões**")
            left.caption(item['stage'])
            if item.get('preventive_priority'): left.caption('Plano preventivo'+(f" · antecipada em {item['anticipated_days']}dia(s)" if item.get('anticipated_days') else ''))
            if item.get('rescheduled'): left.caption('Recuperação · vencimento original '+item['original_due'])
            left.caption(' › '.join(item['path'][:-1]))
            if selected==today.isoformat():
                mode='mistas' if item['new_questions'] and item['repeat_questions'] else 'repetidas' if item['repeat_questions'] else 'novas'
                right.button('Registrar',key='calendar_record_'+item['topic_id'],on_click=go_record,args=(item['topic_id'],item['questions'],mode))
    if not plan['items']: st.info('Dia sem blocos previstos. Pode ser descanso ou intervalo entre revisões.')
    snapshot=st.session_state.setdefault('calendar_snapshot_'+selected,service.store.day(selected,service.store.profile()['profile']['max_questions']))
    with st.expander('Programar quantidade ou descanso deste dia'):
        with st.form('calendar_day_'+selected):
            q=st.number_input('Meta de questões',1,1000,snapshot['settings']['questions'],key='calendar_goal_'+selected)
            rest=st.checkbox('Descanso',value=snapshot['settings']['kind']=='descanso',key='calendar_rest_'+selected)
            save=st.form_submit_button('Salvar programação')
        if save:
            service.configure_day(selected,int(q),'descanso' if rest else 'normal',snapshot['revision'])
            st.session_state.pop('calendar_snapshot_'+selected,None)
            st.success('Programação salva. O calendário será recalculado.')
            st.rerun()
