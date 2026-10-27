"""Lote vinculado e prática do tema pertencem ao mesmo orçamento, com fontes separadas."""
import streamlit as st
from .balanced_reviews import review_parts


def render_review_parts(item,day,go_record,go_review,prefix,primary=False):
    parts=review_parts(item,day)
    st.caption(f"{item['questions']} questões no total: {parts['lot_questions']} em retornos conhecidos"+
        (f" + {parts['complement']} para conferir o tema." if parts['complement'] else '. Retorno dirigido; não comprova domínio geral do tema.'))
    for index,lot in enumerate(parts['lots']):
        st.button(f"Registrar lote de {lot['questions']} respostas",key=prefix+'_lot_'+lot['session_id'],
            on_click=go_review,args=(lot,),width='stretch',type='primary' if primary and index==0 else 'secondary')
    if parts['complement']:
        st.button(f"Registrar complemento de {parts['complement']} questões",key=prefix+'_complement_'+item['topic_id'],
            on_click=go_record,args=(item['topic_id'],parts['complement'],'mistas'),width='stretch',type='primary' if primary and not parts['lots'] else 'secondary')
