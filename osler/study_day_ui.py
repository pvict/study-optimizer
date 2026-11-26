"""Uma meta em questões, próximos blocos e revisões extras escolhidas pelo aluno."""
from .action_feedback import confirm_button,confirm_submit,notify_success

import streamlit as st
from dataclasses import replace
from .topic_picker_ui import pick_topic
from .study_models import AdaptiveProfile
from .study_trajectory_ui import trajectory_detail
from .study_swap_ui import render_swap_controls
from .study_errors_ui import render_error_context
from .review_parts_ui import render_review_parts


def _change_extra(service,day,topic_id,questions,revision,remove=False,topic_name=None,over_limit=False):
    try:
        if remove: notify_success(service.remove_added_topic(day,topic_id,revision),'Alterações salvas.')
        else:
            notify_success(service.add_topic(day,topic_id,questions,revision,over_limit=over_limit),'Tema adicionado ao plano de hoje.')
            st.session_state['show_pending_today_blocks']=True
        st.session_state.pop('day_form_snapshot',None)
        st.session_state['adaptive_notice']='Revisão retirada do plano. Seus resultados continuam no histórico.' if remove else f'{topic_name} foi adicionado aos blocos de hoje.'
    except ValueError as exc: st.session_state['adaptive_error']=str(exc)


def _day_settings(service,view,day):
    plan=view['plan']
    with st.expander('Ajustar meu dia'):
        st.markdown('**Meta de hoje**')
        from .day_goal_ui import render_day_goal
        render_day_goal(service,view,day)
        st.divider()
        st.markdown('**Temas e divisão da rotina**')
        record=st.session_state.setdefault('distribution_profile_snapshot',service.store.profile())
        p=AdaptiveProfile(**record['configured_profile'])
        with st.form('today_distribution'):
            max_topics=st.number_input('Máximo de temas por dia',min_value=1,max_value=10,value=p.max_topics,step=1,key='today_max_topics',
                                       help='Limite padrão dos blocos planejados. Vale para hoje e os próximos dias; revisões extras adicionadas manualmente podem ultrapassá-lo.')
            share=st.slider('Questões em temas novos (%)',0,100,round(p.new_share*100),step=5,key='today_new_share')
            minimum_share=st.slider('Piso de questões em temas novos (%)',0,100,round(p.minimum_new_share*100),step=5,key='today_minimum_new_share',
                                    help='No adaptativo, preserva esta parcela quando há candidatos e capacidade para um bloco. Nunca ultrapassa a proporção desejada acima. Descanso e compromissos explícitos são preservados.')
            workload_mode=st.radio('Distribuição',['adaptive','fixed'],index=0 if p.workload_mode=='adaptive' else 1,
                                   format_func={'adaptive':'Adaptativa','fixed':'Fixa'}.get,key='today_workload_mode',horizontal=True)
            st.caption(f"Em uma meta de {plan['base_questions']}: {round(plan['base_questions']*share/100)} questões em temas novos e {plan['base_questions']-round(plan['base_questions']*share/100)} em revisões. Revisões incluem diagnóstico de temas já estudados; questões novas do banco podem aparecer nos dois grupos.")
            save_share=confirm_submit('Salvar divisão da rotina',key='save_today_distribution',action_key='study_day_ui_47',
                                      details=f'Máximo de {max_topics} temas por dia, {share}% em temas novos e piso adaptativo de {min(share,minimum_share)}%. Hoje e os próximos dias serão recalculados.')
        if save_share:
            try: notify_success(service.store.save_profile(replace(p,new_share=share/100,minimum_new_share=minimum_share/100,workload_mode=workload_mode,max_topics=int(max_topics)),record['id']),'Alterações salvas.')
            except ValueError:
                st.session_state.pop('distribution_profile_snapshot',None)
                raise
            st.session_state.pop('distribution_profile_snapshot',None)
            st.session_state['adaptive_notice']='Divisão atualizada. Hoje e os próximos dias foram recalculados.'
            st.rerun()


