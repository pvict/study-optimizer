"""Composição de Hoje; os controles e regras existentes continuam em seus módulos."""
from .ui_help import explain
from html import escape
from math import ceil
from time import monotonic
from datetime import timedelta

import streamlit as st

from .bento import area_slug,AREA_LABELS,eyebrow,chip,ring
from .planner_service import today_local
from .study_dashboard import date_label,hero_state,pause_remaining,week_summary
from .study_feedback import day_activity
from .study_activity_ui import render_day_activity
from .study_components import render_planner_supply,render_bank_scope
from .study_navigation_ui import go_view
from .study_swap_ui import render_swap_history
from .study_models import AdaptiveProfile
from .exam_goals import ExamGoals,principal_exam
from .final_review_ui import render_approach
from .weekly_review_ui import render_absence_notice,render_weekly_review


def _import():
    st.session_state['advanced_view']='Dados e classificação'
    go_view('Ferramentas')


def _advance():
    st.session_state['bento_advance_open']=True


def _reschedule_area():
    st.session_state['mock_tab_pending']='Treinos por área'
    st.session_state['area_reschedule_requested']=True
    go_view('Plano de questões','Simulados')


def _open_area(task):
    if task.get('completed') and task.get('exam_key'):
        _open_correction(task['exam_key'])
    else:
        st.session_state['mock_tab_pending']='Treinos por área'
        st.session_state['area_result_pending']=task['id']
        go_view('Plano de questões','Simulados')


def _open_correction(exam_key):
    st.session_state['mock_tab_pending']='Correção'
    st.session_state['mock_selection_pending']=exam_key
    go_view('Plano de questões','Simulados')


def _dismiss_pause():
    st.session_state['bento_pause_dismissed']=True
    st.session_state.pop('bento_pause_until',None)


def _start_pause():
    st.session_state['bento_pause_until']=monotonic()+600


@st.fragment(run_every=1)
def _pause():
    if st.session_state.get('bento_pause_dismissed'):return
    with st.container(key='bento-pause'):
        st.subheader('Um intervalo, se quiser')
        explain('Você já registrou um bloco hoje. Pode fazer uma pausa e voltar quando preferir.')
        remaining=pause_remaining(st.session_state.get('bento_pause_until'),monotonic())
        if remaining is None:
            st.button('Iniciar pausa de 10 min',key='bento_pause_start',icon=':material/timer:',on_click=_start_pause)
        elif remaining:
            st.markdown(f'**{remaining//60:02d}:{remaining%60:02d}**')
            st.caption('O plano continua disponível durante a pausa.')
        else:
            st.write('Pausa concluída. Continue quando quiser.')
        st.button('Dispensar pausa',key='bento_pause_dismiss',on_click=_dismiss_pause)


