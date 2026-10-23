"""Registro opcional após o bloco e consulta de conceitos ainda em revisão."""
import pandas as pd
import streamlit as st

from .models import normalize_path
from .planner_service import today_local
from .study_errors import CAUSES, ErrorStore, StudyError


def _next_quick_error(session_id):
    key = 'quick_error_counter_' + session_id
    st.session_state[key] = st.session_state.get(key, 0) + 1


def render_quick_error(service, session_id):
    """Não acrescenta nenhum campo obrigatório ao registro do bloco."""
    session = next((s for s in service.store.active(today_local().isoformat()) if s['session_id'] == session_id), None)
    if not session:
        return
    counter = st.session_state.get('quick_error_counter_' + session_id, 0)
    key = f'quick_error_{session_id}_{counter}'
    with st.expander('Anotar um erro deste bloco (opcional)', expanded=False):
        if st.session_state.get(key + '_saved'):
            st.success('Erro anotado. Você pode marcar como resolvido em Erros.')
            st.button('Anotar outro erro deste bloco', key=key + '_another', on_click=_next_quick_error, args=(session_id,))
            return
        entry = session['entry']
        st.caption('Tema: ' + ' › '.join(entry['path']))
        with st.form(key + '_form'):
            cause = st.selectbox('Por que errei?', list(CAUSES), format_func=CAUSES.get, key=key + '_cause')
            note = st.text_input('Conceito que faltou, nas suas palavras', max_chars=280, key=key + '_note',
                                 placeholder='Uma frase curta, sem copiar o enunciado')
            critical = st.checkbox('É um erro crítico para mim', key=key + '_critical',
                                   help='Enquanto estiver aberto, pede atenção no plano e impede sugestão de reduzir cartões deste tema.')
            save = st.form_submit_button('Salvar erro', key=key + '_save')
        if save:
            try:
                ErrorStore(service.repository, catalog=service.catalog).save(
                    StudyError(entry['path'], entry['day'], cause, note, session_id, critical))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state[key + '_saved'] = True
                st.rerun()


def _close_error(store, key, version, action):
    try:
        getattr(store, action)(key, version)
        st.session_state['study_error_notice'] = 'Erro marcado como resolvido.' if action == 'resolve' else 'Erro desconsiderado. O histórico foi preservado.'
    except ValueError as exc:
        st.session_state['study_error_failure'] = str(exc)


def render_errors(service):
    store = ErrorStore(service.repository)
    st.subheader('Erros')
    st.caption('Guarde apenas o conceito que faltou, nas suas palavras. Enunciados da plataforma não devem ser copiados.')
    if message := st.session_state.pop('study_error_notice', None):
        st.success(message)
    if message := st.session_state.pop('study_error_failure', None):
        st.error(message)
    opened = store.active(today_local().isoformat())
    st.caption(f"{len(opened)} " + ('erro aberto.' if len(opened) == 1 else 'erros abertos.'))
    if opened:
        catalog, _ = service.catalog(today_local().isoformat())
        names = {tuple(normalize_path(t['path'])): t['path'] for t in catalog}
        paths = sorted({tuple(e['path']) for e in opened})
        selected = st.selectbox('Filtrar por tema', [None, *paths],
                                format_func=lambda p: 'Todos os temas' if p is None else ' › '.join(names.get(p, p)), key='study_errors_topic')
        with st.expander('Mais filtros'):
            cause = st.selectbox('Motivo do erro', [None, *CAUSES], format_func=lambda c: 'Todos os motivos' if c is None else CAUSES[c], key='study_errors_cause')
        filtered = [e for e in opened if (selected is None or tuple(e['path']) == selected) and (cause is None or e['cause'] == cause)]
        if not filtered:
            st.info('Nenhum erro aberto com estes filtros.')
        for error in filtered:
            with st.container(border=True):
                st.write(' › '.join(names.get(tuple(error['path']), error['path'])))
                st.caption(error['day'] + ' · ' + CAUSES[error['cause']] + (' · Crítico' if error['critical'] else ''))
                if error['note']:
                    st.text(error['note'])
                if error['flashcard_hint']:
                    st.text('Ideia para cartão: ' + error['flashcard_hint'])
                left, right = st.columns(2)
                left.button('Marcar como resolvido', key='resolve_error_' + error['error_key'],
                            on_click=_close_error, args=(store, error['error_key'], error['version'], 'resolve'), width='stretch')
                right.button('Desconsiderar erro', key='void_error_' + error['error_key'],
                             on_click=_close_error, args=(store, error['error_key'], error['version'], 'void'), width='stretch')
    else:
        st.info('Nenhum erro aberto. Depois de salvar um bloco, use “Anotar um erro deste bloco” se precisar.')
    events = store.events()
    if events:
        st.download_button('Exportar erros e histórico (CSV)', store.export_csv(), file_name='erros-estudo.csv', mime='text/csv', key='study_errors_csv')
        with st.expander('Histórico dos erros'):
            actions = {'save': 'Salvo', 'resolve': 'Resolvido', 'void': 'Desconsiderado'}
            st.dataframe(pd.DataFrame([{'Tema': ' › '.join(e['path']), 'Data do erro': e['day'],
                                        'Motivo': CAUSES[e['cause']], 'Conceito': e['note'], 'Versão': e['version'],
                                        'Ação': actions[e['action']]} for e in events]), hide_index=True, width='stretch')


def render_error_context(service, path, as_of):
    store = ErrorStore(service.repository)
    normalized = tuple(normalize_path(path))
    rows = [e for e in store.active(as_of) if tuple(e['path']) == normalized]
    if not rows:
        return
    st.caption(f"{len(rows)} " + ('erro aberto' if len(rows) == 1 else 'erros abertos') + ' neste tema · consulte Temas → Erros abertos para resolver.')
    with st.expander('Conceitos para retomar'):
        for error in rows:
            st.caption(CAUSES[error['cause']] + (' · Crítico' if error['critical'] else ''))
            if error['note']:
                st.text(error['note'])
