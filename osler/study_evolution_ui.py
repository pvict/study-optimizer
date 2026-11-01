"""Evolução: escolher horizonte, enxergar cenário, reconhecer fatos e agir."""
from .ui_help import explain
from datetime import timedelta,date
import altair as alt
import pandas as pd
import streamlit as st
from .planner_service import today_local
from .planning import _date
from .study_evolution import evolution_attention
from .evolution_performance import performance_outlook
from .evolution_components import journey_html,achievement_html,point_at,number,date_label
from .evolution_spacing import SCENARIOS,SCENARIO_VERSION


def _open_topic(path):
    st.session_state['adaptive_view']='Temas e estatísticas'
    st.session_state['statistics_search']=path[-1]
    st.session_state['statistics_focus']='Todos os temas'
    st.session_state['statistics_area']='Todas'


def progress_chart(context,selected,coverage=False):
    s=context['snapshot']
    if coverage:
        rows=[{'Data':p['date'],'Valor':p['coverage_pct'],'Série':p['kind']} for p in s['points'] if p['date']<=selected]
        rows[0]['Série']='Realizado'
        title='Temas com questões (%)'; domain=[0,100]
    else:
        rows=[{'Data':p['date'],'Valor':p['attempts'],'Série':'Realizado'} for p in s['history']]
        rows += [{'Data':p['date'],'Valor':p['attempts'],'Série':'Previsto'} for p in s['points'] if p['date']<=selected]
        title='Respostas no app (inclui repetições)'; domain=alt.Undefined
    frame=pd.DataFrame(rows)
    chart=alt.Chart(frame).mark_line(strokeWidth=3).encode(
        x=alt.X('Data:T',title=None,axis=alt.Axis(format='%d/%m',labelAngle=0,tickCount=5)),
        y=alt.Y('Valor:Q',title=title,scale=alt.Scale(domain=domain,zero=True)),
        color=alt.Color('Série:N',scale=alt.Scale(domain=['Realizado','Previsto'],range=['#1D1D1F','#0066CC']),legend=alt.Legend(orient='bottom',title=None)),
        strokeDash=alt.StrokeDash('Série:N',scale=alt.Scale(domain=['Realizado','Previsto'],range=[[],[6,4]]),legend=None),
        tooltip=[alt.Tooltip('Data:T',format='%d/%m/%Y'),alt.Tooltip('Valor:Q',format='.1f' if coverage else ',.0f',title=title),'Série:N'])
    observed=chart.mark_point(filled=True,size=35).transform_filter(alt.datum['Série']=='Realizado')
    return (chart+observed).properties(height=280).configure_view(stroke=None).configure_axis(gridColor='#e4eaf2',labelColor='#52627a',titleColor='#52627a')


def _performance(context,selected):
    model=context['performance']; outlook=performance_outlook(model,selected)
    safety=context['snapshot'].get('imported_safety',{})
    if safety.get('weighted_pct') is not None:
        st.write(f"Ponto de partida nos arquivos: **{safety['weighted_pct']:.1f}% de segurança acumulada média por tema**, em {safety['topics']} temas com medição.")
        explain('Média ponderada pelas contagens por tema, incluindo recuperações nas revisões. Fica separada do acerto em questões novas e não é uma previsão de nota na prova.')
    if not model['weekly']:
        st.info('Sua curva de rendimento começa com os blocos de questões novas registrados no app. A segurança acumulada da Osler continua em Temas; ela não substitui essa série.')
        explain('Acompanhar acertos e convicção em novas permite distinguir aprender de reconhecer uma questão repetida.')
        return
    rows=[]
    for w in model['weekly']:
        rows.append({'Data':w['date'],'Percentual':100*w['accuracy'],'Série':'Acerto em novas','Questões':w['questions']})
        if w['conviction'] is not None: rows.append({'Data':w['date'],'Percentual':100*w['conviction'],'Série':'Convicção em novas','Questões':w['confident_n']})
    if outlook['estimate'] is not None:
        last=model['weekly'][-1]
        rows.extend([{'Data':context['as_of'],'Percentual':100*last['accuracy'],'Série':'Cenário condicional','Questões':None},
                     {'Data':selected,'Percentual':100*outlook['estimate'],'Série':'Cenário condicional','Questões':None}])
    chart=alt.Chart(pd.DataFrame(rows)).mark_line(point=True,strokeWidth=2).encode(
        x=alt.X('Data:T',title=None,axis=alt.Axis(format='%d/%m',tickCount=5)),
        y=alt.Y('Percentual:Q',title='Acerto e convicção (%)',scale=alt.Scale(domain=[0,100])),
        color=alt.Color('Série:N',scale=alt.Scale(domain=['Acerto em novas','Convicção em novas','Cenário condicional'],range=['#1D1D1F','#166534','#0066CC']),legend=alt.Legend(orient='bottom',title=None)),
        strokeDash=alt.StrokeDash('Série:N',scale=alt.Scale(domain=['Acerto em novas','Convicção em novas','Cenário condicional'],range=[[],[],[6,4]]),legend=None),
        tooltip=[alt.Tooltip('Data:T',format='%d/%m/%Y'),alt.Tooltip('Percentual:Q',format='.1f'),'Série:N','Questões:Q']).properties(height=280)
    st.altair_chart(chart.configure_view(stroke=None),width='stretch')
    if outlook['estimate'] is None: st.info(outlook['reason'])
    else:
        st.write(f"**{outlook['method']}: {100*outlook['estimate']:.0f}%** em {date_label(selected)} · faixa exploratória de {100*outlook['lower']:.0f}% a {100*outlook['upper']:.0f}%.")
        st.caption(outlook['reason'])
    st.caption(f"{model['questions']} questões novas com acertos exatos · {model['topics']} temas. A composição dos temas pode mudar os percentuais; não é previsão de nota em prova.")


