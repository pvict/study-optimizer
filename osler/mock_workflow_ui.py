"""Resultado e temas errados no mesmo fluxo, sem depender da programação."""
from datetime import date
import streamlit as st
from .mock_exams import MockExam,MockExams
from .planner_service import today_local
from .action_feedback import notify_success
from .topic_picker_ui import pick_topic
from .study_navigation_ui import go_view


def _open_correction(key):
    st.session_state['mock_selection_pending']=key
    st.session_state['mock_tab_pending']='Correção'
    go_view('Plano de questões','Simulados')


def _error_topics(service,row,prefix):
    context=service.mock_errors(row['exam_key']); exam=row['exam']
    st.subheader('2 · Temas errados')
    missed=exam['questions']-exam['correct']
    if not missed:
        st.success('Todos os acertos registrados. Não há erros para corrigir.')
        return
    st.caption(f'{missed} erros ou brancos. A quantidade por tema é opcional. Você pode completar depois.')
    draft_key=f"mock_flow_errors_{row['exam_key']}_{row['version']}_{context['annotation_id']}"
    draft=st.session_state.setdefault(draft_key,[dict(e) for e in context['errors']])
    if context['stale']:st.warning('O resultado foi editado. Confira os temas e salve novamente.')
    catalog,_=service.catalog(today_local().isoformat())
    if exam.get('practice_id'):
        from .models import normalize_path
        area=normalize_path([exam['areas'][0]['area']])[0]
        catalog=[t for t in catalog if normalize_path([t['path'][0]])[0]==area]
    if catalog:
        topic=pick_topic(catalog,prefix+'_topic_'+row['exam_key'])
        count=st.number_input('Erros nesse tema (opcional)',min_value=1,max_value=missed,value=None,key=prefix+'_count_'+row['exam_key'])
        if st.button('Adicionar tema errado',key=prefix+'_add',disabled=topic is None):
            if any(e['path']==topic['path'] for e in draft):st.info('Esse tema já está na lista.')
            else:
                draft.append({'path':topic['path'],'errors':count});st.rerun()
    else:st.info('Para selecionar temas, importe seu relatório em Atualizar dados. O resultado já está salvo e continuará disponível aqui.')
    for i,item in enumerate(draft):
        label,action=st.columns([5,1])
        label.write(' › '.join(item['path'])+(f" · {item['errors']} erros" if item.get('errors') is not None else ''))
        if action.button('Retirar',key=prefix+'_remove_'+str(i)):
            draft.pop(i);st.rerun()
    if st.button('Salvar temas errados',key=prefix+'_save_errors',type='primary',disabled=not draft):
        try:
            notify_success(service.save_mock_errors(row['exam_key'],row['version'],draft,context['annotation_id'],service.agenda.token()),'Temas errados salvos.')
            st.session_state[prefix+'_saved_errors']=row['exam_key'];st.rerun()
        except ValueError as exc:st.error(str(exc))
    if context['errors'] and not context['stale']:
        st.success(f"{len(context['errors'])} tema(s) salvo(s) para este simulado.")
        st.button('3 · Planejar revisão dos temas errados',key=prefix+'_distribute',on_click=_open_correction,args=(row['exam_key'],))
    st.caption('O resultado fica salvo mesmo que você deixe os temas para depois.')


def render_mock_workflow(service,prefix='mock_flow'):
    mocks=MockExams(service.repository); rows=mocks.active(); today=today_local()
    by_key={r['exam_key']:r for r in reversed(rows)}
    selection_key=prefix+'_selected'
    pending=st.session_state.pop(prefix+'_pending',None)
    if pending in by_key:st.session_state[selection_key]=pending
    if st.session_state.get(selection_key) not in {'',*by_key}:st.session_state.pop(selection_key,None)
    if st.button('Registrar outro simulado' if rows else 'Começar novo registro',key=prefix+'_new'):
        st.session_state[selection_key]=''
        for key in list(st.session_state):
            if key.startswith(prefix+'_form_'):st.session_state.pop(key,None)
    default=next((k for k,r in by_key.items() if r['exam']['day']==today.isoformat()),'')
    choices=['',*by_key]
    selected=st.selectbox('Registrar ou retomar um simulado',choices,index=choices.index(default),
        format_func=lambda k:'Novo simulado feito' if not k else date.fromisoformat(by_key[k]['exam']['day']).strftime('%d/%m/%Y')+' · '+by_key[k]['exam']['name'],key=selection_key)
    if selected:
        row=by_key[selected];exam=row['exam']
        st.success(f"Resultado salvo: {exam['name']} · {exam['correct']} de {exam['questions']} acertos")
        _error_topics(service,row,prefix)
        return
    st.subheader('1 · Registrar simulado')
    st.caption('Também aceita simulados sem agendamento.')
    used={r['exam'].get('practice_id') for r in rows}
    tasks={r['id']:r for r in (service.area_schedule() or {}).get('occurrences',[])
           if r.get('date') and r['date']<=today.isoformat() and r.get('status')!='blocked' and r['id'] not in used}
    task_id=st.selectbox('O que você fez?', ['completo',*tasks],
        format_func=lambda k:'Simulado completo' if k=='completo' else tasks[k]['institution']+' · '+tasks[k]['area']+' · treino de '+date.fromisoformat(tasks[k]['date']).strftime('%d/%m'),key=prefix+'_source')
    task=tasks.get(task_id)
    schedule=service.mock_schedule() or {}
    planned=next((r for r in schedule.get('occurrences',[]) if r.get('date')==today.isoformat() and r.get('status')=='reserved'),{})
    token=service.agenda.token()
    with st.form(prefix+'_form',clear_on_submit=False):
        name=st.text_input('Qual simulado ou prova você fez?',value=task['institution']+' · '+task['area'] if task else planned.get('name',''),max_chars=160,disabled=bool(task),key=prefix+'_form_name_'+task_id)
        day=st.date_input('Dia em que fez',value=today,max_value=today,format='DD/MM/YYYY',key=prefix+'_form_day')
        total=st.number_input('Total de questões',min_value=1,max_value=1000000,value=task['questions'] if task else None,step=1,key=prefix+'_form_total_'+task_id)
        correct=st.number_input('Quantas acertou?',min_value=0,max_value=1000000,value=None,step=1,key=prefix+'_form_correct_'+task_id)
        kind=st.selectbox('Tipo de simulado',['prova_anterior','simulado_cursinho','outro'],format_func=lambda k:{'prova_anterior':'Prova anterior','simulado_cursinho':'Simulado de cursinho','outro':'Outro'}[k],key=prefix+'_form_kind',disabled=bool(task))
        institution=st.text_input('Instituição ou banca (opcional)',value=task['institution'] if task else '',disabled=bool(task),key=prefix+'_form_institution_'+task_id)
        submitted=st.form_submit_button('Salvar resultado e informar temas errados',type='primary')
    if submitted:
        try:
            if total is None or correct is None:raise ValueError('Preencha o total de questões e quantas acertou.')
            if task:
                saved=service.register_area_result(task_id,day.isoformat(),int(total),int(correct),token=token)
            else:
                exam=MockExam(day.isoformat(),int(total),int(correct),name=name.strip(),kind=kind,institution=institution.strip() or None)
                saved=mocks.save(exam,expected_token=token)
            notify_success(saved,'Resultado salvo. Agora informe os temas errados.')
            st.session_state[prefix+'_pending']=saved['exam_key']
            st.session_state['mock_selection_pending']=saved['exam_key']
            st.rerun()
        except ValueError as exc:st.error(str(exc))
