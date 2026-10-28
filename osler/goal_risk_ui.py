"""Minha meta: fontes e incerteza à vista, sem nota futura inventada."""
import pandas as pd
import streamlit as st
from .exam_goals import ExamGoals
from .goal_risk import goal_risk_report,NOTICE
from .planner_service import today_local


def _range(m):
    return f"{m['wilson95'][0]:.1f}% a {m['wilson95'][1]:.1f}%" if m['wilson95'] else 'Sem medição'


def render_goal_risk(service):
    st.subheader('Minha meta')
    st.info(NOTICE)
    report=goal_risk_report(service,today_local().isoformat())
    if not report['targets']:
        with st.container(key='bento-goal-empty'):
            st.caption('Cadastre suas provas em Ajustes → Minhas provas. Os dados de estudo continuarão preservados.')
        return
    metadata={e['target_id']:e['target'] for e in ExamGoals(service.repository).active()}
    st.caption('Janela recente: '+report['window_start']+' até '+report['as_of']+'. Faixas de Wilson de 95%; descrevem os registros, sem prever uma nota futura.')
    for target in report['targets']:
        with st.container(key='bento-goal-'+target['target_id']):
            _render_target(target,metadata.get(target['target_id'],{}))


def _render_target(target,metadata):
    confidence={'informado':'Informada','conferido':'Conferida','estimado':'Estimada'}.get(metadata.get('cutoff_confidence'),'Não informada')
    st.markdown('**'+target['institution']+' · '+target['exam_date']+'**')
    st.write(f"{target['days_remaining']} dias restantes · {target['label']}")
    st.caption(f"Corte informado: {target['cutoff_score']:g}/{target['max_score']:g} ({target['cutoff_pct']:.1f}%). Fonte: {target['cutoff_source']} · Confiança da fonte: {confidence}")
    for warning in target['warnings']: st.caption(warning)
    st.markdown('**Simulados desta banca**')
    if target['mocks']:
        st.dataframe(pd.DataFrame([{'Data':m['day'],'Simulado':m['name'],'Acertos':m['correct'],'Questões':m['n'],
                                    'Faixa observada (95%)':_range(m),'Condições':m['conditions'],'Referência':m['label']} for m in target['mocks']]),hide_index=True,width='stretch')
        st.caption('Cada simulado mantém seu denominador. A comparação exige prova vinculada, condições realistas, inéditas e escala objetiva confirmada em Minhas provas.')
    else: st.caption('Nenhum simulado recente desta banca informado.')
    st.markdown('**Questões novas por grande área**')
    st.caption('Resultados por área orientam o estudo; não são comparados diretamente ao corte global da prova. Faixas nominais não corrigem seleção de temas ou correlação entre questões.')
    if target['areas']:
        st.dataframe(pd.DataFrame([{'Área':a['area'],'Acertos':a['correct'],'Questões':a['n'],'Faixa observada (95%)':_range(a),
                                    'Lacuna ponderada (p.p.)':a['weighted_gap_pp']} for a in target['areas']]),hide_index=True,width='stretch')
        with st.expander('Temas específicos que contribuem para as lacunas · '+target['institution']):
            topics=[t for a in target['areas'] for t in a['topics']]
            st.dataframe(pd.DataFrame([{'Tema':t['path'][-1],'Caminho':' › '.join(t['path']),'Questões novas':t['n'],
                                        'Faixa observada (95%)':_range(t),'Lacuna ponderada (p.p.)':t['weighted_gap_pp']} for t in topics]),hide_index=True,width='stretch')
            st.caption('Lacuna = incidência relativa × distância da meta de aprendizagem. Não é uma quantidade de pontos que você ganhará. Temas sem medição ou sem incidência individual não recebem lacuna estimada.')
    else: st.caption('Ainda faltam blocos exatos de questões novas para medir áreas.')
