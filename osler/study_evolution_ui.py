"""Evolução: escolher horizonte, enxergar cenário, reconhecer fatos e agir."""
from datetime import timedelta,date
import altair as alt
import pandas as pd
import streamlit as st
from .planner_service import today_local
from .planning import _date
from .study_evolution import evolution_attention
from .evolution_performance import performance_outlook
from .evolution_components import journey_html,achievement_html,point_at,number,date_label


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
        color=alt.Color('Série:N',scale=alt.Scale(domain=['Realizado','Previsto'],range=['#172b4d','#2563eb']),legend=alt.Legend(orient='bottom',title=None)),
        strokeDash=alt.StrokeDash('Série:N',scale=alt.Scale(domain=['Realizado','Previsto'],range=[[],[6,4]]),legend=None),
        tooltip=[alt.Tooltip('Data:T',format='%d/%m/%Y'),alt.Tooltip('Valor:Q',format='.1f' if coverage else ',.0f',title=title),'Série:N'])
    observed=chart.mark_point(filled=True,size=35).transform_filter(alt.datum['Série']=='Realizado')
    return (chart+observed).properties(height=280).configure_view(stroke=None).configure_axis(gridColor='#e4eaf2',labelColor='#52627a',titleColor='#52627a')


def _performance(context,selected):
    model=context['performance']; outlook=performance_outlook(model,selected)
    safety=context['snapshot'].get('imported_safety',{})
    if safety.get('weighted_pct') is not None:
        st.write(f"Ponto de partida nos arquivos: **{safety['weighted_pct']:.1f}% de segurança acumulada média por tema**, em {safety['topics']} temas com medição.")
        st.caption('Média ponderada pelas contagens por tema, incluindo recuperações nas revisões. Fica separada do acerto em questões novas e não é uma previsão de nota na prova.')
    if not model['weekly']:
        st.info('Sua curva de rendimento começa com os blocos de questões novas registrados no app. A segurança acumulada da Osler continua em Temas; ela não substitui essa série.')
        st.caption('Acompanhar acertos e convicção em novas permite distinguir aprender de reconhecer uma questão repetida.')
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
        color=alt.Color('Série:N',scale=alt.Scale(domain=['Acerto em novas','Convicção em novas','Cenário condicional'],range=['#172b4d','#166534','#2563eb']),legend=alt.Legend(orient='bottom',title=None)),
        strokeDash=alt.StrokeDash('Série:N',scale=alt.Scale(domain=['Acerto em novas','Convicção em novas','Cenário condicional'],range=[[],[],[6,4]]),legend=None),
        tooltip=[alt.Tooltip('Data:T',format='%d/%m/%Y'),alt.Tooltip('Percentual:Q',format='.1f'),'Série:N','Questões:Q']).properties(height=280)
    st.altair_chart(chart.configure_view(stroke=None),width='stretch')
    if outlook['estimate'] is None: st.info(outlook['reason'])
    else:
        st.write(f"**{outlook['method']}: {100*outlook['estimate']:.0f}%** em {date_label(selected)} · faixa exploratória de {100*outlook['lower']:.0f}% a {100*outlook['upper']:.0f}%.")
        st.caption(outlook['reason'])
    st.caption(f"{model['questions']} questões novas com acertos exatos · {model['topics']} temas. A composição dos temas pode mudar os percentuais; não é previsão de nota em prova.")


