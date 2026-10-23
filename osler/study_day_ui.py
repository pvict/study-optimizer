"""Uma meta em questões, próximos blocos e revisões extras escolhidas pelo aluno."""
import streamlit as st
from dataclasses import replace
from datetime import timedelta

from .planner_service import today_local
from .topic_picker_ui import pick_topic
from .study_models import AdaptiveProfile
from .study_trajectory_ui import trajectory_detail
from .study_components import block_heading,block_context
from .study_activity_ui import render_day_activity
from .study_feedback import day_activity
from .study_swap_ui import render_swap_controls,render_swap_history
from .study_errors_ui import render_error_context
from .final_review_ui import render_approach


def _change_extra(service,day,topic_id,questions,revision,remove=False):
    try:
        if remove: service.remove_added_topic(day,topic_id,revision)
        else: service.add_topic(day,topic_id,questions,revision)
        st.session_state.pop('day_form_snapshot',None)
        st.session_state['adaptive_notice']='Revisão retirada do plano. Seus resultados continuam no histórico.' if remove else 'Revisão adicionada. A meta mudou só para hoje.'
    except ValueError as exc: st.session_state['adaptive_error']=str(exc)


def _day_settings(service,view,day):
    plan=view['plan']
    with st.expander('Ajustar meu dia'):
        st.markdown('**Meta de hoje**')
        cached=st.session_state.get('day_form_snapshot')
        if not cached or cached['day']!=day: st.session_state['day_form_snapshot']=view['day']
        snapshot=st.session_state['day_form_snapshot']
        with st.form('day_goal'):
            questions=st.number_input('Quantas questões quer fazer hoje?',min_value=1,max_value=1000,value=snapshot['settings']['questions'],key='day_questions')
            rest=st.checkbox('Hoje é dia de descanso',value=snapshot['settings']['kind']=='descanso',key='day_rest')
            st.caption('Vale só para hoje. O padrão dos próximos dias fica em Ajustes.')
            save=st.form_submit_button('Atualizar meta de hoje')
        if save:
            service.configure_day(day,int(questions),'descanso' if rest else 'normal',snapshot['revision'])
            st.session_state.pop('day_form_snapshot',None)
            st.session_state['adaptive_notice']='Meta de hoje atualizada.'
            st.rerun()
        st.divider()
        st.markdown('**Dividir novos e revisões**')
        record=st.session_state.setdefault('distribution_profile_snapshot',service.store.profile())
        p=AdaptiveProfile(**record['configured_profile'])
        with st.form('today_distribution'):
            share=st.slider('Questões em temas novos (%)',0,100,round(p.new_share*100),step=5,key='today_new_share')
            workload_mode=st.radio('Distribuição',['adaptive','fixed'],index=0 if p.workload_mode=='adaptive' else 1,
                                   format_func={'adaptive':'Adaptativa','fixed':'Fixa'}.get,key='today_workload_mode',horizontal=True)
            st.caption(f"Em uma meta de {plan['base_questions']}: {round(plan['base_questions']*share/100)} questões em temas novos e {plan['base_questions']-round(plan['base_questions']*share/100)} em revisões. Revisões incluem diagnóstico de temas já estudados; questões novas do banco podem aparecer nos dois grupos.")
            save_share=st.form_submit_button('Salvar divisão da rotina',key='save_today_distribution')
        if save_share:
            try: service.store.save_profile(replace(p,new_share=share/100,workload_mode=workload_mode),record['id'])
            except ValueError:
                st.session_state.pop('distribution_profile_snapshot',None)
                raise
            st.session_state.pop('distribution_profile_snapshot',None)
            st.session_state['adaptive_notice']='Divisão atualizada. Hoje e os próximos dias foram recalculados.'
            st.rerun()


