"""Dados necessários, impacto e aplicação explícita no mesmo contexto."""
from .action_feedback import confirm_button,confirm_submit,notify_success

import pandas as pd
import streamlit as st
from .exam_goals import active_exams


def _clear(): st.session_state.pop('exam_weight_preview_data',None)


def render_exam_weights(service):
    exams=active_exams(service.repository); record=service.store.profile(); p=record['configured_profile']
    if not exams and not p['exam_weights'] and not any(w!=1 for w in p['institution_weights'].values()): return
    with st.expander('Importância das provas e aviso de aproximação'):
        st.caption('Mudar a importância mantém as outras instituições selecionadas. Para ponderar o conjunto, cada instituição precisa ter uma tabela individual importada e aplicável. A tabela conjunta continua sendo usada sem pesos individuais.')
        selected={}; missing=set(); suffix='_'+str(record['id'])
        for e in exams:
            key=e['target_id']; name=e['target']['institution']+' · '+e['target']['exam_date']
            eligibility=service.exam_weight_eligibility({key:p['exam_weights'].get(key,1.5)})
            missing.update(eligibility['missing'])
            active=key in p['exam_weights']
            enabled=st.checkbox('Personalizar importância · '+name,value=active,disabled=not eligibility['allowed'] and not active,
                                key='exam_weight_use_'+key+suffix,on_change=_clear)
            weight=st.number_input('Importância · '+name,min_value=.1,value=float(p['exam_weights'].get(key,1)),
                                   disabled=not enabled or not eligibility['allowed'],key='exam_weight_value_'+key+suffix,on_change=_clear)
            if enabled: selected[key]=weight
        if missing: st.info('Pesos bloqueados enquanto faltar incidência individual para: '+', '.join(sorted(missing))+'. Envie os arquivos em Ajustes → Instituições e incidências.')
        days=st.number_input('Avisar quando faltarem quantos dias? (0 desliga)',0,90,p['approach_days'],key='approach_days'+suffix,on_change=_clear)
        allowed=service.exam_weight_eligibility(selected)['allowed']
        if st.button('Ver prévia da importância e do aviso',key='exam_weight_preview',disabled=not allowed):
            try: st.session_state['exam_weight_preview_data']=service.preview_exam_weights(selected,int(days))
            except ValueError as exc:
                _clear(); st.error(str(exc))
        preview=st.session_state.get('exam_weight_preview_data')
        if not preview or preview['weights']!=selected or preview['approach_days']!=days: return
        before,after=preview['before'],preview['after']
        st.markdown('**Confira tudo que será alterado**')
        if preview['legacy_weights_before']!=preview['legacy_weights_after']:
            st.info('Pesos antigos definidos diretamente nas instituições serão retirados. Os nomes serão mantidos; a importância será definida apenas pelas provas selecionadas acima.')
            st.dataframe(pd.DataFrame([{'Instituição':n,'Peso antigo salvo':w,'Peso base depois':preview['legacy_weights_after'][n]}
                for n,w in preview['legacy_weights_before'].items()]),hide_index=True,width='stretch')
        names=list(dict.fromkeys([*before['weights'],*after['weights']]))
        st.dataframe(pd.DataFrame([{'Instituição':n,'Peso antes':before['weights'].get(n),'Peso depois':after['weights'].get(n)} for n in names]),hide_index=True,width='stretch')
        st.caption(f"Aviso de aproximação: {before['approach_days']} → {after['approach_days']} dias. Carga: {before['max_questions']} → {after['max_questions']} questões/dia. Data de referência: {before['exam_date']} → {after['exam_date']}.")
        st.caption(f"Temas com incidência conhecida: {before['coverage']:.1%} → {after['coverage']:.1%}. Acertos, convicção, histórico e parâmetros de repetição não serão reescritos.")
        today_before={r['topic_id']:r for r in before['today']}; today_after={r['topic_id']:r for r in after['today']}
        ids=list(dict.fromkeys([*today_before,*today_after]))
        st.markdown('**Blocos de hoje**')
        st.dataframe(pd.DataFrame([{'Tema':(today_after.get(k) or today_before[k])['path'][-1],
                                   'Questões antes':today_before.get(k,{}).get('questions',0),'Questões depois':today_after.get(k,{}).get('questions',0)} for k in ids]),hide_index=True,width='stretch')
        with st.expander('Fontes e demais mudanças na previsão'):
            st.caption('Próximos contatos comparados até '+preview['window_end']+'. Resultados futuros podem mudar estas datas; o efeito de pesos posteriores à janela não é listado aqui.')
            st.dataframe(pd.DataFrame(preview['sources']),hide_index=True,width='stretch')
            st.caption(f"{len(preview['rank_changes'])} temas com incidência ou prioridade alterada.")
            st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Prioridade antes':r['before_priority'],'Prioridade depois':r['after_priority'],
                'Estado antes':{'dominado':'Dominado','aprendendo':'Aprendendo','alerta':'Em alerta'}.get(r['before_state'],r['before_state']),
                'Estado depois':{'dominado':'Dominado','aprendendo':'Aprendendo','alerta':'Em alerta'}.get(r['after_state'],r['after_state']),
                'Incidência antes (%)':100*r['before_importance'],'Incidência depois (%)':100*r['after_importance']} for r in preview['rank_changes']]),hide_index=True,width='stretch',height=240)
            st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Antes':r['before_date'] or 'Sem vaga na janela anterior',
                'Depois':r['after_date'] or 'Sem vaga nesta janela','Questões antes':r['questions'],'Questões depois':r['after_questions']} for r in preview['topic_changes']]),hide_index=True,width='stretch',height=240)
            for warning in after['warnings']: st.caption(warning)
        stale=preview['token']!=service.agenda.token()
        if stale: st.info('Os dados mudaram. Monte outra prévia antes de aplicar.')
        if confirm_button('Aplicar importância e aviso',key='exam_weight_apply',type='primary',disabled=stale,action_key='exam_weights_ui_63'):
            try: notify_success(service.apply_exam_weights(preview),'Agenda atualizada.')
            except ValueError as exc:
                _clear(); st.error(str(exc)); return
            _clear()
            st.session_state.pop('adaptive_profile_snapshot',None)
            st.session_state['adaptive_notice']='Importância e aviso atualizados conforme a prévia; histórico preservado.'
            st.rerun()
