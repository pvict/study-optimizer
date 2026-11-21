from streamlit.testing.v1 import AppTest


def test_explanations_are_optional_and_survive_navigation_without_changing_plan():
    app=AppTest.from_string('''
import streamlit as st
from osler.study_navigation_ui import render_navigation
from osler.ui_help import explain
render_navigation()
st.metric('Questões',120)
st.warning('Confirme a data antes de salvar.')
explain('Explicação técnica opcional.')
''').run()
    assert not app.exception
    assert not app.caption or not any(c.value=='Explicação técnica opcional.' for c in app.caption)
    assert app.metric[0].value=='120' and app.warning[0].value=='Confirme a data antes de salvar.'
    app.toggle(key='show_explanations').set_value(True).run()
    assert any(c.value=='Explicação técnica opcional.' for c in app.caption)
    app.button(key='nav_topics').click().run()
    assert app.toggle(key='show_explanations').value
    assert app.metric[0].value=='120'
    app.toggle(key='show_explanations').set_value(False).run()
    assert not any(c.value=='Explicação técnica opcional.' for c in app.caption)


def test_feedback_details_are_collapsed_without_hiding_metrics_or_next_contact(monkeypatch):
    import osler.study_activity_ui as ui
    feedback={'entry':{'day':'2026-10-29','mode':'mistas','kind':'bloco','questions':27,
                       'correct':19,'confident_correct':11},
              'accuracy_pct':100*19/27,'conviction_pct':100*11/27,'approximate':False,
              'level':'info','message':'Interpretação detalhada do desempenho.',
              'mistakes':8,'guesses':8,'small_block':False,'next_questions':20,
              'next_review_kind':'lot_only','next_action':'Faça o retorno vinculado.',
              'next_contact':'2026-11-05','theme_contact':None,
              'pending':{'questions':16,'due_date':'2026-11-05'},'coordinated_return':False,
              'planner_supply':None}
    monkeypatch.setattr(ui,'result_feedback',lambda *_:feedback)
    app=AppTest.from_string('''
from osler.study_activity_ui import render_result_feedback
render_result_feedback({'profile':{'review_strategy':'balanced_v2'}},'session')
''').run()
    assert not app.exception
    details=next(e for e in app.expander if e.label=='Detalhes do resultado e da revisão')
    assert not details.proto.expanded
    assert any('Interpretação detalhada' in i.value for i in details.info)
    assert not any('Interpretação detalhada' in i.value for i in app.main.info if i not in details.info)
    assert app.metric[0].value=='70,4%' and app.metric[1].value=='40,7%'
    assert any('05/11/2026' in m.value for m in app.main.markdown)
