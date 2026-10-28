"""Demanda e capacidade visíveis; uma proposta segura pode permanecer vazia."""
from datetime import date,timedelta
import pandas as pd
import streamlit as st
from .planner_service import today_local
from .study_models import AdaptiveProfile
from .study_replanning import effective_routine
from .final_review import special_config
from .study_triage_policy import propose_triage


def render_triage(service):
    st.subheader('Plano de corte')
    with st.container(key='bento-triage-summary'):
        days=st.selectbox('Horizonte da comparação',[14,28,90,180],index=1,format_func=lambda n:f'{n} dias',key='triage_days')
        view=service.overview(today_local().isoformat()); p=AdaptiveProfile(**view['profile']); start=view['date']; end=min(p.exam_date,(today_local()+timedelta(days=days-1)).isoformat())
        if end<start: st.info('Confira a data da prova em Ajustes.'); return
        settings=service.store.days(); calendar=[]
        for i in range((date.fromisoformat(end)-today_local()).days+1):
            day=(today_local()+timedelta(days=i)).isoformat(); over=view['agenda']['overrides'].get(day,{})
            config=special_config(settings.get(day,{'questions':p.max_questions,'kind':'normal','extra_topics':[]}),over)
            _,q=effective_routine(p,config,over)
            calendar.append({'date':day,'target_questions':0 if config['kind']=='descanso' or p.start_date and day<p.start_date else q,
                             'done_questions':view['plan']['done_questions'] if day==start else 0})
        summary=propose_triage(view['planning_states'],calendar,start,end,max_gap=p.max_contact_gap)
        balance=f"{summary['deficit_questions']:,} acima da carga" if summary['balance_questions']>=0 else f"{-summary['balance_questions']:,} de folga na carga"
        st.write(f"Demanda condicional: {summary['demand_questions']:,} questões · capacidade: {summary['capacity_questions']:,} · diferença: {balance}.")
        st.caption('Revisões já iniciadas e retornos conhecidos, repetindo doses e intervalos atuais. Temas na fila inicial não viram revisões recorrentes. A capacidade é a carga total; parte dela também atende temas novos. Este cenário não é uma quantidade comprovadamente necessária.')
    with st.container(key='bento-triage-controls'):
        with st.expander('Como montar a proposta'):
            factor=st.number_input('Multiplicar o intervalo futuro por',1.,3.,1.5,.25,key='triage_factor')
            defer=st.number_input('Permitir adiamento do próximo contato futuro (dias)',0,14,0,key='triage_defer')
            st.caption('Primeiro menor incidência, depois maior convicção e amostra. Exigimos inéditas, ao menos 30 respostas e Wilson inferior de 80%. Sem medição, com erro aberto ou fragilidade: manter. O máximo entre contatos da sua rotina continua valendo.')
        if st.button('Montar prévia do corte',key='triage_preview'):
            st.session_state['triage_preview_data']=service.preview_triage(int(days),float(factor),int(defer))
    preview=st.session_state.get('triage_preview_data')
    if preview and (preview['days'],preview['frequency_factor'],preview['defer_days'])==(days,factor,defer):
        with st.container(key='bento-triage-preview'):
            st.write(f"Diferença antes: {preview['before']['deficit_questions']:,} questões · após a proposta: {preview['after']['deficit_questions']:,}.")
            st.caption(f"Tentativas com vaga no cenário: {preview['projected_questions_before']:,} antes → {preview['projected_questions_after']:,} depois. Menos frequência pode custar retenção; a mudança é opcional e temporária.")
            changed=[r for r in preview['rows'] if r['action']!='manter']
            frame=[{'Tema':r['path'][-1],'Decisão':r['action'],'Intervalo atual':r['old_interval'],'Intervalo proposto':r['new_interval'],
                    'Adiar até':r.get('defer_until'),'Motivo':r['reason']} for r in preview['rows']]
            if changed: st.dataframe(pd.DataFrame([r for r in frame if r['Decisão']!='manter']),hide_index=True,width='stretch')
            kept=[r for r in frame if r['Decisão']=='manter']
            with st.expander(f'Temas mantidos e motivos ({len(kept)})'):
                st.dataframe(pd.DataFrame(kept),hide_index=True,width='stretch',height=280)
            if not changed: st.info('Não há redução segura com os dados e limites atuais. A diferença de capacidade permanece; considere ajustar carga ou horizonte.')
            if st.button('Aplicar esta política de corte',key='triage_apply',disabled=not changed,type='primary'):
                service.apply_triage(preview); st.session_state.pop('triage_preview_data',None); st.success('Política aplicada. Você pode desfazer abaixo.'); st.rerun()
    active=service.agenda.active(view['sessions'],view['date'])['active']
    for r in active:
        if r.get('scope')=='triage' and st.button('Desfazer plano de corte',key='triage_undo_'+str(r['id'])):
            service.cancel_replan(r['id']); st.success('Frequência anterior restaurada; estudo preservado.'); st.rerun()