def render_evolution(service):
    from .evolution_history_ui import render_history
    section=st.segmented_control('Ver evolução',['Histórico','Cenários'],default='Histórico',key='evolution_section',selection_mode='single')
    if section=='Cenários':
        with st.container(key='bento-evolution-scenario'):
            st.caption('Planejamento condicional. As projeções abaixo não são estudo realizado nem previsão de nota na prova.')
            _render_scenario(service)
    else:
        render_history(service)


def _render_scenario(service):
    profile=service.store.profile()['profile']; today=today_local()
    end=max(today.isoformat(),min(profile['exam_date'],(today+timedelta(days=547)).isoformat()))
    options=['2 semanas','1 mês','3 meses','6 meses','Fim da preparação' if profile['exam_date']<=end else 'Horizonte disponível','Escolher data']
    period=st.radio('Quero olhar para',options,index=1,horizontal=True,key='evolution_period')
    horizon={'2 semanas':14,'1 mês':30,'3 meses':90,'6 meses':180}
    selected=min(end,(today+timedelta(days=horizon.get(period,547))).isoformat())
    if period=='Escolher data': selected=st.date_input('Data da projeção',value=min(today+timedelta(days=30),date.fromisoformat(end)),min_value=today,max_value=date.fromisoformat(end),key='evolution_date',format='DD/MM/YYYY').isoformat()
    scenario=None
    with st.expander('Premissas e carga da simulação'):
        spacing_scenario=st.radio('Como projetar as próximas revisões?',list(SCENARIOS),format_func=SCENARIOS.get,key='evolution_spacing')
        st.caption('O primeiro cenário amplia os intervalos conforme a política do app, se os blocos atingirem a meta com convicção. O segundo mantém os intervalos atuais. Nenhuma hipótese muda seu plano ou seus resultados.')
        simulate=st.checkbox('Comparar com outra meta de questões',key='evolution_simulate')
        if simulate: scenario=int(st.number_input('Questões por dia neste cenário',1,1000,profile['max_questions'],key='evolution_questions'))
        st.caption('A simulação preserva seus ajustes. Descansos e adicionais já programados continuam valendo; ao simular outra carga, ela substitui as metas-base dos dias.')
    key=[SCENARIO_VERSION,service.agenda.token(),today.isoformat(),scenario,spacing_scenario]
    cache=st.session_state.get('evolution_context_cache',{})
    if cache.get('key')!=key:
        with st.spinner('Projetando sua jornada com a rotina atual…'):
            cache={'key':key,'context':service.evolution_context(scenario,spacing_scenario=spacing_scenario)}
            st.session_state['evolution_context_cache']=cache
    context=cache['context']; snapshot=context['snapshot']; point=point_at(snapshot,selected)
    if profile['exam_date']<today.isoformat(): st.info('A data de referência da preparação já passou. Seu histórico continua disponível; ajuste a prova para projetar os próximos meses.')
    if not context['exam_in_horizon']: st.caption('A prova está além do horizonte de18meses disponível. A jornada vai até '+date_label(end)+'.')
    if not snapshot['total_topics']: st.info('Importe seu relatório de questões para construir a jornada por temas. Nenhuma conquista ou evolução foi criada como exemplo.')
    st.subheader('Seu caminho até '+date_label(selected))
    if spacing_scenario=='progressive':
        explain(f"Previsto se os próximos blocos atingirem sua meta com convicção: intervalos avançam até {profile['max_contact_gap']} dias, com ajuste por incidência. É uma hipótese de planejamento, sem ganho de acerto ou domínio registrado.")
    else: explain('Previsto mantendo os intervalos atuais e executando os blocos. Realizado corresponde aos registros e ao histórico documentado.')
    st.html(journey_html(context,selected))
    with st.container(key='evolution_summary'):
        a,b,c=st.columns(3)
        a.metric('Respostas previstas',number(point['future_attempts']))
        b.metric('Temas com prática',f"{point['covered']}/{snapshot['total_topics']}")
        c.metric('Cobertura',f"{point['coverage_pct']:.1f}%" if snapshot['total_topics'] else 'Sem catálogo')
    explain('Respostas incluem repetições. O histórico importado conta para a cobertura; não é somado aos blocos do app. Cobertura não comprova domínio.')
    additional=point['covered']-snapshot['covered_now']
    st.caption(f"{snapshot['covered_now']} temas hoje · +{additional} previstos")
    month_before=max(context['as_of'],(_date(selected)-timedelta(days=30)).isoformat())
    if selected>context['as_of'] and point['covered']<snapshot['total_topics'] and point['covered']==point_at(snapshot,month_before)['covered']:
        explain('Sem primeiros contatos adicionais neste trecho com os limites atuais. Mais tempo pode continuar ocupado pelas revisões; a divisão entre novos e revisões, as doses e o limite de temas por dia restringem a cobertura.')
    chart=st.radio('Acompanhar',['Questões respondidas','Cobertura dos temas','Rendimento'],horizontal=True,key='evolution_chart')
    if chart=='Rendimento': _performance(context,selected)
    else: st.altair_chart(progress_chart(context,selected,chart=='Cobertura dos temas'),width='stretch')
    st.subheader('Marcos que contam sua história')
    st.html(achievement_html(snapshot['achievements']))
    attention=evolution_attention(snapshot,selected)
    st.subheader('Onde vale colocar atenção')
    explain('Possíveis pontos fracos neste cenário, ordenados por prioridade relativa. O último rendimento conhecido permanece até uma nova medição real; esta lista não é dívida de estudo.')
    for item in attention[:3]:
        left,right=st.columns([3,1])
        left.markdown('**'+item['path'][-1]+'** · '+item['kind'])
        left.caption(item['reason']+' '+ ' › '.join(item['path'][:-1]))
        right.button('Ver tema',key='evolution_topic_'+item['topic_id'],on_click=_open_topic,args=(item['path'],),width='stretch')
    if not attention: st.caption('Nenhum ponto de atenção identificado pelos dados disponíveis. Isso não substitui novas medições de rendimento.')
    with st.expander('Temas e premissas em detalhe'):
        st.caption(f"Base atual: {number(snapshot['actual_attempts'])} respostas em blocos no app. Soma das contagens de questões distintas por tema nos arquivos: {number(snapshot['imported_unique'])}. Não há identificação global das questões entre temas.")
        if snapshot.get('non_additive_topics'):
            st.caption('Temas com histórico abrangendo subtemas aparecem na cobertura e em suas fichas; suas contagens importadas e convicção não foram somadas novamente aos totais dos filhos.')
        if attention: st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Situação':r['kind'],'Motivo':r['reason'],
                                                'Última medida (%)':100*r['rate'] if r['rate'] is not None else None,
                                                'Fonte da medida':r['rate_source'],'Caminho':' › '.join(r['path'])} for r in attention]),hide_index=True,width='stretch')
        for warning in context['incidence_warnings']: st.caption(warning)
        st.caption('A projeção usa o alocador do calendário com a hipótese selecionada. Somente a Evolução permite avançar intervalos de forma condicional; o calendário operacional continua dependendo de resultados reais. Contatos previstos não aumentam convicção, domínio ou conquistas reais.')
        st.caption('Doses e rendimento conhecidos são mantidos. Os lotes já conhecidos entram no cálculo; não são gerados novos lotes nem resíduos hipotéticos de erros de 7 dias. Erros e faltas futuros podem exigir mais revisões e reduzir a cobertura deste cenário.')
        if point.get('reviews_waiting') or point.get('pending_responses'):
            st.caption(f"Nesta data do cenário: {point.get('reviews_waiting',0)} temas com revisão prevista aguardariam vaga e {point.get('pending_responses',0)} respostas de lotes conhecidos aguardariam revisão. São limites previstos, sem criar pendências reais.")
        st.caption('Totais acumulados informados reconhecem cobertura, mas não são somados aos blocos realizados no app nem desbloqueiam conquistas de registros de blocos.')
        st.caption('Estimativas de rendimento usam apenas questões novas com acertos exatos; histórico insuficiente ou horizonte longo não gera percentual inventado. Não é probabilidade de aprovação.')
        st.dataframe(pd.DataFrame(snapshot['points']).query('date <= @selected')[['date','attempts','future_attempts','covered','coverage_pct','kind']].rename(columns={'date':'Data','attempts':'Respostas no app','future_attempts':'Respostas previstas adicionais','covered':'Temas cobertos','coverage_pct':'Cobertura (%)','kind':'Estado'}),hide_index=True,width='stretch')
