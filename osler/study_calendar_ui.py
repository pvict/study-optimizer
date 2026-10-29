"""Calendário em cards semanais/mensais e detalhe do dia, com previsão identificada."""
import calendar
from datetime import timedelta,date
from html import escape
import streamlit as st
from .bento import area_slug,eyebrow,chip
from .planner_service import today_local
from .study_replanning import past_calendar
from .study_replanning_ui import render_replanning
from .study_prevention_ui import render_prevention,open_prevention
from .study_capacity_ui import render_capacity_summary
from .study_swap_ui import render_swap_controls
from .final_review_ui import render_exam_dates,render_final_review,render_mock_days
from .mock_schedule_ui import render_mock_schedule
from .review_parts_ui import render_review_parts
from .study_components import render_planner_supply,render_bank_scope


_MONTHS=('Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro')
_DAY_LABELS={'feito':'Com registro','hoje':'Hoje','previsao':'Previsão','simulado':'Simulado','descanso':'Descanso','semplano':'Sem plano'}


def _month_label(day):
    return f'{_MONTHS[day.month-1]} {day.year}'


def _shift_month(day,offset,minimum=None,maximum=None):
    """Navegação de apresentação, preservando o dia dentro do mês e do horizonte."""
    year,month=divmod(day.year*12+day.month-1+offset,12)
    result=date(year,month+1,min(day.day,calendar.monthrange(year,month+1)[1]))
    if minimum is not None:result=max(minimum,result)
    if maximum is not None:result=min(maximum,result)
    return result


def _day_state(day,plan,today):
    if plan is None:return 'semplano'
    mode=plan.get('routine_override',{}).get('mode')
    if mode in {'mock_reserved','mock_day'}:return 'simulado'
    if plan.get('not_started'):return 'semplano'
    done=plan.get('done_questions')
    if day<=today and done is not None and done>0:return 'feito'
    if mode=='final_rest' or plan.get('kind')=='descanso':return 'descanso'
    if day==today:return 'hoje'
    if day>today and (plan.get('items') or (plan.get('questions') or 0)>0):return 'previsao'
    return 'semplano'


def _day_area_chips(plan):
    areas=[]
    for item in (plan or {}).get('items',[]):
        path=item.get('path') or []
        if path and path[0] not in areas:areas.append(path[0])
        if len(areas)==2:break
    return ''.join('<span class="o-calendar-area o-calendar-area--'+area_slug([area])+'">'+escape(area)+'</span>' for area in areas)


def _move_month(offset,minimum,maximum):
    st.session_state['calendar_reference']=_shift_month(st.session_state['calendar_reference'],offset,minimum,maximum)
    _reference_changed()


def _select_day(day):
    st.session_state['calendar_selected']=day


def _reference_changed():
    st.session_state['calendar_selected']=st.session_state['calendar_reference'].isoformat()


def _day_summary(day,plan,context,today):
    state=_day_state(day,plan,today)
    markers=' o-calendar-today' if day==today else ''
    if day.isoformat()==st.session_state.get('calendar_selected',st.session_state.get('calendar_reference',today).isoformat()):markers+=' o-calendar-selected'
    label='Hoje' if day==today and state=='feito' else _DAY_LABELS[state]
    st.html('<div class="o-calendar-state'+markers+'">'+label+'</div>')
    for e in context.get('exam_dates',[]):
        if e['date']==day.isoformat(): st.caption(e['label']+' · '+e['institution'])
    for e in context.get('correction_days',[]):
        if e['date']==day.isoformat(): st.caption('Correção · '+e['name']+(' · informar temas' if e['needs_details'] else ' · reforço programado'))
    if plan is None:
        st.caption('Fora do período disponível')
        return
    if plan.get('routine_override',{}).get('mode')=='mock_reserved':
        done=day.isoformat() in context.get('mock_result_days',set())
        st.caption('Simulado realizado' if done else 'Simulado programado')
        st.caption('Resultado registrado em Simulados' if done else 'Meta normal dispensada · resultado ainda não registrado')
        return
    if plan.get('routine_override',{}).get('mode')=='mock_day':
        st.caption('Simulado realizado'); return
    if plan.get('not_started'):
        st.caption('Antes do início · sem meta')
        return
    for task in plan.get('area_tasks',[]):
        st.caption('Treino por área · '+task['institution']+' · '+task['area']+f" · {task['questions']} questões"+(' · realizado' if task['completed'] else ''))
    if plan.get('historical'):
        done=plan.get('done_questions')
        st.caption('Quantidade não informada' if done is None else f'{done} questões registradas' if done else 'Sem estudo registrado')
    elif state=='descanso':st.caption('Meta dispensada')
    else:
        questions=plan.get('questions')
        st.caption('Quantidade não informada' if questions is None else f'{questions} questões previstas' if day>today and questions else 'A recalcular' if day>today else f'{questions} questões no plano')
        if state=='feito':st.caption(f"{plan['done_questions']} questões registradas")
    areas=_day_area_chips(plan)
    if areas:st.html('<div class="o-calendar-areas">'+areas+'</div>')
    if day>today and plan.get('topic_backlog'):
        st.caption(f"{plan['topic_backlog']} revisões a encaixar")
        if plan.get('capacity',{}).get('mode')!='adaptive': st.button('Ver revisões',key='calendar_risks_'+day.isoformat(),on_click=open_prevention,args=(day.isoformat(),),width='stretch')


