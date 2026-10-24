"""Lote vinculado e prática do tema pertencem ao mesmo orçamento, com fontes separadas."""
import streamlit as st
from .balanced_reviews import review_parts


def render_review_parts(item,day,go_record,go_review,prefix):
    parts=review_parts(item,day)
    st.caption(f"{item['questions']} questões no total: {parts['lot_questions']} em retornos conhecidos"+
        (f" + {parts['complement']} para conferir o tema." if parts['complement'] else '. O lote não substitui a medição geral do tema.'))
    for lot in parts['lots']:
        st.button(f"Registrar lote de {lot['questions']} respostas",key=prefix+'_lot_'+lot['session_id'],
            on_click=go_review,args=(lot,),width='stretch')
    if parts['complement']:
        st.button(f"Registrar complemento de {parts['complement']} questões",key=prefix+'_complement_'+item['topic_id'],
            on_click=go_record,args=(item['topic_id'],parts['complement'],'mistas'),width='stretch')
