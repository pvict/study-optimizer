"""Planejamento diário com atualização curta, sem configuração por subtema."""
from .ui_help import explain
from .action_feedback import confirm_button,confirm_submit,notify_success

from dataclasses import replace
from datetime import date
import sqlite3
import uuid

import streamlit as st

from .adaptive_service import AdaptiveService
from .guide_settings_ui import render_guide_settings
from .planner_service import today_local
from .study_models import AdaptiveProfile
from .study_day_ui import render_study_day
from .study_tables_ui import render_topic_table
from .topic_picker_ui import reset_picker
from .study_calendar_ui import render_calendar
from .exam_goals_ui import render_exam_goals
from .exam_goals import ExamGoals
from .study_evolution_ui import render_evolution
from .review_strategy_ui import render_review_strategy
from .study_errors_ui import render_errors
from .mock_exams_ui import render_mock_exams,render_mock_settings
from .final_review_ui import render_exam_weights
from .goal_risk_ui import render_goal_risk
from .study_triage_ui import render_triage
from .parameter_ui import render_parameter_settings
from .consolidated_export import consolidated_csv

VIEWS=['Meu dia','Temas em atenção','Calendário','Evolução','Temas e estatísticas','Registrar resultados','Simulados','Ajustes','Agrupamentos']


def _go_record(topic_id,questions,mode=None):
    reset_picker('record')
    st.session_state.pop('study_saved',None)
    st.session_state['adaptive_view']='Registrar resultados'
    st.session_state['adaptive_topic']=topic_id
    st.session_state['study_n']=questions
    st.session_state['study_kind']='bloco'
    st.session_state['study_mode']=mode or st.session_state.get('last_study_mode','novas')
    st.session_state['study_method']='acertos'
    st.session_state.pop('study_correct',None)
    st.session_state.pop('study_edit',None)
    st.session_state.pop('study_review_of',None)
    st.session_state.pop('study_confident',None)
    st.session_state.pop('study_cards_created',None)
    st.session_state.pop('study_date',None)
    st.session_state.pop('study_duration',None)
    st.session_state.pop('record_search',None)
    st.session_state['study_entry_id']=uuid.uuid4().hex


def _go_review(item):
    from .models import stable_topic_id
    _go_record(stable_topic_id(item['path']),item['questions'],'repetidas')
    st.session_state['study_review_of']=item['session_id']


def _back_to_plan():
    st.session_state['adaptive_view']='Meu dia'


