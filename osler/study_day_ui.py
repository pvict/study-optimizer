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


def _change_extra(service,day,topic_id,questions,revision,remove=False):
    try:
        if remove: notify_success(service.remove_added_topic(day,topic_id,revision),'Alterações salvas.')
        else: notify_success(service.add_topic(day,topic_id,questions,revision),'Alterações salvas.')
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
            save=confirm_submit('Atualizar meta de hoje',action_key='study_day_ui_32')
        if save:
            notify_success(service.configure_day(day,int(questions),'descanso' if rest else 'normal',snapshot['revision']),'Agenda atualizada.')
            st.session_state.pop('day_form_snapshot',None)
            st.session_state['adaptive_notice']='Meta de hoje atualizada.'
            st.rerun()
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
    mode='mistas' if item['new_questions'] and item['repeat_questions'] else 'repetidas' if item['repeat_questions'] else 'novas'
    swap_button=None
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
        action,swap_button=st.columns([1.4,1],gap='small')
        action.button('Registrar complemento' if (item.get('planner_supply') or {}).get('external_only') else 'Registrar este bloco',key=f"study_{item['topic_id']}",type='primary' if hero else 'secondary',
                  on_click=go_record,args=(item['topic_id'],item['questions'],mode))
    render_swap_controls(service,day,item,button_container=swap_button)
    from .planner_completion_ui import render_completion_choice
    render_completion_choice(service,view,item)
    with st.expander('Ver próximas revisões'):
        if not hero: st.caption(' › '.join(item['path'][:-1])+' · '+item['stage'])
        render_error_context(service,item['path'],day)
        st.write(item['reason'])
        trajectory_detail(item,AdaptiveProfile(**view['profile']),day,limit=5)
    if item['added_by_user']:
        confirm_button('Retirar revisão extra',key=f"remove_extra_{item['topic_id']}",on_click=_change_extra,
                  args=(service,day,item['topic_id'],0,view['day']['revision'],True),action_key='study_day_ui_86')


def _extra_controls(service,view,day,advance=False):
    _day_settings(service,view,day)
    plan=view['plan']
    if view['states'] and plan['kind']!='descanso':
        with st.expander('Adiantar revisões',expanded=advance or bool(st.session_state.get('extra_topic'))):
            st.caption('Acrescente questões e um tema só para hoje.')
            catalog,_=service.catalog(day)
            chosen=pick_topic(catalog,'extra',st.session_state.get('extra_topic'))
            if chosen:
                selected=chosen['topic_id']
                already=sum(e['questions'] for e in view['day']['settings']['extra_topics'] if e['topic_id']==selected)
                maximum=min(1000,chosen['total']-already)
                if maximum>0:
                    q=st.number_input('Questões extras',min_value=1,max_value=maximum,value=min(10,maximum),key=f'extra_count_{selected}_{maximum}')
                    confirm_button('Adicionar ao meu dia',on_click=_change_extra,args=(service,day,selected,int(q),view['day']['revision']),width='stretch',action_key='study_day_ui_104')
                else: st.caption('A quantidade conhecida desse banco já foi adicionada hoje.')
            st.caption('Só entra no progresso depois que você registrar o resultado.')


def render_study_day(service,go_record,go_review,go_edit=None):
    from .bento_day_ui import render_today
    render_today(service,go_record,go_review,go_edit)
