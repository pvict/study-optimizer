"""A redução da fila no centro do app, sem formulário por subtema."""
import streamlit as st

def _open_tool(view, sources, batch_id=None, item_id=None, row_id=None):
    st.session_state['main_view'] = 'Ferramentas'
    st.session_state['advanced_view'] = view
    if sources['qbank'] and sources['flashcards']:
        st.session_state['planner_q_id'] = sources['qbank']
        st.session_state['planner_f_id'] = sources['flashcards']
    if batch_id is not None:
        st.session_state['planner_batch_id'] = batch_id
        if item_id is not None:
            st.session_state[f'planner_item_{batch_id}'] = item_id
    if row_id is not None:
        st.session_state['planner_search'] = ''
        st.session_state['planner_area'] = 'Todas'
        st.session_state['planner_categories'] = ['A', 'B']
        st.session_state['planner_initial_range'] = (0, 100)
        st.session_state['planner_selection'] = [row_id]


def render_reduction(repo):
    from .practical_reduction_ui import render_practical
    render_practical(repo, _open_tool)
