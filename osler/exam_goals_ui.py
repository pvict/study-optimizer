"""Minhas provas: referência documentada, versões preservadas e principal explícita."""
from dataclasses import replace
from datetime import date
import pandas as pd
import streamlit as st
from .exam_goals import ExamGoals,ExamTarget,principal_exam
from .planner_service import today_local
from .study_models import AdaptiveProfile


def _reset_exam(row=None):
    for key in list(st.session_state):
        if key.startswith('exam_field_'): st.session_state.pop(key,None)
    if row: st.session_state['exam_edit']=row
    else: st.session_state.pop('exam_edit',None)


def _void_exam(goals,row):
    try:
        goals.void(row['target_id'],row['version'])
        _reset_exam()
        st.session_state.pop('adaptive_profile_snapshot',None)
        st.session_state.pop('exam_primary_snapshot',None)
        st.session_state['adaptive_notice']='Prova desconsiderada. As versões anteriores foram preservadas.'
    except ValueError as exc: st.session_state['adaptive_error']=str(exc)


def _reload_exams():
    _reset_exam()
    st.session_state.pop('adaptive_profile_snapshot',None)
    st.session_state.pop('exam_primary_snapshot',None)


def render_exam_goals(service):
    goals=ExamGoals(service.repository)
    rows=goals.active()
    if st.session_state.pop('exam_reset_pending',False): _reset_exam()
    st.subheader('Minhas provas')
    st.caption('Cadastre datas e cortes com fonte. O percentual do corte é apenas referência; não prevê sua nota nem sua aprovação.')
    st.button('Recarregar provas',on_click=_reload_exams,key='reload_exams')
    current=service.store.profile()
    if rows:
        chosen=principal_exam(AdaptiveProfile(**current['profile']),rows,today_local().isoformat())
        st.info(f"Data usada no plano: {chosen['target']['exam_date']} · {chosen['target']['institution']}")
        st.dataframe(pd.DataFrame([{'Instituição':r['target']['institution'],'Edição':r['target']['exam_year'],
                                    'Data da prova':r['target']['exam_date'],'Inscrição até':r['target']['registration_deadline'],
                                    'Corte informado':r['target']['cutoff_score'],'Nota máxima':r['target']['max_score'],
                                    'Corte de referência (%)':100*r['target']['cutoff_score']/r['target']['max_score'],
                                    'Fonte':r['target']['cutoff_source'],'Conferência':r['target']['cutoff_confidence']} for r in rows]),
                     hide_index=True,width='stretch',column_config={'Corte de referência (%)':st.column_config.NumberColumn(format='%.1f%%')})
        by_id={r['target_id']:r for r in rows}
        record=st.session_state.setdefault('exam_primary_snapshot',current)
        configured=AdaptiveProfile(**record['configured_profile'])
        options=['automatic',*by_id]
        def label(key):
            if key=='automatic': return 'Automática · próxima prova cadastrada'
            target=by_id[key]['target']
            return target['institution']+' · '+target['exam_date']
        with st.form('exam_primary_form'):
            selected=st.selectbox('Prova principal',options,index=options.index(configured.primary_exam_id) if configured.primary_exam_id in by_id else 0,
                                  format_func=label,key='exam_primary')
            st.caption('A principal define a data do plano. No automático, usamos a futura mais próxima; se todas passaram, a mais recente.')
            save=st.form_submit_button('Usar esta prova principal',key='save_exam_primary')
        if save:
            service.store.save_profile(replace(configured,primary_exam_id=None if selected=='automatic' else selected),record['id'])
            st.session_state.pop('exam_primary_snapshot',None)
            st.session_state.pop('adaptive_profile_snapshot',None)
            st.session_state['adaptive_notice']='Prova principal atualizada. O calendário foi recalculado.'
            st.rerun()
        selected=st.selectbox('Prova para consultar ou editar',list(by_id),format_func=label,key='exam_selected')
        left,right=st.columns(2)
        left.button('Editar prova',key='edit_exam',on_click=_reset_exam,args=(by_id[selected],),width='stretch')
        right.button('Desconsiderar prova',key='void_exam',on_click=_void_exam,args=(goals,by_id[selected]),width='stretch')
    else:
        st.info('Nenhuma prova cadastrada. A data já configurada no plano continua valendo.')
    editing=st.session_state.get('exam_edit')
    data=editing['target'] if editing else {}
    st.button('Cadastrar outra prova' if editing else 'Limpar formulário',on_click=_reset_exam,key='new_exam')
    st.markdown('**Editar prova · nova versão**' if editing else '**Cadastrar prova**')
    with st.form('exam_target_form'):
        institution=st.text_input('Instituição',value=data.get('institution',''),key='exam_field_institution')
        day=st.date_input('Data da prova',value=date.fromisoformat(data.get('exam_date',current['profile']['exam_date'])),key='exam_field_date',format='DD/MM/YYYY')
        left,right=st.columns(2)
        cutoff=left.number_input('Nota de corte de referência',min_value=0.,value=float(data['cutoff_score']) if data else None,key='exam_field_cutoff')
        maximum=right.number_input('Nota máxima da prova',min_value=.01,value=float(data.get('max_score',100)),key='exam_field_max')
        source=st.text_input('Fonte do corte (obrigatória)',value=data.get('cutoff_source',''),placeholder='Edital, documento ou link da edição consultada',key='exam_field_source')
        with st.expander('Edição, inscrição e observações (opcionais)'):
            bases=['nao_informada','percentual_objetivo','pontuacao_ponderada']
            score_basis=st.selectbox('Como a nota do corte é calculada?',bases,index=bases.index(data.get('score_basis','nao_informada')),
                                     format_func={'nao_informada':'Ainda não confirmei a escala','percentual_objetivo':'Acertos objetivos, com questões de mesmo peso','pontuacao_ponderada':'Pontuação ponderada ou outras etapas'}.get,key='exam_field_score_basis')
            year=st.number_input('Ano da edição',min_value=1,max_value=9999,value=data.get('exam_year'),key='exam_field_year')
            deadline=st.date_input('Último dia de inscrição',value=date.fromisoformat(data['registration_deadline']) if data.get('registration_deadline') else None,key='exam_field_deadline',format='DD/MM/YYYY')
            choices=['informado','conferido','estimado']
            confidence=st.selectbox('Como este corte foi conferido?',choices,index=choices.index(data.get('cutoff_confidence','informado')),key='exam_field_confidence')
            notes=st.text_area('Observações',value=data.get('notes',''),key='exam_field_notes')
        save=st.form_submit_button('Salvar prova',type='primary',key='save_exam')
    if save:
        if day is None: raise ValueError('Informe a data da prova antes de salvar.')
        target=ExamTarget(institution,day.isoformat(),cutoff,maximum,source,year,deadline.isoformat() if deadline else None,confidence,notes,score_basis)
        goals.save(target,target_id=editing['target_id'] if editing else None,expected_version=editing['version'] if editing else 0)
        st.session_state['exam_reset_pending']=True
        st.session_state.pop('adaptive_profile_snapshot',None)
        st.session_state['adaptive_notice']='Prova salva. Datas atualizadas; nenhum estudo foi criado.'
        st.rerun()
    with st.expander('Histórico das provas'):
        history=goals.events()
        if history:
            st.dataframe(pd.DataFrame([{'Instituição':e['target']['institution'],'Versão':e['version'],'Ação':'Desconsiderada' if e['action']=='void' else 'Salva',
                                        'Data da prova':e['target']['exam_date'],'Corte':e['target']['cutoff_score'],'Fonte':e['target']['cutoff_source']} for e in history]),hide_index=True,width='stretch')
        else: st.caption('O histórico será criado ao salvar a primeira prova.')