def render_evolution(service):
    profile=service.store.profile()['profile']; today=today_local()
    end=max(today.isoformat(),min(profile['exam_date'],(today+timedelta(days=547)).isoformat()))
    options=['2 semanas','1 mês','3 meses','6 meses','Fim da preparação' if profile['exam_date']<=end else 'Horizonte disponível','Escolher data']
    period=st.radio('Quero olhar para',options,index=1,horizontal=True,key='evolution_period')
    horizon={'2 semanas':14,'1 mês':30,'3 meses':90,'6 meses':180}
    selected=min(end,(today+timedelta(days=horizon.get(period,547))).isoformat())
    if period=='Escolher data': selected=st.date_input('Data da projeção',value=min(today+timedelta(days=30),date.fromisoformat(end)),min_value=today,max_value=date.fromisoformat(end),key='evolution_date',format='DD/MM/YYYY').isoformat()
    scenario=None
    with st.expander('Simular outra carga diária'):
        simulate=st.checkbox('Comparar com outra meta de questões',key='evolution_simulate')
        if simulate: scenario=int(st.number_input('Questões por dia neste cenário',1,1000,profile['max_questions'],key='evolution_questions'))
        st.caption('A simulação preserva seus ajustes. Descansos e adicionais já programados continuam valendo; ao simular outra carga, ela substitui as metas-base dos dias.')
    key=[service.agenda.token(),today.isoformat(),scenario]
    cache=st.session_state.get('evolution_context_cache',{})
    if cache.get('key')!=key:
        with st.spinner('Projetando sua jornada com a rotina atual…'):
            cache={'key':key,'context':service.evolution_context(scenario)}
            st.session_state['evolution_context_cache']=cache
    context=cache['context']; snapshot=context['snapshot']; point=point_at(snapshot,selected)
    if profile['exam_date']<today.isoformat(): st.info('A data de referência da preparação já passou. Seu histórico continua disponível; ajuste a prova para projetar os próximos meses.')
    if not context['exam_in_horizon']: st.caption('A prova está além do horizonte de18meses disponível. A jornada vai até '+date_label(end)+'.')
    if not snapshot['total_topics']: st.info('Importe seu relatório de questões para construir a jornada por temas. Nenhuma conquista ou evolução foi criada como exemplo.')
    st.subheader('Seu caminho até '+date_label(selected))
    st.caption('Realizado: registros e histórico documentado. Previsto: execução do cenário, mantendo o desempenho e os intervalos atuais.')
    st.html(journey_html(context,selected))
    with st.container(key='evolution_summary'):
        a,b,c=st.columns(3)
        a.metric('Respostas previstas',number(point['future_attempts']))
        b.metric('Temas com prática',f"{point['covered']}/{snapshot['total_topics']}")
        c.metric('Cobertura',f"{point['coverage_pct']:.1f}%" if snapshot['total_topics'] else 'Sem catálogo')
    st.caption('Respostas incluem repetições. O histórico importado conta para a cobertura; não é somado aos blocos do app. Cobertura não comprova domínio.')
    month_before=max(context['as_of'],(_date(selected)-timedelta(days=30)).isoformat())
    if selected>context['as_of'] and point['covered']==point_at(snapshot,month_before)['covered']:
        st.caption('A cobertura fica estável neste trecho do cenário porque a rotina prioriza revisões. Novos resultados e mudanças na distribuição podem abrir espaço para outros temas.')
    chart=st.radio('Acompanhar',['Questões respondidas','Cobertura dos temas','Rendimento'],horizontal=True,key='evolution_chart')
    if chart=='Rendimento': _performance(context,selected)
    else: st.altair_chart(progress_chart(context,selected,chart=='Cobertura dos temas'),width='stretch')
    st.subheader('Marcos que contam sua história')
    st.html(achievement_html(snapshot['achievements']))
    attention=evolution_attention(snapshot,selected)
    st.subheader('Onde vale colocar atenção')
    st.caption('Possíveis pontos fracos neste cenário, ordenados por prioridade relativa. O último rendimento conhecido permanece até uma nova medição real; esta lista não é dívida de estudo.')
    for item in attention[:3]:
        left,right=st.columns([3,1])
        left.markdown('**'+item['path'][-1]+'** · '+item['kind'])
        left.caption(item['reason']+' '+ ' › '.join(item['path'][:-1]))
        right.button('Ver tema',key='evolution_topic_'+item['topic_id'],on_click=_open_topic,args=(item['path'],),width='stretch')
    if not attention: st.caption('Nenhum ponto de atenção identificado pelos dados disponíveis. Isso não substitui novas medições de rendimento.')
    with st.expander('Temas e premissas em detalhe'):
        st.caption(f"Base atual: {number(snapshot['actual_attempts'])} respostas em blocos no app. Soma das contagens de questões distintas por tema nos arquivos: {number(snapshot['imported_unique'])}. Não há identificação global das questões entre temas.")
        if attention: st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Situação':r['kind'],'Motivo':r['reason'],
                                                'Última medida (%)':100*r['rate'] if r['rate'] is not None else None,
                                                'Fonte da medida':r['rate_source'],'Caminho':' › '.join(r['path'])} for r in attention]),hide_index=True,width='stretch')
        for warning in context['incidence_warnings']: st.caption(warning)
        st.caption('A projeção usa o mesmo calendário adaptativo. Menos temas novos pode limitar a cobertura até novos resultados liberarem espaço. Contatos previstos não aumentam convicção, domínio ou conquistas reais.')
        st.caption('Totais acumulados informados reconhecem cobertura, mas não são somados aos blocos realizados no app nem desbloqueiam conquistas de registros de blocos.')
        st.caption('Estimativas de rendimento usam apenas questões novas com acertos exatos; histórico insuficiente ou horizonte longo não gera percentual inventado. Não é probabilidade de aprovação.')
        st.dataframe(pd.DataFrame(snapshot['points']).query('date <= @selected')[['date','attempts','future_attempts','covered','coverage_pct','kind']].rename(columns={'date':'Data','attempts':'Respostas no app','future_attempts':'Respostas previstas adicionais','covered':'Temas cobertos','coverage_pct':'Cobertura (%)','kind':'Estado'}),hide_index=True,width='stretch')