def render_adaptive(repo):
    service=AdaptiveService(repo)
    weight_status=service.store.profile()['weight_policy']
    if not weight_status['allowed']: st.warning(weight_status['reason']+' O conjunto original foi mantido sem esses pesos. Corrija em Ajustes → Minhas provas.')
    if 'last_study_mode' not in st.session_state:
        previous=[r for r in service.store.active(today_local().isoformat()) if r['entry']['kind']=='bloco']
        st.session_state['last_study_mode']=max(previous,key=lambda r:r['id'])['entry']['mode'] if previous else 'novas'
    if st.session_state.get('adaptive_view') not in VIEWS: st.session_state['adaptive_view']='Meu dia'
    view=st.session_state['adaptive_view']
    current=st.session_state['adaptive_view']
    if current not in {'Meu dia','Registrar resultados'}: st.title({'Meu dia':'Seu plano de hoje','Calendário':'Calendário de estudos','Temas e estatísticas':'Temas e desempenho',
              'Temas em atenção':'Temas em atenção','Registrar resultados':'Registrar resultado','Ajustes':'Ajustes do plano','Evolução':'Sua evolução','Simulados':'Seus simulados','Agrupamentos':'Divisão das revisões'}[current])
    if current not in {'Meu dia','Registrar resultados'}: explain({'Meu dia':'Faça os blocos abaixo e registre o resultado para atualizar o plano.',
                'Temas em atenção':'Veja os temas incidentes sem prática, as dificuldades e o tempo sem contato.',
                'Calendário':'Consulte os próximos dias e abra espaço para suas revisões.',
                'Temas e estatísticas':'Encontre o que precisa de atenção e acompanhe seu rendimento.',
                'Registrar resultados':'Registre o que fez. O próximo plano acompanha seus resultados.',
                'Ajustes':'Defina sua rotina uma vez. Ajuste quando precisar.','Evolução':'Enxergue o que já construiu e explore os próximos capítulos da preparação.',
                'Simulados':'Acompanhe simulados, treinos por área e a correção dos erros.','Agrupamentos':'Compare os temas separados com uma divisão por categorias específicas.'}[current])
    if 'adaptive_notice' in st.session_state: st.success(st.session_state.pop('adaptive_notice'))
    if 'adaptive_error' in st.session_state: st.error(st.session_state.pop('adaptive_error'))
    if view!='Ajustes': st.session_state.pop('adaptive_profile_snapshot',None)
    if view!='Ajustes': st.session_state.pop('exam_primary_snapshot',None)
    if view!='Meu dia': st.session_state.pop('day_form_snapshot',None)
    if view!='Meu dia': st.session_state.pop('distribution_profile_snapshot',None)
    if view!='Calendário':
        for key in list(st.session_state):
            if key.startswith('calendar_snapshot_'): st.session_state.pop(key,None)
    try:
        if view=='Meu dia': render_study_day(service,_go_record,_go_review,_edit)
        elif view=='Temas em atenção':
            from .study_attention_ui import render_attention
            render_attention(service,service.overview(today_local().isoformat()),today_local().isoformat(),_go_record)
        elif view=='Calendário': render_calendar(service,_go_record,_go_review)
        elif view=='Registrar resultados':
            with st.container(key='study_registration'):
                with st.container(key='registration_header'):
                    st.title('Registrar resultado')
                    explain('Registre o que fez. O próximo plano acompanha seus resultados.')
                _register(service)
        elif view=='Temas e estatísticas':
            stats,errors,cut,goal=st.tabs(['Desempenho dos temas','Erros abertos','Plano de corte','Minha meta'],key='topics_tabs',on_change='rerun')
            with stats: render_topic_table(service,_go_record)
            with errors: render_errors(service)
            with cut: render_triage(service)
            with goal: render_goal_risk(service)
            with st.container(key='bento-topics-export'):
                st.download_button('Exportar CSV consolidado',consolidated_csv(service,today_local().isoformat()),'historico-consolidado.csv','text/csv',key='consolidated_export')
                explain('Fontes e versões em linhas separadas. Não some os denominadores entre PDFs, acumulados, blocos e simulados.')
        elif view=='Evolução': render_evolution(service)
        elif view=='Simulados': render_mock_exams(service)
        elif view=='Agrupamentos':
            from .grouping_ui import render_grouping
            render_grouping(service)
        else:
            with st.container(key='bento-settings-navigation'):
                settings=st.radio('O que ajustar?',['Meta e rotina','Minhas provas','Instituições e incidências'],horizontal=True,key='study_settings_section')
            if settings=='Meta e rotina':
                with st.container(key='bento-settings-routine'):
                    _settings(service)
                with st.expander('Avançado · revisões, simulados e calibração'):
                    with st.container(key='study_settings'):
                        render_review_strategy(service)
                        render_mock_settings(service)
                        render_parameter_settings(service)
            elif settings=='Minhas provas':
                with st.container(key='bento-settings-exams'):
                    render_exam_goals(service)
                    render_exam_weights(service)
            else:
                with st.container(key='bento-settings-incidence'):
                    render_guide_settings(repo,incidence_only=True)
    except (ValueError,sqlite3.Error,OSError) as exc:
        st.error(str(exc))


def _register(service):
    from .study_registration_ui import render_registration
    with st.container(key='bento-record'):
        render_registration(service,_go_record,_go_review,_back_to_plan,_edit)


def _edit(event):
    from .models import stable_topic_id
    reset_picker('record')
    st.session_state['adaptive_view']='Registrar resultados'
    st.session_state.pop('study_saved',None)
    e=event['entry']
    st.session_state['study_edit']=event
    st.session_state.pop('record_search',None)
    st.session_state['study_review_of']=e.get('review_of')
    st.session_state['study_confident']=e.get('confident_correct')
    st.session_state['study_cards_created']=e.get('cards_created',0)
    st.session_state['study_method']='percentual' if e['percent'] is not None else 'acertos'
    st.session_state['adaptive_topic']=stable_topic_id(e['path'])
    for key,value in {'study_n':e['questions'] or 1,'study_correct':e['correct'],'study_percent':e['percent'],'study_kind':e['kind'],
                      'study_mode':e['mode'],'study_duration':e['minutes'],'study_date':date.fromisoformat(e['day']),'study_last_contact':e.get('last_contact') or ''}.items():
        st.session_state[key]=value


def _set_display_name():
    st.session_state['interface_name']=' '.join(st.session_state['settings_display_name'].split())
    st.session_state['settings_display_name']=st.session_state['interface_name']