def _block(service,view,item,day,go_record,go_review,hero=False):
    from .study_day_ui import _block_controls
    slug=area_slug(item['path'])
    with st.container(key='bento-hero-'+slug if hero else 'bento-block-'+item['topic_id']):
        label=AREA_LABELS[slug] or item['path'][0]
        state='sem_registro' if item.get('status')=='sem_registro' else item.get('learning_state')
        n=item['questions'];dose=f"{n} "+('questão' if n==1 else 'questões')
        text=(eyebrow(label+' · '+dose,slug)+'<div class="o-block-title"><h3>'+escape(item['path'][-1])+'</h3></div>'
              )
        if hero:
            errors=next((s.get('open_error_count',0) for s in view['planning_states'] if s['topic_id']==item['topic_id']),0)
            text+='<p class="o-path">'+escape(' › '.join(item['path'][:-1]))+'</p><div class="o-block-context">'+chip('',state)+chip(item['stage'])
            if errors:text+=chip(str(errors)+(' erro aberto' if errors==1 else ' erros abertos'))
            text+='</div>'
            if st.session_state.get('show_explanations',False):
                text+='<p class="o-reason">'+escape(item['reason'])+'</p>'
        st.html(text)
        if item.get('group_members'):
            st.html(chip(f"Agrupamento · {len(item['group_member_paths'])} temas"))
            with st.popover('Ver temas agrupados',icon=':material/account_tree:'):
                st.markdown('**'+escape(item['path'][-1])+'**')
                for path in item['group_member_paths']:
                    st.write(' › '.join(path[len(item['path']):]))
        if hero and view['time_source']=='Mediana de blocos registrados':
            minutes=ceil(n*view['plan']['effective_profile']['minutes_per_question'])
            st.caption(f'≈ {minutes} min · estimativa a partir dos seus blocos')
        render_planner_supply(item)
        render_bank_scope(item,view['profile']['min_block'])
        notices=[]
        if item.get('review_kind')=='lot_only':notices.append('Retorno de respostas sem convicção · a revisão completa mantém sua própria data.')
        if item.get('preventive_priority'):notices.append('Prioridade do plano preventivo')
        if item.get('swap_return'):notices.append('Tema remanejado após troca · reserva a partir de '+ '/'.join(reversed(item['reschedule_date'].split('-'))))
        elif (item.get('planner_supply') or {}).get('external_only'):notices.append('Complemento no banco completo')
        elif item.get('correction'):notices.append('Reforço dos erros do simulado · data reservada '+date_label(item['reschedule_date']))
        elif item.get('rescheduled'):notices.append('Recuperação agendada · atraso original desde '+item['original_due'])
        if item['added_by_user']:notices.append(f"Adicionado por você · {item['extra_pending']} questões extras · só hoje")
        if notices:st.caption(' · '.join(notices))
        _block_controls(service,view,item,day,go_record,go_review,hero)


def _hero_empty(state,plan):
    with st.container(key='bento-state-'+state):
        if state=='empty':
            st.subheader('Seu estudo começa aqui')
            st.write('Importe seu relatório de questões para montar o plano com o que você já estudou.')
            st.button('Importar relatório',key='bento_import',type='primary',icon=':material/upload_file:',on_click=_import)
        elif state=='rest':
            st.subheader('Hoje é descanso')
            st.write('A meta de questões está dispensada. O plano continua no próximo dia, sem dívida de questões.')
            st.caption('Véspera de prova reservada. Para alterar, abra a revisão final no Calendário.' if plan.get('routine_override',{}).get('mode')=='final_rest' else 'Para estudar hoje, abra Ajustar meu dia abaixo.')
        elif state=='mock':
            st.subheader('Hoje é dia de simulado')
            st.write('Os blocos normais estão dispensados. Registre o resultado ou altere a data em Simulados.')
            if plan['routine_override'].get('mock_questions'):st.caption(f"{plan['routine_override']['mock_questions']} questões no simulado · resultado separado dos blocos.")
            st.caption('Registre o resultado e os temas errados na seção Simulado de hoje, no início desta página.')
        elif state=='not_started':
            st.subheader('Tudo pronto para começar')
            st.info('Seu cronograma começa em '+ '/'.join(reversed(plan['start_date'].split('-')))+'. Até lá, não há meta diária nem faltas no aplicativo.')
            st.caption('Seu histórico importado já está disponível em Temas.')
        elif state=='complete':
            st.subheader('Meta registrada')
            st.write('Os resultados de hoje já estão no histórico. Se quiser continuar, acrescente uma revisão ao dia.')
            st.button('Adiantar revisões',key='bento_advance',icon=':material/add:',on_click=_advance)
        else:
            st.subheader('Seu dia está livre de blocos automáticos')
            st.write('Consulte o Calendário ou acrescente um tema em Adiantar revisões.')


