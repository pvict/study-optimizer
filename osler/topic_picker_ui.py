"""Busca digitada e caminho progressivo, com escolhas explícitas do geral ao específico."""
import streamlit as st
from .models import normalize_path
from .topic_catalog import is_practice_topic


def reset_picker(key):
    for name in list(st.session_state):
        if name.startswith(key+'_'): st.session_state.pop(name,None)


def pick_topic(topics,key,selected_id=None):
    topics=[t for t in topics if is_practice_topic(t)]
    if not topics: return None
    if st.session_state.get(key+'_requested')!=selected_id:
        reset_picker(key)
        st.session_state[key+'_requested']=selected_id
    search=st.text_input('Digite o tema ou navegue pelas áreas',placeholder='Ex.: feridas, diabetes, oncologia',key=key+'_search')
    by_id={t['topic_id']:t for t in topics}
    if search.strip():
        query=normalize_path([search])[0]
        matches=[t for t in topics if query in normalize_path([' → '.join(t['path'])])[0]]
        if not matches:
            st.info('Nenhum tema encontrado. Tente uma palavra mais geral.')
            return None
        matches=sorted(matches,key=lambda t:(len(t['path']),' → '.join(t['path'])))
        st.caption(f'{len(matches)} temas específicos. '+('Mostrando os primeiros 20; refine a busca.' if len(matches)>20 else 'Escolha o tema que vai estudar.'))
        matches=matches[:20]
        chosen=st.radio('Resultados da busca',[t['topic_id'] for t in matches],format_func=lambda k:' › '.join(by_id[k]['path']),key=key+'_search_result')
        st.markdown('**'+ ' › '.join(by_id[chosen]['path'])+'**')
        return by_id[chosen]
    preferred=by_id.get(selected_id)
    areas=sorted({t['path'][0] for t in topics})
    area=st.selectbox('1 · Área',areas,index=areas.index(preferred['path'][0]) if preferred else 0,key=key+'_area')
    prefix=[area]
    depth=1
    while True:
        candidates=[t for t in topics if t['path'][:len(prefix)]==prefix]
        exact=next((t for t in candidates if t['path']==prefix),None)
        children=sorted({t['path'][len(prefix)] for t in candidates if len(t['path'])>len(prefix)})
        if not children:
            result=exact
            break
        options=(['Este assunto inteiro'] if exact else [])+children
        expected=preferred['path'][depth] if preferred and preferred['path'][:depth]==prefix and len(preferred['path'])>depth else None
        widget=key+'_level_'+str(depth)+'_'+'_'.join(normalize_path(prefix))
        value=st.selectbox(f'{depth+1} · '+('Assunto' if depth==1 else 'Subtema'),options,index=options.index(expected) if expected in options else 0,key=widget)
        if value=='Este assunto inteiro':
            result=exact
            break
        prefix.append(value)
        depth+=1
    if result: st.markdown('**'+ ' › '.join(result['path'])+'**')
    return result
