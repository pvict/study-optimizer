"""Menu único; rotas continuam nas chaves públicas de estado já existentes."""
import streamlit as st

STUDY=[('Hoje','today','Meu dia','light_mode'),('Calendário','calendar','Calendário','calendar_month'),
       ('Evolução','evolution','Evolução','trending_up'),('Temas','topics','Temas e estatísticas','menu_book'),
       ('Simulados','mocks','Simulados','assignment')]


def go_view(main,adaptive=None):
    if main not in {'Plano de questões','Diminuir revisões','Ferramentas'}: raise ValueError('Tela desconhecida.')
    st.session_state['main_view']=main
    if adaptive is not None: st.session_state['adaptive_view']=adaptive


def register_view():
    if st.session_state.get('study_saved'):
        from .adaptive_ui import _go_record
        _go_record(st.session_state.get('adaptive_topic'),20)
    go_view('Plano de questões','Registrar resultados')


def render_navigation():
    if st.session_state.get('main_view') not in {'Plano de questões','Diminuir revisões','Ferramentas'}:
        st.session_state['main_view']='Plano de questões'
    st.session_state.setdefault('adaptive_view','Meu dia')
    with st.sidebar:
        with st.container(key='bento_sidebar'):
            st.markdown('<div class="o-brand"><svg width="38" height="38" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="19" fill="#4F46E5"/><path d="M20 11v18M11 20h18" stroke="white" stroke-width="3" stroke-linecap="round"/></svg><span><strong>Osler</strong><small>Preparação para a residência</small></span></div>',unsafe_allow_html=True)
            st.button('Registrar bloco',key='nav_register',type='primary',icon=':material/edit_note:',on_click=register_view,width='stretch')
            st.caption('ESTUDO')
            for label,key,view,icon in STUDY:
                active=st.session_state['main_view']=='Plano de questões' and st.session_state['adaptive_view']==view
                with st.container(key='nav_active_'+key if active else 'nav_idle_'+key):
                    st.button(label,key='nav_'+key,icon=f':material/{icon}:',on_click=go_view,args=('Plano de questões',view),width='stretch')
            st.caption('FERRAMENTAS')
            for label,key,main,icon in [('Flashcards','flashcards','Diminuir revisões','style'),('Arquivos e ferramentas','files','Ferramentas','folder_open')]:
                with st.container(key='nav_active_'+key if st.session_state['main_view']==main else 'nav_idle_'+key):
                    st.button(label,key='nav_'+key,icon=f':material/{icon}:',on_click=go_view,args=(main,),width='stretch')
            st.divider()
            with st.container(key='nav_active_settings' if st.session_state['adaptive_view']=='Ajustes' and st.session_state['main_view']=='Plano de questões' else 'nav_idle_settings'):
                st.button('Ajustes',key='nav_settings',icon=':material/settings:',on_click=go_view,args=('Plano de questões','Ajustes'),width='stretch')
            with st.expander('Sobre o app'):
                st.caption('Tudo fica no seu computador. As ações na Osler continuam sendo feitas por você.')
    return st.session_state['main_view']