def _today_ring(plan,state):
    with st.container(key='bento-today-ring'):
        summary=(f"{plan['done_questions']} de {plan['target_questions']} questões registradas" if plan['target_questions'] else f"{plan['done_questions']} questões registradas · sem meta de blocos hoje")
        st.html('<h3>Hoje</h3><p class="o-path">'+summary+'</p>')
        # SVG fixo da biblioteca visual; st.html sanitiza e remove SVG.
        dist=plan['distribution']
        remaining=f"Restam {plan['questions']} no plano" if plan['target_questions'] else 'Sem meta de blocos hoje'
        if state=='empty':remaining='Plano disponível após importar o relatório'
        text=f"{dist['planned_new']} em temas novos · {dist['planned_reviews']} em revisões e diagnósticos."
        if plan.get('area_tasks'): text+=' '+str(sum(t['questions'] for t in plan['area_tasks'] if not t['completed']))+' em treino por área.'
        st.markdown('<div class="o-ring-row">'+ring(plan['done_questions'],plan['target_questions'],80)+'<div><strong>'+remaining+'</strong><p>'+text+'</p></div></div>',unsafe_allow_html=True)


def _rhythm(summary):
    labels={'done':'Com estudo','partial':'Parcial','rest':'Descanso','future':'Próximo dia','missing':'Sem registro'}
    symbols={'done':'✓','partial':'½','rest':'—','future':'·','missing':'·'}
    points=''.join('<div class="o-week-day" aria-label="'+escape(d['date']+': '+labels[d['status']])+'"><span>'+letter+'</span><b class="o-day-'+d['status']+'">'+symbols[d['status']]+'</b></div>' for d,letter in zip(summary['days'],['S','T','Q','Q','S','S','D']))
    with st.container(key='bento-rhythm'):
        st.html('<h3>Ritmo da semana</h3><div class="o-week">'+points+'</div>')
        st.caption(f"{summary['study_days']} de 7 dias com estudo · {summary['rest_days']} de descanso")
        st.caption('✓ Estudo · ½ Parcial · — Descanso')


def _metrics(summary,exam):
    with st.container(key='bento_week_metrics'):
        a,b,c,d=st.columns(4,gap='medium')
        with a,st.container(key='bento-metric-volume'):
            st.metric('Questões na semana',str(summary['questions']))
            st.caption(f"Semana anterior: {summary['previous_questions']}")
            explain('Blocos registrados; inclui repetições.')
        with b,st.container(key='bento-metric-accuracy'):
            st.metric('Acerto em novas','—' if summary['new_accuracy'] is None else f"{100*summary['new_accuracy']:.1f}%".replace('.',','))
            st.caption(f"n = {summary['new_n']} questões novas")
            explain('Contagens exatas nesta semana. Repetidas, mistas, simulados e PDFs separados.')
            if summary['new_unknown']:st.caption(f"{summary['new_unknown']} novas sem acerto exato informado, fora do percentual.")
        with c,st.container(key='bento-metric-mastery'):
            st.metric('Temas dominados','—' if summary['mastered'] is None else str(summary['mastered']))
            if summary['mastered'] is None:st.caption('Importe um relatório para acompanhar os temas.')
            else:explain('Estado atual dos temas registrados.')
        with d,st.container(key='bento-metric-exam'):
            n=summary['exam_days']
            st.metric('Dias até a prova','—' if n is None or n<0 else str(n))
            st.caption('Cadastre sua prova em Ajustes → Minhas provas.' if exam is None else exam['institution']+' · '+ '/'.join(reversed(exam['exam_date'].split('-'))))


def _open_mock_section(section):
    st.session_state['mock_tab_pending']=section
    go_view('Plano de questões','Simulados')


def _full_mocks_today(service,plan,day):
    from .mock_exams import MockExams
    results=[r for r in MockExams(service.repository).active()
             if r['exam']['day']==day and not r['exam'].get('practice_id')]
    scheduled=[r for r in (service.mock_schedule(day) or {}).get('occurrences',[])
               if r.get('date')==day and r.get('status')=='reserved']
    rows=[]
    for item in scheduled:
        match=next((r for r in results if item.get('name') and r['exam']['name']==item['name']),None)
        if match is None and len(scheduled)==1 and len(results)==1: match=results[0]
        rows.append({'name':item.get('name') or (match['exam']['name'] if match else None),
                     'recorded':match is not None})
    if not rows:
        rows=[{'name':r['exam']['name'],'recorded':True} for r in results]
    if not rows and plan.get('routine_override',{}).get('mode') in {'mock_day','mock_reserved'}:
        rows=[{'name':None,'recorded':False}]
    return rows


