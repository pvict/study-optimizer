"""Conversa semanal curta, sem ajustes automáticos ou cobrança de faltas."""
from .action_feedback import confirm_button,confirm_submit,notify_success

import pandas as pd
import streamlit as st
from .planner_service import today_local
from .weekly_review import WeeklyReviewStore,weekly_summary,absence_notice


def render_absence_notice(service,as_of=None):
    notice=absence_notice(service,as_of or today_local().isoformat())
    if notice: st.info(f"Há {notice['days']} dias sem registro local de estudo. Você pode retomar pelo plano de hoje ou ajustar a carga. Isso não significa que você ficou sem estudar.")


def render_weekly_review(service,as_of=None):
    as_of=as_of or today_local().isoformat()
    with st.expander('Revisão da semana (opcional)'):
        report=weekly_summary(service,as_of); store=WeeklyReviewStore(service.repository)
        key=report['week_key']; old=next(iter(store.active(key)),None)
        snapshot_key='weekly_snapshot_'+key
        old=st.session_state.setdefault(snapshot_key,old)
        if st.button('Recarregar revisão salva',key='weekly_reload_'+key):
            for widget in [snapshot_key,'weekly_blocked_'+key,'weekly_load_'+key,'weekly_rest_'+key]:
                st.session_state.pop(widget,None)
            st.rerun()
        st.caption(report['current']['start']+' a '+report['current']['end']+' · comparação com os mesmos dias da semana anterior. Variações descritivas; amostras podem ser pequenas.')
        a=report['current']['adhesion']
        st.write(f"{a['done_blocks']} de {a['planned_blocks']} blocos salvos concluídos · {report['current']['late_blocks']} ainda incompletos · {report['current']['open_errors']} erros abertos · {report['current']['mocks']} simulados.")
        delta=report['changes']
        errors=f"{delta['open_errors']:+d}" if delta['open_errors'] is not None else 'sem fotografia comparável'
        st.caption(f"Variação: blocos incompletos {delta['late_blocks']:+d} · simulados {delta['mocks']:+d} · erros abertos: {errors}.")
        st.caption('Erro aberto é o estado atual. Sem uma fotografia antiga, não estimamos quantos estavam abertos na semana anterior.')
        if report['accuracy']:
            st.dataframe(pd.DataFrame([{'Área':r['area'],'Fonte':r['source'],'Contexto':r['context'],'Questões nesta semana':r['current']['questions'],
                                        'Acerto nesta semana (%)':100*r['current']['accuracy'] if r['current']['accuracy'] is not None else None,
                                        'Mudança (p.p.)':r['change_pp']} for r in report['accuracy']]),hide_index=True,width='stretch')
        if report['suggested_questions']:
            st.caption(f"Sugestão para considerar: experimentar {report['suggested_questions']} questões por dia. É uma heurística de carga, não uma prescrição. Nenhuma meta foi alterada; se fizer sentido, ajuste em Ajustes → Meta e rotina.")
        values=old['review']['answers'] if old else {}
        with st.form('weekly_review_'+key):
            blocked=st.text_input('O que travou sua semana?',value=values.get('blocked',''),max_chars=1000,key='weekly_blocked_'+key)
            change=st.text_input('O que gostaria de mudar na carga?',value=values.get('load_change',''),max_chars=1000,key='weekly_load_'+key)
            rest=st.checkbox('Preciso reservar descanso',value=values.get('needs_rest',False),key='weekly_rest_'+key)
            save=confirm_submit('Salvar revisão da semana' if not old else 'Salvar nova versão da revisão',action_key='weekly_review_ui_42')
        if save:
            notify_success(store.save(key,{'blocked':blocked,'load_change':change,'needs_rest':rest},expected_version=old['version'] if old else 0,summary=report),'Alterações salvas.')
            st.session_state.pop(snapshot_key,None)
            st.success('Revisão salva. Sua rotina não foi alterada.')
        history=store.events()
        if history:
            with st.expander('Histórico das revisões semanais'):
                st.dataframe(pd.DataFrame([{'Semana':r['week_key'],'Versão':r['version'],'Estado':r['action'],'Registrado em':r['created_at']} for r in history]),hide_index=True,width='stretch')