def render_study_day(service,go_record,go_review,go_edit=None):
    study_today=today_local()
    day=study_today.isoformat()
    st.caption(f"Dia de estudo: {study_today:%d/%m/%Y} · encerra em {study_today+timedelta(days=1):%d/%m} às 04h (Brasília).")
    view=service.overview(day)
    service.remember_day(view)
    plan=view['plan']
    render_approach(service)
    routine=plan.get('routine_override',{})
    if routine.get('mode')=='mock_day':
        st.success(f"Dia feito por simulado · {routine['mock_questions']} questões. O resultado fica separado dos blocos.")
    elif routine.get('mode')=='final_rest': st.info('Véspera da prova · descanso reservado pela revisão final.')
    elif routine.get('mode')=='final_review': st.info('Revisão final · priorize os conceitos dos erros abertos. A programação temporária pode ser desfeita no Calendário.')
    if plan.get('not_started'):
        st.info('Seu cronograma começa em '+ '/'.join(reversed(plan['start_date'].split('-')))+'. Até lá, não há meta diária nem faltas no aplicativo.')
        st.caption('Seu histórico da Osler já está disponível em Temas. O Calendário mostra os blocos a partir do início; os contatos anteriores continuam orientando as prioridades.')
        render_day_activity(view,go_edit)
        return
    with st.container(key='study_summary'):
        st.html(f'<div class="study-progress-summary"><strong>{plan["done_questions"]} de {plan["target_questions"]} questões registradas</strong><span>{plan["questions"]} para fazer no plano</span></div>')
        if plan['target_questions']:
            st.progress(min(1.,plan['done_questions']/plan['target_questions']))
        dist=plan['distribution']
        st.caption(f"Plano restante: {dist['planned_new']} questões em temas novos · {dist['planned_reviews']} em revisões e diagnósticos.")
        if plan['extra_questions']: st.caption(f"{plan['base_questions']} da meta + {plan['extra_questions']} que você adicionou para adiantar.")
        if plan['overrun_questions']: st.caption(f"{plan['overrun_questions']} questões já feitas acima da meta anterior foram preservadas nas revisões extras.")
    override=plan.get('routine_override',{})
    capacity=plan.get('capacity',{})
    if capacity.get('mode')=='adaptive':
        if capacity['effective_share']<capacity['reference_share']: st.caption('Hoje, mais espaço para revisões. Sua divisão de referência continua salva; o ajuste é recalculado a cada dia.')
        if capacity.get('unused_questions'): st.caption(f"{capacity['unused_questions']} questões da meta ficaram livres: respeitamos a dose dos blocos e a capacidade de repetir. Você pode usar Adiantar revisões.")
    if override.get('mode')=='reviews': st.info('Novos temas pausados hoje pelo plano temporário. Gerencie em Calendário → Reorganizar atrasos.')
    elif override.get('mode')=='extra': st.info(f"Plano temporário: até {override['extra_questions']} questões adicionais de revisão hoje. Seu padrão está preservado.")
    work,extra=st.columns([1.85,1],gap='large')
    with work,st.container(key='study_work'):
        st.subheader('Blocos de questões')
        activity=day_activity(view)
        remaining,completed=st.tabs(['Para fazer',f"Feito hoje ({activity['questions']})"])
        with completed: render_day_activity(view,go_edit)
        with remaining:
            if plan['kind']=='descanso':
                st.info('A meta normal foi dispensada neste dia. Para retomar, desfaça a programação no Calendário ou em Simulados.' if routine.get('mode') in {'mock_day','final_rest'} else 'Descanse hoje. O plano recomeça sem dívida de questões. Para retomar agora, abra Ajustar meu dia.')
            elif not view['states']: st.info('Comece importando seu relatório de questões em Arquivos e ferramentas → Dados e classificação → Importar relatórios.')
            elif not plan['items']:
                if plan['done_questions']>=plan['target_questions']: st.success('Meta registrada. Se quiser continuar, abra Adiantar revisões.')
                else: st.info('Nenhum bloco automático para hoje. Consulte o Calendário ou abra Adiantar revisões.')
            for index,item in enumerate(plan['items'],1):
                with st.container(border=True,key=f'study_block_{index}'):
                    block_heading(item)
                    st.caption(' › '.join(item['path'][:-1]))
                    block_context(item)
                    render_error_context(service,item['path'],day)
                    if item.get('review_kind')=='lot_only': st.caption('Retorno de respostas sem convicção · a revisão completa do tema mantém sua própria data.')
                    if item.get('preventive_priority'): st.caption('Prioridade do plano preventivo')
                    if item.get('swap_return'): st.caption('Tema remanejado após troca · reserva a partir de '+ '/'.join(reversed(item['reschedule_date'].split('-'))))
                    elif item.get('rescheduled'): st.caption('Recuperação agendada · atraso original desde '+item['original_due'])
                    if item['added_by_user']: st.caption(f"Adicionado por você · {item['extra_pending']} questões extras neste bloco · só hoje")
                    elif item['priority']=='urgente': st.caption('Prioridade urgente · comece por aqui')
                    mode='mistas' if item['new_questions'] and item['repeat_questions'] else 'repetidas' if item['repeat_questions'] else 'novas'
                    if item.get('review_kind')=='lot_only':
                        lots=[lot for lot in item['pending_reviews'] if lot['due_date']<=day]
                        for lot in lots:
                            st.button(f"Revisar lote de {lot['questions']} respostas",key='study_lot_'+lot['session_id'],
                                      on_click=go_review,args=(lot,),width='stretch')
                        complement=max(0,item['questions']-sum(lot['questions'] for lot in lots))
                        if complement:
                            st.caption(f'Complete o bloco com {complement} questões do tema, registradas separadamente dos lotes.')
                            st.button('Registrar complemento',key='study_complement_'+item['topic_id'],on_click=go_record,
                                      args=(item['topic_id'],complement,'mistas'),width='stretch')
                    else:
                        st.button('Registrar este bloco',key=f"study_{item['topic_id']}",type='primary' if index==1 else 'secondary',
                                  on_click=go_record,args=(item['topic_id'],item['questions'],mode))
                    with st.expander('Ver próximas revisões'):
                        st.write(item['reason'])
                        trajectory_detail(item,AdaptiveProfile(**view['profile']),day,limit=5)
                    render_swap_controls(service,day,item)
                    if item['added_by_user']:
                        st.button('Retirar revisão extra',key=f"remove_extra_{item['topic_id']}",on_click=_change_extra,
                                  args=(service,day,item['topic_id'],0,view['day']['revision'],True))
            if plan['kind']!='descanso' and view['states'] and plan['questions']<max(0,plan['target_questions']-plan['done_questions']):
                st.info('Parte da meta não pôde ser distribuída com os temas e limites atuais. Adicione outro tema ou ajuste o número de temas em Ajustes.')
    with extra,st.container(key='study_support'):
        render_swap_history(service,view)
        due=[q for q in view['review_queue'] if q['due_date']<=day]
        if due and plan['kind']!='descanso':
            st.subheader('Respostas sem convicção')
            st.caption('Lotes com retorno para hoje. Fazem parte da meta do dia.')
            for item in due[:4]:
                with st.container(border=True):
                    st.markdown('**'+item['path'][-1]+f" · {item['questions']} pendentes**")
                    st.button('Revisar este lote',key='queue_'+item['session_id'],on_click=go_review,args=(item,),width='stretch')
        _day_settings(service,view,day)
        if view['states'] and plan['kind']!='descanso':
            with st.expander('Adiantar revisões',expanded=bool(st.session_state.get('extra_topic'))):
                st.caption('Acrescente questões e um tema só para hoje.')
                catalog,_=service.catalog(day)
                chosen=pick_topic(catalog,'extra',st.session_state.get('extra_topic'))
                if chosen:
                    selected=chosen['topic_id']
                    already=sum(e['questions'] for e in view['day']['settings']['extra_topics'] if e['topic_id']==selected)
                    maximum=min(1000,chosen['total']-already)
                    if maximum>0:
                        q=st.number_input('Questões extras',min_value=1,max_value=maximum,value=min(10,maximum),key=f'extra_count_{selected}_{maximum}')
                        st.button('Adicionar ao meu dia',on_click=_change_extra,args=(service,day,selected,int(q),view['day']['revision']),width='stretch')
                    else: st.caption('A quantidade conhecida desse banco já foi adicionada hoje.')
                st.caption('Só entra no progresso depois que você registrar o resultado.')
        st.caption('Meta global nos temas: '+f"{view['profile']['target_accuracy']:g}%"+' · Flashcards: referência de 500 revisões/dia, separada das questões.')
    with st.expander('Como este plano foi escolhido'):
        st.write('O plano combina incidência, desempenho, tamanho da amostra e tempo sem contato. Erros em questões novas, repetidas ou mistas podem dar prioridade à revisão. A quantidade do dia é definida por você; o tempo não limita o plano.')
        if dist['adjusted']: st.caption('A proporção precisou ser aproximada por disponibilidade, blocos mínimos ou limite de temas. Revisões extras ficam fora da divisão automática.')
        for warning in view['warnings']: st.caption(warning)
        small=sum(t['small_bank'] for t in view['planning_states'])
        if small: st.caption(f'{small} temas têm menos questões conhecidas que o mínimo por bloco. Veja os temas e o complemento necessário no plano de revisões em Temas e estatísticas.')
        st.caption('A meta de 90% orienta a preparação. Não é uma previsão de aprovação; intervalos de revisão são regras iniciais de planejamento.')
    if plan['items']:
        if st.button('Preparar plano para download'):
            st.session_state['study_download_path']=str(service.export(view))
        from pathlib import Path
        path=Path(st.session_state.get('study_download_path',''))
        if path.is_file(): st.download_button('Baixar plano de questões',path.read_bytes(),'plano.csv','text/csv')