def _date_button(day,plan,selected):
    label=['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][day.weekday()]+' · '+day.strftime('%d/%m')
    st.button(label,key='calendar_cell_'+day.isoformat(),on_click=_select_day,args=(day.isoformat(),),
              disabled=plan is None,type='primary' if day.isoformat()==selected else 'secondary',width='stretch')


def render_calendar(service,go_record,go_review=None):
    today=today_local()
    start_date=service.store.profile()['profile'].get('start_date')
    service.remember_day(service.overview(today.isoformat()))
    context=service.replanning()
    context['mock_result_days']=service.recorded_mock_days()
    context['exam_dates']=service.exam_dates()
    context['correction_days']=service.exam_learning_agenda()
    initial=min(max(today,date.fromisoformat(start_date)),today+timedelta(days=547)) if start_date else today
    minimum,maximum=today-timedelta(days=90),today+timedelta(days=547)
    if start_date and date.fromisoformat(start_date)>maximum: st.caption('O início está além do horizonte atual de 18 meses. O calendário ainda não programa blocos nesse período.')
    st.session_state.setdefault('calendar_reference',initial)
    with st.container(key='bento-calendar-toolbar'):
        previous,title,following,vision,picker=st.columns([.65,2,.65,3.2,2.4],vertical_alignment='center',gap='small')
        reference=st.session_state['calendar_reference']
        previous.button('Anterior',key='calendar_previous_month',icon=':material/chevron_left:',help='Mês anterior',on_click=_move_month,args=(-1,minimum,maximum),disabled=reference==minimum)
        title.html('<h3 class="o-calendar-month">'+_month_label(reference)+'</h3>')
        following.button('Próximo',key='calendar_next_month',icon=':material/chevron_right:',help='Próximo mês',on_click=_move_month,args=(1,minimum,maximum),disabled=reference==maximum)
        mode=vision.radio('Visão',['Agenda','Semana','Mês'],index=1,horizontal=True,key='calendar_mode')
        reference=picker.date_input('Ir para uma data',min_value=minimum,max_value=maximum,key='calendar_reference',on_change=_reference_changed,format='DD/MM/YYYY')
    with st.container(key='bento-calendar-replanning'):
        count=len(context['backlog'])
        label=f'{count} '+('tema pede nova data' if count==1 else 'temas pedem nova data')
        with st.expander('Reorganizar · '+label):
            if count:st.caption('Temas atrasados nesta agenda podem receber novas datas. A prévia não altera seus resultados.')
            render_replanning(service,context)
    end=min(today+timedelta(days=547),reference.replace(day=calendar.monthrange(reference.year,reference.month)[1])+timedelta(days=7))
    plans=service.calendar(max(1,(end-today).days+1))
    by_date={p['date']:p for p in plans}
    by_date.update(past_calendar(context['view']['planning_states'],context['view']['sessions'],service.agenda.daily_plans(),(today-timedelta(days=96)).isoformat(),today.isoformat(),context['backlog']))
    from .exam_practice import decorate_practice_plan
    for key,plan in by_date.items():
        if plan.get('historical'): decorate_practice_plan(plan,context['view']['agenda'],key,context['view']['sessions'])
    for key,override in context['overrides'].items():
        if key in by_date:
            by_date[key]['routine_override']=override
    days=[reference-timedelta(days=reference.weekday())+timedelta(days=i) for i in range(7)] if mode!='Mês' else list(calendar.Calendar().itermonthdates(reference.year,reference.month))
    st.caption('Escolha um dia para ver os blocos. Previsões mudam com seus resultados.')
    render_exam_dates(service,days[0].isoformat(),days[-1].isoformat())
    selected=st.session_state.get('calendar_selected',reference.isoformat())
    if selected not in by_date: selected=reference.isoformat()
    st.session_state['calendar_selected']=selected
    if mode=='Agenda':
        with st.container(key='calendar_agenda'):
            for day in days:
                plan=by_date.get(day.isoformat())
                with st.container(border=True,key='bento-calendar-day-'+_day_state(day,plan,today)+'-'+day.isoformat()):
                    left,right=st.columns([1,3])
                    with left: _date_button(day,plan,selected)
                    with right: _day_summary(day,plan,context,today)
    else:
        with st.container(key='calendar_grid'):
            for start in range(0,len(days),7):
                columns=st.columns(7,gap='small')
                for column,day in zip(columns,days[start:start+7]):
                    plan=by_date.get(day.isoformat())
                    with column.container(border=True,key='bento-calendar-day-'+_day_state(day,plan,today)+'-'+day.isoformat()):
                        _date_button(day,plan,selected)
                        _day_summary(day,plan,context,today)
    with st.container(key='calendar_selected_detail'):
        if selected in by_date:_render_selected_day(service,go_record,go_review,today,start_date,selected,by_date[selected],context['view'])
        else:st.info('Fora do período disponível. Escolha outra data no calendário.')
        from .error_cards_ui import render_cards_summary
        render_cards_summary(service.repository,context['view'],selected)
    with st.expander('Programar ou mudar datas dos simulados'):
        render_mock_schedule(service)
    with st.expander('Mais opções do calendário',expanded=bool(st.session_state.get('prevention_enabled'))),st.container(key='calendar_management'):
        if start_date:st.caption('Início do cronograma: '+ '/'.join(reversed(start_date.split('-'))))
        st.caption('As revisões seguintes serão recalculadas com seus resultados; retornos de questões já registrados continuam na agenda.')
        if any(t.get('review_committed') is False for t in context['view']['planning_states']):
            st.caption('O histórico importado forma uma fila de prioridades. Os primeiros contatos são distribuídos dentro da sua carga; não são dívidas de estudo. Alertas se referem a revisões já previstas neste cenário.')
        render_prevention(service)
        render_capacity_summary(service,max(reference.isoformat(),today.isoformat(),start_date or today.isoformat()))
        render_final_review(service)
        render_mock_days(service)


def _render_selected_day(service,go_record,go_review,today,start_date,selected,plan,current_view):
    strategy=service.store.profile()['profile'].get('review_strategy')
    st.subheader('Blocos de '+ '/'.join(reversed(selected.split('-'))))
    for correction in service.exam_learning_agenda():
        if correction['date']==selected:
            st.info('Correção de '+correction['name']+'. '+('Informe os temas errados na aba Simulados → Correção para distribuir a prática.' if correction['needs_details'] else 'Os temas de reforço usam parte da meta normal deste dia.'))
    for task in plan.get('area_tasks',[]):
        st.info(task['institution']+' · '+task['area']+f" · treino de {task['questions']} questões dentro da meta diária. Registre o resultado em Simulados → Treinos por área.")
    override=plan.get('routine_override',{})
    if override.get('mode')=='mock_day': st.success(f"Dia feito por simulado · {override['mock_questions']} questões, separadas dos blocos.")
    elif override.get('mode')=='mock_reserved':
        recorded=selected in service.recorded_mock_days()
        st.info('Resultado do simulado registrado. Consulte os detalhes em Simulados → Resultados.' if recorded else 'Simulado programado. Os blocos normais foram dispensados; veja ou altere a data em Programar ou mudar datas dos simulados.')
        series=service.mock_schedule()
        moved=[r for r in (series or {}).get('topic_changes',[]) if r['before_date']==selected]
        if moved:
            import pandas as pd
            st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Nova data prevista':r['after_date'] or 'Sem vaga no horizonte da prévia'} for r in moved]),hide_index=True,width='stretch')
            st.caption('Fotografia da prévia aplicada. As datas atuais dos próximos blocos acompanham seus resultados e ajustes de rotina.')
        return
    elif override.get('mode')=='final_rest': st.info('Véspera da prova · descanso reservado.')
    elif override.get('mode')=='final_review': st.caption('Programação temporária de revisão final.')
    if plan.get('not_started'):
        st.info('O cronograma ainda não começou neste dia. Escolha uma data a partir de '+ '/'.join(reversed(start_date.split('-')))+'.')
        return
    if plan.get('historical'):
        if not plan['has_plan']: st.info('Dia sem plano salvo. Não presumimos quais temas você deveria ter feito.')
        done=plan.get('done_questions')
        st.caption('Quantidade registrada não informada.' if done is None else f'{done} questões realmente registradas nesse dia.')
        for row in plan.get('delayed_topics',[]): st.warning(row['path'][-1]+f" · {row['days_late']} dias de atraso · abra Reorganizar acima para mudar a data.")
        return
    if selected>today.isoformat() and plan.get('forecast_mode')=='next_contact':
        st.caption('Datas e quantidades previstas para o próximo bloco de cada tema. Os encontros seguintes dependem do resultado; não são compromissos repetidos automaticamente.')
        st.caption(f"Meta deste dia: {plan['target_questions']} questões. A previsão parcial não reduz sua meta; o plano será recalculado após os próximos resultados.")
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
        slug=area_slug(item['path'])
        with st.container(key='bento-calendar-block-'+slug+'-'+item['topic_id']):
            left,right=st.columns([3,1])
            with left:
                state='sem_registro' if item.get('status')=='sem_registro' else item.get('learning_state')
                text=(eyebrow(item['path'][0]+' · '+str(item['questions'])+' questões',slug)
                      +'<div class="o-block-title"><h3>'+escape(item['path'][-1])+'</h3></div>'
                      +'<p class="o-path">'+escape(' › '.join(item['path'][:-1]))+'</p>'
                      +'<div class="o-block-context">'+chip(item['stage']))
                if state:text+=chip('',state)
                text+='</div>'
                if item.get('reason'):text+='<p class="o-reason">'+escape(item['reason'])+'</p>'
                st.html(text)
            if item.get('forecast_basis')=='next_contact' and selected>today.isoformat(): left.caption('Depois deste bloco, data e quantidade da próxima revisão serão recalculadas.')
            if item.get('preventive_priority'): left.caption('Plano preventivo'+(f" · antecipada em {item['anticipated_days']}dia(s)" if item.get('anticipated_days') else ''))
            if item.get('swap_return'): left.caption('Tema remanejado após troca · reserva a partir de '+ '/'.join(reversed(item['reschedule_date'].split('-'))))
            elif (item.get('planner_supply') or {}).get('external_only'): left.caption('Complemento no banco completo')
            elif item.get('rescheduled'): left.caption('Recuperação · vencimento original '+item['original_due'])
            with left:
                render_planner_supply(item)
                render_bank_scope(item,current_view['profile']['min_block'])
            if selected==today.isoformat():
                mode='mistas' if item['new_questions'] and item['repeat_questions'] else 'repetidas' if item['repeat_questions'] else 'novas'
                if strategy=='balanced_v2' and item.get('review_kind') in {'lot_only','combined'} and go_review:
                    with right: render_review_parts(item,selected,go_record,go_review,'calendar')
                elif item.get('review_kind')=='lot_only' and go_review:
                    for lot in item['pending_reviews']:
                        if lot['due_date']<=selected: right.button('Revisar lote',key='calendar_lot_'+lot['session_id'],on_click=go_review,args=(lot,))
                    left.caption('O complemento do bloco pode ser registrado na tela Hoje.')
                else: right.button('Registrar',key='calendar_record_'+item['topic_id'],on_click=go_record,args=(item['topic_id'],item['questions'],mode))
                render_swap_controls(service,selected,item,'calendar')
                from .planner_completion_ui import render_completion_choice
                render_completion_choice(service,current_view,item,'calendar_')
    if selected==today.isoformat():
        from .planner_completion_ui import render_completions
        render_completions(service,current_view)
    if not plan['items']:
        st.info('Descanso programado.' if plan['kind']=='descanso' else 'Os blocos deste dia serão recalculados após os próximos resultados. A ausência de uma previsão não significa que o dia esteja livre.' if plan.get('forecast_mode')=='next_contact' and selected>today.isoformat() else 'Dia sem blocos previstos. Pode ser descanso ou intervalo entre revisões.')
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