def _block_controls(service,view,item,day,go_record,go_review,hero=False):
    mode='mistas' if item.get('manual_pending') or item['new_questions'] and item['repeat_questions'] else 'repetidas' if item['repeat_questions'] else 'novas'
    if view['profile'].get('review_strategy')=='balanced_v2' and item.get('review_kind') in {'lot_only','combined'}:
        render_review_parts(item,day,go_record,go_review,'study',primary=hero)
    elif item.get('review_kind')=='lot_only':
        lots=[lot for lot in item['pending_reviews'] if lot['due_date']<=day]
        for index,lot in enumerate(lots):
            st.button(f"Revisar lote de {lot['questions']} respostas",key='study_lot_'+lot['session_id'],
                      on_click=go_review,args=(lot,),width='stretch',type='primary' if hero and index==0 else 'secondary')
        complement=max(0,item['questions']-sum(lot['questions'] for lot in lots))
        if complement:
            st.caption(f'Complete o bloco com {complement} questões do tema, registradas separadamente dos lotes.')
            st.button('Registrar complemento',key='study_complement_'+item['topic_id'],on_click=go_record,
                      args=(item['topic_id'],complement,'mistas'),width='stretch',type='primary' if hero and not lots else 'secondary')
    else:
        st.button('Registrar complemento' if (item.get('planner_supply') or {}).get('external_only') else 'Registrar este bloco',key=f"study_{item['topic_id']}",type='primary' if hero else 'secondary',
                  on_click=go_record,args=(item['topic_id'],min(1000000,item['questions']),mode))
    with st.container(key=f"today-options-{item['topic_id']}"), st.expander('Opções do bloco'):
        if not item.get('manual_pending'):
            render_swap_controls(service,day,item)
            from .return_deferral_ui import render_return_deferral
            render_return_deferral(service,view,item)
        from .planner_completion_ui import render_completion_choice
        render_completion_choice(service,view,item)
        if item['added_by_user']:
            confirm_button('Retirar revisão extra',key=f"remove_extra_{item['topic_id']}",on_click=_change_extra,
                           args=(service,day,item['topic_id'],0,view['day']['revision'],True),action_key='study_day_ui_86')
        with st.expander('Ver próximas revisões'):
            if not hero: st.caption(' › '.join(item['path'][:-1])+' · '+item['stage'])
            render_error_context(service,item['path'],day)
            st.write(item['reason'])
            trajectory_detail(item,AdaptiveProfile(**view['profile']),day,limit=5)


def _extra_controls(service,view,day,advance=False):
    _day_settings(service,view,day)
    plan=view['plan']
    if view['states'] and plan['kind']!='descanso':
        with st.expander('Adicionar tema ao dia',expanded=advance or bool(st.session_state.get('extra_topic'))):
            catalog,_=service.catalog(day)
            catalog=list({t['topic_id']:t for t in [*catalog,*[t for t in view['planning_states'] if t.get('group_members')]]}.values())
            chosen=pick_topic(catalog,'extra',st.session_state.get('extra_topic'))
            if chosen:
                selected=chosen['topic_id']
                over_limit=st.checkbox('Acrescentar além dos limites do plano',value=False,key='extra_over_limit')
                already=sum(e['questions'] for e in view['day']['settings']['extra_topics'] if e['topic_id']==selected and not e.get('over_limit'))
                maximum=1000000 if over_limit else min(1000,chosen['total']-already)
                if maximum>0:
                    q=st.number_input('Questões extras',min_value=1,max_value=maximum,value=min(10,maximum),key=f'extra_count_{selected}_{maximum}')
                    override=plan['routine_override']
                    capped='recovery_limit' in override and not view['day']['settings'].get('effective_goal')
                    details=f"Adicionar {q} questões de {chosen['path'][-1]} aos blocos de hoje."
                    if over_limit:
                        details+=' São adicionais à meta e às atividades já previstas.'
                        total=plan['target_questions']+override.get('recovery_reserved',0)+q
                        st.caption(f"Total do dia com retornos externos: {total} questões.")
                        if q>chosen['total']:st.caption(f"Acervo conhecido: {chosen['total']} questões. Use o banco completo ou questões repetidas para complementar.")
                    elif capped:
                        details+=' Elas entram na carga da retomada e podem reduzir as revisões externas previstas para hoje.'
                    confirm_button('Adicionar ao meu dia',on_click=_change_extra,
                                   args=(service,day,selected,int(q),view['day']['revision']),kwargs={'topic_name':chosen['path'][-1],'over_limit':over_limit},
                                   details=details,width='stretch',action_key='study_day_ui_104')
                else: st.caption('A quantidade conhecida desse banco já foi adicionada hoje.')
            st.caption('Só entra no progresso depois que você registrar o resultado.')


def render_study_day(service,go_record,go_review,go_edit=None):
    from .bento_day_ui import render_today
    render_today(service,go_record,go_review,go_edit)
