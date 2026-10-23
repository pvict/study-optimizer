"""Recuperação em quatro escolhas, prévia concreta e desfazer sem perder estudo."""
from datetime import timedelta,date
import hashlib,json
import pandas as pd
import streamlit as st
from .planner_service import today_local
from .study_replanning import MODES


def render_replanning(service,context):
    rows=context['backlog']
    with st.expander(f"Resumo de atrasos · {len(rows)} temas",expanded=bool(rows)):
        a,b,c=st.columns(3)
        a.metric('Temas atrasados',len(rows))
        b.metric('Recuperações agendadas',len(context['rows']))
        booked={r['topic_id'] for r in context['rows']}
        c.metric('Atrasados sem nova data',sum(r['topic_id'] not in booked for r in rows))
        st.caption('Vermelho: atraso confirmado · Azul: recuperação agendada · Laranja: pendência prevista. O atraso permanece até registrar o estudo.')
    with st.expander('Reorganizar atrasos',expanded=False):
        if not rows: st.info('Nenhum atraso confirmado. Temas sem data de contato conhecida não são considerados atrasados.')
        else:
            mode=st.radio('Como quer recuperar?',list(MODES),format_func=MODES.get,key='replan_mode')
            st.caption({'balanced':'Mantém sua meta e sua divisão entre novos e revisões. Recuperações ocupam vagas do grupo correspondente.',
                        'reviews':'Mantém a quantidade diária e reserva o período para revisões. A divisão normal volta depois.',
                        'extra':'Adiciona questões só neste período, destinadas às revisões. Não altera sua meta padrão.',
                        'custom':'Escolha a data de cada tema na tabela. As cotas e os limites diários continuam valendo.'}[mode])
            first,period=st.columns(2)
            start=first.date_input('Começar em',today_local(),min_value=today_local(),max_value=today_local()+timedelta(days=458),key='replan_start',format='DD/MM/YYYY')
            days=period.number_input('Distribuir em quantos dias?',1,90,7,key='replan_days')
            extra=st.number_input('Questões adicionais por dia',0,300,20,step=5,key='replan_extra') if mode=='extra' else 20
            all_selected=st.checkbox('Incluir todos os temas atrasados',value=True,key='replan_all')
            defaults=pd.DataFrame([{'Incluir':all_selected,'Tema':r['path'][-1],'Caminho':' › '.join(r['path']),
                                    'Dias de atraso':r['days_late'],'Questões':r['questions'],'Nova data':start,
                                    'topic_id':r['topic_id']} for r in rows])
            signature=hashlib.sha256(json.dumps([[r['topic_id'] for r in rows],start.isoformat(),all_selected]).encode()).hexdigest()[:12]
            fields=['Incluir','Tema','Dias de atraso','Questões']+(['Nova data'] if mode=='custom' else [])
            edited=st.data_editor(defaults[fields],hide_index=True,width='stretch',key='replan_topics_'+signature,
                                  disabled=[k for k in fields if k not in ['Incluir','Nova data']],
                                  column_config={'Nova data':st.column_config.DateColumn(min_value=start,max_value=start+timedelta(days=int(days)-1))})
            selected=[r['topic_id'] for i,r in enumerate(rows) if edited.iloc[i]['Incluir']]
            dates={r['topic_id']:edited.iloc[i]['Nova data'].isoformat() for i,r in enumerate(rows) if mode=='custom' and edited.iloc[i]['Incluir'] and edited.iloc[i]['Nova data'] is not None}
            options=[start.isoformat(),int(days),mode,selected,int(extra),dates]
            option_key=hashlib.sha256(json.dumps(options,sort_keys=True).encode()).hexdigest()
            if st.button('Montar prévia de reagendamento',key='generate_replan_preview',disabled=not selected):
                preview=service.preview_replan(*options[:3],selected=selected,extra_questions=int(extra),dates=dates)
                st.session_state['replan_preview']={'options':option_key,'preview':preview}
            saved=st.session_state.get('replan_preview',{})
            if saved.get('options')==option_key:
                preview=saved['preview']
                if preview['rows']:
                    st.markdown('**Confira sua recuperação**')
                    st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Vencia em':r['original_due'],'Reagendado para':r['date'],'Questões':r['questions']} for r in preview['rows']]),hide_index=True,width='stretch')
                    st.caption('Os temas de maior risco recebem as primeiras vagas disponíveis. Atraso relativo, erros, incidência e retornos de7dias orientam essa ordem; é uma prioridade de planejamento, não uma previsão pessoal de memória.')
                if preview['unassigned']:
                    st.warning(f"{len(preview['unassigned'])} temas ficaram sem vaga. Amplie o período, mude a estratégia ou ajuste a carga.")
                    st.caption('Ao aplicar, as datas anteriores dos temas selecionados serão substituídas. Os selecionados sem vaga ficarão sem nova data e continuarão na lista de atrasos. Você poderá desfazer esta redistribuição.')
                    st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Questões':r['questions'],'Motivo':r['reason']} for r in preview['unassigned']]),hide_index=True,width='stretch')
                stale=preview['token']!=context['token']
                if stale: st.warning('Os dados mudaram. Monte uma nova prévia antes de aplicar.')
                if st.button('Aplicar este reagendamento',key='apply_replan_preview',type='primary',disabled=stale or not preview['rows']):
                    service.apply_replan(preview)
                    st.session_state.pop('replan_preview',None)
                    st.session_state['adaptive_notice']='Recuperação agendada. Nenhum estudo foi marcado como feito.'
                    st.rerun()
        recoveries=[r for r in context['active'] if r.get('scope') not in {'final_review','mock_day'}]
        if recoveries:
            last=recoveries[-1]
            st.divider()
            st.caption(f"Última redistribuição: {MODES[last['mode']]} · início {last['start']} · {last['days']}dias. Desfazer preserva todos os resultados registrados.")
            if st.button('Desfazer última redistribuição',key='undo_last_replan'):
                service.cancel_replan(last['id'],context['token'])
                st.session_state.pop('replan_preview',None)
                st.session_state['adaptive_notice']='Redistribuição desfeita. Seus estudos continuam no histórico.'
                st.rerun()