def _settings(service):
    st.subheader('Meta e rotina')
    with st.expander('Nome e ajustes salvos (opcional)'):
        st.text_input('Como quer ser chamado? (opcional)',value=st.session_state.get('interface_name',''),max_chars=40,
                      key='settings_display_name',on_change=_set_display_name)
        explain('Nome usado somente nesta sessão do aplicativo. Não altera os dados do seu plano.')
        if st.button('Recarregar ajustes salvos'):
            st.session_state.pop('adaptive_profile_snapshot',None)
            st.rerun()
    record=st.session_state.setdefault('adaptive_profile_snapshot',service.store.profile())
    p=AdaptiveProfile(**record['configured_profile'])
    with st.form('adaptive_profile'):
        left,right=st.columns(2)
        count=left.number_input('Meta padrão de questões por dia',min_value=1,max_value=1000,value=p.max_questions)
        share_percent=right.slider('Questões em temas novos (%)',0,100,round(p.new_share*100),step=5,key='settings_new_share')
        explain('A meta é por questões. Para mudar só um dia, use Hoje → Ajustar meu dia.')
        share=share_percent/100
        workload_mode=st.radio('Como distribuir a rotina?',['adaptive','fixed'],index=0 if p.workload_mode=='adaptive' else 1,
                               format_func={'adaptive':'Adaptativa — abre espaço para revisões','fixed':'Fixa — mantém a proporção escolhida'}.get,key='settings_workload_mode')
        st.divider()
        st.subheader('Objetivos e datas')
        left,right=st.columns(2)
        start=left.date_input('Início do cronograma',value=date.fromisoformat(p.start_date) if p.start_date else None,key='settings_start_date',format='DD/MM/YYYY')
        target=right.number_input('Meta de acerto nos temas (%)',min_value=1.,max_value=100.,value=float(p.target_accuracy))
        explain('Antes do início, sem metas nem faltas. O histórico anterior continua valendo para as revisões.')
        explain('Objetivo de aprendizagem: acerto em questões novas e amostra suficiente; convicção é informação complementar. Não é nota de prova nem probabilidade de aprovação.' if p.review_strategy=='balanced_v2' else 'Objetivo de aprendizagem: acerto com convicção em questões novas e amostra suficiente. Não é nota de prova nem probabilidade de aprovação.')
        if ExamGoals(service.repository).active():
            exam=date.fromisoformat(p.exam_date)
            st.caption('Data efetiva do plano: '+record['profile']['exam_date']+'. Gerencie em Minhas provas.')
        else: exam=st.date_input('Data de referência da prova',value=date.fromisoformat(p.exam_date),format='DD/MM/YYYY')
        with st.expander('Metas por grande área (opcional)'):
            catalog,_=service.catalog(today_local().isoformat())
            from .models import normalize_path
            areas={normalize_path([t['path'][0]])[0]:t['path'][0] for t in catalog}
            for name in p.area_targets: areas.setdefault(normalize_path([name])[0],name)
            values=[{'Área':name,'Usar meta própria':any(normalize_path([name])==normalize_path([k]) for k in p.area_targets),
                     'Meta (%)':float(p.target_for_area(name))} for name in sorted(areas.values())]
            import pandas as pd
            area_frame=st.data_editor(pd.DataFrame(values,columns=['Área','Usar meta própria','Meta (%)']),hide_index=True,width='stretch',disabled=['Área'],key='area_targets_'+str(record['id']),
                                      column_config={'Meta (%)':st.column_config.NumberColumn(min_value=1.,max_value=100.,step=1.)})
            st.caption('Ative só as áreas que quiser personalizar. As demais usam a meta global; não há configuração por subtema.')
        explain(f"{share_percent}% de questões em temas novos · {100-share_percent}% em revisões e diagnósticos. A proporção pode ser aproximada se faltarem temas elegíveis ou vagas por dia.")
        with st.expander('Instituições, distribuição e detalhes'):
            st.caption('A importância das provas é ajustada em Minhas provas, com incidência individual e prévia antes de aplicar. As instituições do conjunto ficam em Instituições e incidências.')
            max_topics=st.number_input('Máximo de temas por dia',min_value=1,max_value=10,value=p.max_topics)
            recent=st.number_input('Janela recente em dias',min_value=1,max_value=730,value=p.recent_days)
            minimum=st.number_input('Mínimo de questões por bloco automático',min_value=1,max_value=100,value=p.min_block)
            gap=st.number_input('Máximo de dias entre contatos',min_value=1,max_value=90,value=p.max_contact_gap)
        save=confirm_submit('Salvar planejamento',type='primary',action_key='adaptive_ui_204',details=f'Meta: {count} questões/dia · Novos: {share_percent}% · Prova: {exam:%d/%m/%Y}. O calendário será recalculado.')
    if save:
        notify_success(service.store.save_profile(replace(p,target_accuracy=target,exam_date=exam.isoformat(),start_date=start.isoformat() if start else None,max_questions=int(count),
                                           new_share=share,workload_mode=workload_mode,max_topics=int(max_topics),recent_days=int(recent),min_block=int(minimum),max_contact_gap=int(gap),
                                           area_targets={r['Área']:float(r['Meta (%)']) for _,r in area_frame.iterrows() if r['Usar meta própria']}),record['id']),'Alterações salvas.')
        st.session_state.pop('adaptive_profile_snapshot',None)
        st.session_state['adaptive_notice']='Planejamento atualizado. As próximas quantidades já seguem esses ajustes.'
        st.rerun()
