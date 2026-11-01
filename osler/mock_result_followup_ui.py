"""Coleta imediata dos erros após o resultado; mesma anotação usada na Correção."""
import streamlit as st
from .topic_picker_ui import pick_topic
from .planner_service import today_local
from .action_feedback import notify_success


def request_error_topics(saved):
    if saved['exam']['questions']>saved['exam']['correct']:
        st.session_state['mock_error_prompt']={'exam_key':saved['exam_key'],'version':saved['version']}


def _later():
    st.session_state.pop('mock_error_prompt',None)


@st.dialog('Quais temas você errou?',width='large',on_dismiss=_later)
def render_error_prompt(service):
    pending=st.session_state.get('mock_error_prompt')
    if not pending:return
    try:context=service.mock_errors(pending['exam_key'])
    except ValueError:
        _later();st.rerun()
    record=context['exam'];exam=record['exam']
    pending.setdefault('annotation_id',context['annotation_id'])
    st.write('**'+exam['name']+'**')
    st.caption(f"Resultado salvo · {exam['questions']-exam['correct']} erros ou brancos")
    if record['version']!=pending['version'] or pending['annotation_id']!=context['annotation_id']:
        st.warning('O resultado mudou. Abra a aba Correção para conferir os erros atuais.')
        if st.button('Fechar',key='mock_error_changed'):_later();st.rerun()
        return
    draft_key='mock_error_draft_'+record['exam_key']+'_'+str(record['version'])
    draft=st.session_state.setdefault(draft_key,[dict(r) for r in context['errors']])
    catalog,_=service.catalog(today_local().isoformat())
    if exam.get('practice_id'):
        from .models import normalize_path
        area=normalize_path([exam['areas'][0]['area']])[0]
        catalog=[t for t in catalog if normalize_path([t['path'][0]])[0]==area]
    if catalog:
        topic=pick_topic(catalog,'mock_error_picker_'+record['exam_key'])
        count=st.number_input('Erros neste tema · opcional',min_value=1,max_value=max(1,exam['questions']-exam['correct']),
                              value=None,key='mock_error_count_'+record['exam_key'])
        if st.button('Adicionar tema',key='mock_error_add'):
            if topic and not any(r['path']==topic['path'] for r in draft):
                draft.append({'path':topic['path'],'errors':count});st.rerun()
            elif topic:st.info('Esse tema já está na lista.')
    else:st.info('Importe o catálogo de temas para associar os erros. Você pode completar depois na aba Correção.')
    if draft:
        st.markdown('**Temas para o reforço**')
        for i,row in enumerate(draft):
            label,action=st.columns([5,1],gap='small')
            label.write(' › '.join(row['path'])+(f" · {row['errors']} erros" if row.get('errors') is not None else ''))
            if action.button('Retirar',key='mock_error_remove_'+str(i)):
                draft.pop(i);st.rerun()
    if st.button('Salvar temas para reforço',key='mock_error_save',type='primary',disabled=not draft):
        try:
            service.save_mock_errors(record['exam_key'],record['version'],draft,context['annotation_id'],service.agenda.token())
        except ValueError as exc:st.error(str(exc))
        else:
            notify_success(True,'Temas errados salvos.')
            _later();st.session_state.pop(draft_key,None)
            st.session_state['mock_tab_pending']='Correção'
            st.session_state['practice_notice']='Temas salvos. Confira a prévia da distribuição para reservar o reforço.'
            st.rerun()
    if st.button('Informar depois',key='mock_error_later'):
        _later();st.rerun()