def _render_full_mocks_today(service,plan,day):
    from .mock_workflow_ui import render_mock_workflow
    scheduled=_full_mocks_today(service,plan,day)
    with st.expander('Simulado de hoje · registrar resultado e temas errados',expanded=bool(scheduled)):
        render_mock_workflow(service,'today_mock_flow')


def render_today(service,go_record,go_review,go_edit=None):
    from .study_day_ui import _extra_controls
    study_today=today_local();day=study_today.isoformat()
    with st.container(key='bento_header'):
        heading,stamp=st.columns([2,1],gap='medium',vertical_alignment='center')
        with heading:
            name=st.session_state.get('interface_name','')
            if name:
                import re
                name=re.sub(r'([\\`*_{}\[\]()#+\-.!|>])',r'\\\1',name)
            st.title('Olá'+(', '+name if name else ''))
            explain('Um bloco de cada vez.')
        with stamp:st.html('<span class="o-date">'+escape(date_label(day))+'</span>')
    with st.spinner('Preparando seu plano…'):
        view=service.overview(day)
        service.remember_day(view)
        if service.agenda.token()!=view['planning_token']:
            view=service.overview(day)
    plan=view['plan'];state=hero_state(view);activity=day_activity(view)
    exam=principal_exam(AdaptiveProfile(**view['profile']),ExamGoals(service.repository).active(),day)
    exam=exam['target'] if exam else None
    summary=week_summary(view,service.store.days(),service.guide.days(),exam,service.recorded_mock_days())
    render_approach(service)
    _render_full_mocks_today(service,plan,day)
    if plan.get('routine_override',{}).get('mode')=='external_day':
        from .action_feedback import confirm_button,notify_success
        external=plan['routine_override']
        with st.container(border=True):
            st.subheader('Hoje: revisões na Osler')
            st.write(f"Você informou {external['external_done']} questões feitas. Restam {external['external_target']-external['external_done']} para o limite de {external['external_target']} de hoje.")
            st.info('Complete somente as questões restantes na Osler. Não há blocos extras do app para hoje.')
            with st.expander('Sobre esta contagem'):
                st.write('Volume informado manualmente, sem atribuição de temas, acertos ou convicção. Ao registrar os resultados por tema, confira as quantidades para evitar duplicação.')
            if confirm_button('Voltar ao plano do app hoje',action_key='resume_external_day'):
                record=next(r for r in view['agenda']['active'] if r.get('scope')=='external_day' and r['created_day']==day)
                notify_success(service.cancel_replan(record['id'],view['planning_token']),'Plano de hoje retomado.')
                st.rerun()
        from .error_cards_ui import render_cards_summary
        render_cards_summary(service.repository,view)
        return
    from .recovery_ui import render_recovery
    render_recovery(service,view)
    render_absence_notice(service,day)
    if plan.get('capacity',{}).get('new_floor_shortfall'):
        st.warning('O piso de temas novos não coube nos blocos disponíveis. Confira o máximo de temas e a divisão em Ajustar meu dia; compromissos já reservados continuam protegidos.')
    waiting=[r for r in view['agenda'].get('area_practice',[]) if r.get('status')=='waiting']
    if waiting:
        st.warning(f'{len(waiting)} treino(s) atrasado(s) sem vaga para recuperação. Ajuste as datas ou a carga em Simulados → Treinos por área.')
    for task in plan.get('area_tasks',[]):
        with st.container(border=True,key='bento-area-today-'+task['id']):
            st.subheader(task['institution']+' · '+task['area'])
            if task.get('recovery'):st.warning('Treino atrasado desde '+date_label(task['missed_date'])+' · recuperado no plano de hoje.')
            st.write(f"Treino por área · {task['done']} questões registradas" if task['completed'] else f"Treino por área · {task['questions']} questões dentro da meta de hoje")
            explain('Misture os temas dessa área no banco da instituição. O resultado da área fica separado dos percentuais por tema.')
            st.button('Ver resultado e corrigir' if task['completed'] else 'Registrar treino por área',key='area_today_'+task['id'],on_click=_open_area,args=(task,))
            if not task['completed']:
                st.button('Reagendar treino',key='move_area_today_'+task['id'],on_click=_reschedule_area)
    corrections=[r for r in service.exam_learning_agenda() if r['date']==day]
    if corrections:
        with st.container(border=True,key='bento-correction-today'):
            st.subheader('Dia de corrigir e reforçar')
            for correction in corrections:
                st.write(correction['name']+' · '+('informe os temas errados em Simulados → Correção' if correction['needs_details'] else 'os temas do reforço estão nos blocos do plano'))
                st.button('Abrir correção deste resultado',key=f"correction_today_{corrections.index(correction)}_{correction['exam_key']}",on_click=_open_correction,args=(correction['exam_key'],))
    with st.container(key='bento_top'):
        main,side=st.columns([2,1],gap='medium')
        with main:
            if state=='study':_block(service,view,plan['items'][0],day,go_record,go_review,True)
            else:_hero_empty(state,plan)
        with side:
            _today_ring(plan,state)
            _rhythm(summary)
    with st.container(key='bento_body'):
        work,support=st.columns([2,1],gap='medium')
        with work,st.container(key='bento_work'):
            st.subheader('Blocos de questões')
            done_label=f"Feito hoje ({activity['questions']})"
            if st.session_state.get('today_blocks_tab','').startswith('Feito hoje'):
                st.session_state['today_blocks_tab']=done_label
            remaining,completed=st.tabs(['Para fazer',done_label],key='today_blocks_tab',on_change='rerun')
            if completed.open:
                with completed:render_day_activity(view,go_edit)
            if remaining.open:
              with remaining:
                if plan.get('excess_done_questions'):st.write(f"{plan['excess_done_questions']} questões além dos blocos previstos. Elas contam no seu total e no desempenho, sem substituir os outros temas de hoje.")
                items=plan['items'][1:] if state=='study' else plan['items']
                for item in items:_block(service,view,item,day,go_record,go_review)
                if not items:st.caption('O próximo bloco está destacado acima.' if state=='study' else 'Nenhum outro bloco para hoje.')
                freed=sum(r['skipped_questions'] for r in plan.get('planner_completions',[]))
                if plan['kind']!='descanso' and view['states'] and plan['questions']<max(0,plan['target_questions']-plan['done_questions']-freed):
                    st.info('Parte da meta não pôde ser distribuída com os temas e limites atuais. Adicione outro tema ou ajuste o número de temas em Ajustes.')
            from .planner_completion_ui import render_completions
            render_completions(service,view)
        with support:
            if st.session_state.get('bento_pause_day')!=day:
                st.session_state['bento_pause_day']=day
                st.session_state.pop('bento_pause_dismissed',None)
                st.session_state.pop('bento_pause_until',None)
            if activity['blocks'] and not st.session_state.get('bento_pause_dismissed'):_pause()
            with st.container(key='bento-tools'):
                st.subheader('Seu dia, do seu jeito')
                # Expandir o atalho sem alterar os dados do dia.
                advance=st.session_state.pop('bento_advance_open',False)
                _extra_controls(service,view,day,advance)
                st.caption(f"Dia de estudo até {study_today+timedelta(days=1):%d/%m} às 04h · Brasília.")
    st.subheader('Sua semana')
    _metrics(summary,exam)
    with st.expander('Detalhes do dia e do plano'):
        from .error_cards_ui import render_cards_summary
        render_cards_summary(service.repository,view)
        render_swap_history(service,view)
        from .return_deferral_ui import render_return_deferral_history
        render_return_deferral_history(service,view)
        if view['profile'].get('return_mode')=='theme' and view.get('reference_review_queue'):
            with st.expander('Histórico dos retornos de sete dias'):
                st.write('Referência dos lotes registrados. Neste modo, a prática é organizada por tema; estes lotes não acrescentam tarefas à agenda.')
                st.dataframe([{'Tema':q['path'][-1],'Respostas':q['questions'],'Data de referência':q['due_date']}
                              for q in view['reference_review_queue']],hide_index=True,width='stretch')
        due=[q for q in view['review_queue'] if q['due_date']<=day]
        if due and plan['kind']!='descanso':
            st.subheader('Respostas sem convicção')
            st.caption('Lotes com retorno para hoje. Fazem parte da meta do dia.')
            for item in due[:4]:
                st.markdown('**'+item['path'][-1]+f" · {item['questions']} pendentes**")
                st.button('Revisar este lote',key='queue_'+item['session_id'],on_click=go_review,args=(item,),width='stretch')
        for key,label in [('extra_questions','Questões extras adicionadas'),('overrun_questions','Questões acima da meta anterior preservadas'),('excess_done_questions','Questões além dos blocos previstos, sem substituir outros temas')]:
            if plan.get(key):st.caption(f'{label}: {plan[key]}')
        capacity=plan.get('capacity',{})
        if capacity.get('mode')=='adaptive' and capacity['effective_share']<capacity['reference_share']:st.caption('Hoje, mais espaço para revisões. Sua divisão de referência continua salva; o ajuste é recalculado a cada dia.')
        if capacity.get('intake_future_pressure'):st.caption('Retomadas antigas ganharam espaço na carga de hoje. A previsão de capacidade futura está apertada; os próximos blocos serão recalculados com seus resultados.')
        if capacity.get('initial_capacity_shortfall'):st.caption(f"A carga atual não comporta retomar todo o histórico em {view['profile']['max_contact_gap']} dias. O app prioriza os contatos por evidência, incidência e tempo sem contato; esse prazo não está garantido para todos os temas.")
        if capacity.get('unused_questions'):st.caption(f"{capacity['unused_questions']} questões da meta ficaram livres: respeitamos a dose dos blocos e a capacidade de repetir. Você pode usar Adiantar revisões.")
        override=plan.get('routine_override',{})
        if override.get('mode')=='reviews':st.info('Novos temas pausados hoje pelo plano temporário. Gerencie em Calendário → Reorganizar atrasos.')
        elif override.get('mode')=='extra':st.info(f"Plano temporário: até {override['extra_questions']} questões adicionais de revisão hoje. Seu padrão está preservado.")
        elif override.get('mode')=='final_review':st.info('Revisão final · priorize os conceitos dos erros abertos. A programação temporária pode ser desfeita no Calendário.')
        st.write('O plano combina incidência, desempenho, tamanho da amostra e tempo sem contato. O tempo não limita a quantidade de questões.')
        if plan['distribution']['adjusted']:st.caption('A proporção precisou ser aproximada por disponibilidade, blocos mínimos ou limite de temas. Revisões extras ficam fora da divisão automática.')
        for warning in view['warnings']:st.caption(warning)
        st.caption('A meta de 90% orienta a preparação. Não é previsão de aprovação. Flashcards seguem uma meta separada das questões.')
        render_weekly_review(service,day)
        _plan_download(service,view)


def _plan_download(service,view):
    from pathlib import Path
    stamp=(view['date'],view['planning_token'])
    if view['plan']['items'] and st.button('Preparar plano para download'):
        st.session_state['study_download_path']=str(service.export(view))
        st.session_state['study_download_stamp']=stamp
    path=Path(st.session_state.get('study_download_path',''))
    if path.is_file():
        current=st.session_state.get('study_download_stamp')==stamp
        if not current:st.caption('A exportação anterior foi preservada. O plano mudou; prepare um novo arquivo para baixar o plano atual.')
        st.download_button('Baixar plano de questões' if current else 'Baixar exportação anterior',path.read_bytes(),'plano.csv','text/csv')
