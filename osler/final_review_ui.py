"""Datas e revisão final com comparação antes de alterar o calendário."""
from datetime import date,timedelta
import pandas as pd
import streamlit as st
from .exam_goals import active_exams
from .planner_service import today_local
from .study_models import AdaptiveProfile
from dataclasses import replace


def open_final_review():
    st.session_state['adaptive_view']='Calendário'
    st.session_state['final_review_open']=True


def render_approach(service):
    threshold=service.store.profile()['profile']['approach_days']
    exams=[e for e in service.exam_dates() if e['kind']=='exam_date' and 0<=e['days_left']<=threshold]
    if threshold and exams:
        e=exams[0]
        st.info(f"Fase de aproximação · {e['institution']} em {e['days_left']} dias. Confira seu ritmo e os erros que ainda estão abertos.")
        st.button('Planejar revisão final',key='approach_final_review',on_click=open_final_review)


def render_exam_dates(service,start,end):
    rows=[e for e in service.exam_dates() if start<=e['date']<=end]
    if rows:
        st.markdown('**Provas e inscrições neste período**')
        st.dataframe(pd.DataFrame([{'Data':r['date'],'Compromisso':r['label'],'Instituição':r['institution'],
                                    'Dias restantes':r['days_left']} for r in rows]),hide_index=True,width='stretch')


def render_final_review(service):
    with st.expander('Revisão final para uma prova',expanded=st.session_state.get('final_review_open',False)):
        current=service.agenda.active(service.store.active(today_local().isoformat()),today_local().isoformat())
        for row in current['active']:
            if row.get('scope')!='final_review': continue
            st.caption('Revisão aplicada: '+row['start']+' até '+row['rest_day'])
            if st.button('Desfazer esta revisão final',key='final_undo_'+str(row['id'])):
                service.cancel_replan(row['id'],service.agenda.token())
                st.session_state['adaptive_notice']='Revisão final desfeita. Agenda anterior restaurada; resultados preservados.'
                st.rerun()
        exams=[e for e in active_exams(service.repository) if e['target']['exam_date']>today_local().isoformat()]
        if not exams:
            st.caption('Cadastre uma prova futura em Ajustes → Minhas provas para planejar a reta final.')
            return
        lookup={e['target_id']:e for e in exams}
        selected=st.selectbox('Qual prova?',list(lookup),format_func=lambda key:lookup[key]['target']['institution']+' · '+lookup[key]['target']['exam_date'],key='final_exam')
        exam_day=date.fromisoformat(lookup[selected]['target']['exam_date'])
        start=st.date_input('Começar a revisão em',value=max(today_local(),exam_day-timedelta(days=14)),key='final_start',format='DD/MM/YYYY')
        questions=st.number_input('Questões por dia na revisão final',1,1000,service.store.profile()['profile']['max_questions'],key='final_questions')
        st.caption('Sugestão de 7 a 14 dias. Primeiro os erros abertos; depois incidência e desempenho. A véspera fica reservada para descanso.')
        if st.button('Ver prévia da revisão final',key='final_preview'):
            try: st.session_state['final_preview_data']=service.preview_final_review(selected,start.isoformat(),int(questions))
            except ValueError as exc: st.error(str(exc))
        preview=st.session_state.get('final_preview_data')
        if preview and (preview['target_id'],preview['start'],preview['questions'])==(selected,start.isoformat(),questions):
            st.caption('Véspera de descanso: '+preview['rest_day']+'. O padrão diário e seus resultados serão preservados. As sugestões deste período não se acumulam como dívida.')
            if preview['rows']:
                st.dataframe(pd.DataFrame([{'Data':r['date'],'Tema específico':r['path'][-1],'Questões':r['questions'],'Motivo':r['basis']} for r in preview['rows']]),hide_index=True,width='stretch')
            else: st.info('Nenhum tema disponível na janela. Confira os dias de descanso e o catálogo.')
            st.caption(f"{len(preview['replaced_days'])} dias terão programação temporária. A carga não é preenchida artificialmente quando faltam temas elegíveis; cada tema aparece uma vez nesta proposta.")
            if st.button('Aplicar revisão final',key='final_apply',disabled=not preview['rows'],type='primary'):
                try:
                    service.apply_final_review(preview)
                    st.session_state.pop('final_preview_data',None)
                    st.session_state['adaptive_notice']='Revisão final aplicada. Você pode desfazer abaixo.'
                    st.rerun()
                except ValueError as exc: st.error(str(exc))


def render_mock_days(service):
    current=service.agenda.active(service.store.active(today_local().isoformat()),today_local().isoformat())
    active=[r for r in current['active'] if r.get('scope')=='mock_day']
    if not active: return
    with st.expander('Dias feitos por simulado'):
        for row in active:
            for day,override in row['overrides'].items():
                st.caption(f"{day} · {override['mock_questions']} questões do simulado, separadas dos blocos.")
            if st.button('Restaurar meta normal deste dia',key='calendar_undo_mock_'+str(row['id'])):
                service.cancel_replan(row['id'],service.agenda.token())
                st.session_state['adaptive_notice']='Meta diária restaurada. Simulado e resultados preservados.'
                st.rerun()


def render_exam_weights(service):
    from .exam_weights_ui import render_exam_weights as render
    render(service)
