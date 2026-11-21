"""Histórico observado e sua apresentação; não projeta aprendizagem ou altera planos."""
from .ui_help import explain
from collections import defaultdict
from datetime import timedelta
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from .bento import AREA_LABELS,area_slug,bar,eyebrow
from .classification import wilson_interval
from .final_review import special_config
from .planning import _date
from .study_models import AdaptiveProfile
from .study_replanning import effective_routine


def observed_history(sessions,as_of,profile,settings,overrides,*,weeks=8,area_results=()):
    """Bases descritivas separadas; a meta é referência da rotina atual, não passado inferido."""
    today=_date(as_of);monday=today-timedelta(days=today.weekday())
    entries=[s['entry'] for s in sessions if s['entry']['day']<=as_of and s['entry']['kind']!='acumulado']
    from .exam_practice import area_extra_volume
    extra=area_extra_volume(area_results,sessions,as_of)
    first=monday-timedelta(weeks=weeks-1) if weeks else min([_date(e['day']) for e in entries]+[_date(d) for d in extra]+[today])
    first-=timedelta(days=first.weekday())
    entries=[e for e in entries if e['day']>=first.isoformat()]
    measured=[e for e in entries if e['kind']=='bloco' and e['mode']=='novas' and
              not e.get('review_of') and e.get('correct') is not None]
    by_week={};cursor=first
    while cursor<=today:
        by_week[cursor.isoformat()]={'date':cursor.isoformat(),'new_n':0,'correct':0,'conviction_n':0,
                                    'confident':0,'volume':0,'target':None}
        cursor+=timedelta(days=7)
    def week(e):
        day=_date(e['day']);return by_week[(day-timedelta(days=day.weekday())).isoformat()]
    for e in entries:
        if e['kind']=='bloco':week(e)['volume']+=e['questions']
    for day,n in extra.items():
        if day>=first.isoformat(): week({'day':day})['volume']+=n
    areas=defaultdict(lambda:{'n':0,'correct':0})
    for e in measured:
        row=week(e);row['new_n']+=e['questions'];row['correct']+=e['correct']
        if e.get('confident_correct') is not None:
            row['conviction_n']+=e['questions'];row['confident']+=e['confident_correct']
        area=areas[e['path'][0]];area['n']+=e['questions'];area['correct']+=e['correct']
    cursor=first
    while cursor<=today:
        day=cursor.isoformat()
        if not profile.start_date or day>=profile.start_date:
            config=special_config(settings.get(day,{'questions':profile.max_questions,'kind':'normal','extra_topics':[]}),overrides.get(day,{}))
            _,target=effective_routine(profile,config,overrides.get(day,{}))
            row=by_week[(cursor-timedelta(days=cursor.weekday())).isoformat()]
            row['target']=(row['target'] or 0)+(0 if config['kind']=='descanso' else target+overrides.get(day,{}).get('area_reserved',0))
        cursor+=timedelta(days=1)
    for w in by_week.values():
        w['accuracy']=100*w['correct']/w['new_n'] if w['new_n'] else None
        w['conviction']=100*w['confident']/w['conviction_n'] if w['conviction_n'] else None
    area_rows=[]
    for name,a in sorted(areas.items()):
        rate=100*a['correct']/a['n'];lower,upper=wilson_interval(rate,a['n'])
        area_rows.append({'area':name,**a,'rate':rate,'lower':lower,'upper':upper})
    n=sum(e['questions'] for e in measured);correct=sum(e['correct'] for e in measured)
    return {'weeks':list(by_week.values()),'areas':area_rows,'new_n':n,'correct':correct,
            'accuracy':100*correct/n if n else None,'volume':sum(w['volume'] for w in by_week.values()),
            'study_days':len({e['day'] for e in entries}|{d for d,n in extra.items() if n and d>=first.isoformat()}),'start':first.isoformat(),'end':as_of}


def _chart_style(chart,height=260):
    return chart.properties(height=height).configure_view(stroke=None).configure_axis(
        gridColor='#E5E7EB',labelColor='#4B5563',titleColor='#4B5563',labelFontSize=12,titleFontSize=12
    ).configure_legend(labelColor='#4B5563',labelFontSize=12)


def _accuracy_chart(model):
    rows=[]
    for w in model['weeks']:
        for key,label,n in [('accuracy','Acerto em novas',w['new_n']),('conviction','Acerto com convicção',w['conviction_n'])]:
            rows.append({'Semana':w['date'],'Percentual':w[key],'Série':label,'Amostra':n})
    chart=alt.Chart(pd.DataFrame(rows)).mark_line(point=alt.OverlayMarkDef(filled=True,size=45),strokeWidth=2).encode(
        x=alt.X('Semana:T',title=None,axis=alt.Axis(format='%d/%m',tickCount=4,labelAngle=0)),
        y=alt.Y('Percentual:Q',title='Acertos (%)',scale=alt.Scale(domain=[0,100])),
        color=alt.Color('Série:N',scale=alt.Scale(domain=['Acerto em novas','Acerto com convicção'],range=['#111827','#0066CC']),legend=alt.Legend(orient='bottom',title=None)),
        strokeDash=alt.StrokeDash('Série:N',scale=alt.Scale(domain=['Acerto em novas','Acerto com convicção'],range=[[],[5,3]]),legend=None),
        tooltip=[alt.Tooltip('Semana:T',format='%d/%m/%Y'),alt.Tooltip('Percentual:Q',format='.1f'),'Amostra:Q','Série:N'])
    st.altair_chart(_chart_style(chart),width='stretch')


def _volume_chart(model):
    rows=[{'Semana':w['date'],'Questões':w[key],'Série':label} for w in model['weeks']
          for key,label in [('volume','Registradas'),('target','Referência atual')]]
    chart=alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(
        x=alt.X('Semana:T',title=None,axis=alt.Axis(format='%d/%m',tickCount=4,labelAngle=0)),
        xOffset='Série:N',y=alt.Y('Questões:Q',title='Questões'),
        color=alt.Color('Série:N',scale=alt.Scale(domain=['Registradas','Referência atual'],range=['#0066CC','#D1D5DB']),legend=alt.Legend(orient='bottom',title=None)),
        tooltip=[alt.Tooltip('Semana:T',format='%d/%m/%Y'),'Questões:Q','Série:N'])
    st.altair_chart(_chart_style(chart),width='stretch')


def render_history(service):
    from .planner_service import today_local
    today=today_local().isoformat();sessions=service.store.active(today)
    profile=AdaptiveProfile(**service.store.profile()['profile'])
    with st.container(key='bento-evolution-controls'):
        period=st.radio('Histórico de',['4 semanas','8 semanas','Todo o período'],index=1,horizontal=True,key='evolution_history_period')
        explain('Somente registros realizados. Treinos por área entram no volume uma vez; seus acertos ficam em Simulados. Arquivos importados têm bases próprias.')
    agenda=service.agenda.active(sessions,today)
    model=observed_history(sessions,today,profile,service.store.days(),agenda['overrides'],
                           weeks={'4 semanas':4,'8 semanas':8,'Todo o período':None}[period],area_results=agenda.get('area_results',[]))
    with st.container(key='bento-evolution-summary'):
        a,b,c=st.columns(3)
        a.metric('Questões registradas',f"{model['volume']:,}".replace(',','.'))
        a.caption('Inclui novas, repetidas e mistas.')
        b.metric('Acerto em novas',f"{model['accuracy']:.1f}%" if model['accuracy'] is not None else '—')
        b.caption(f"n = {model['new_n']} · acertos exatos em questões novas.")
        c.metric('Dias com estudo',model['study_days'])
        c.caption('Dias com registros no período escolhido.')
    if not model['volume']:
        st.info('Registre um bloco para começar seu histórico. O primeiro resultado aparece aqui com sua amostra, sem evolução demonstrativa.')
    with st.container(key='bento-evolution-charts'):
        left,right=st.columns([1.4,1],gap='medium')
        with left,st.container(key='bento-evolution-accuracy'):
            st.subheader('Seu rendimento por semana')
            if model['new_n']:_accuracy_chart(model)
            else:st.info('Registre questões novas com acertos exatos para visualizar o rendimento. Repetidas e acertos acumulados não completam essa curva.')
            explain('Acerto e convicção têm amostras identificadas em cada ponto. Sem registro, a curva tem uma lacuna; não vira 0%.')
        with right,st.container(key='bento-evolution-volume'):
            st.subheader('Seu ritmo de questões')
            _volume_chart(model)
            explain('Referência: rotina atual nos dias já decorridos, respeitando início, descanso e simulados programados. Metas históricas podem ter sido diferentes.')
    with st.container(key='bento-evolution-areas'):
        st.subheader('Acerto por área')
        explain('Questões novas com acertos exatos. As faixas Wilson de 95% mostram a incerteza da amostra; não são previsão de nota.')
        if not model['areas']:st.caption('Ainda não há amostra de questões novas neste período.')
        for row in model['areas']:
            slug=area_slug([row['area']]);label=f"{row['rate']:.1f}% · n = {row['n']}"
            st.html('<div class="o-history-area"><div class="o-history-area-label">'+eyebrow(row['area'],slug)+
                    '<strong>'+escape(label)+'</strong></div>'+bar(row['rate']/100,slug,label=label)+
                    '<p>Faixa Wilson 95%: '+f"{row['lower']:.1f}% a {row['upper']:.1f}%"+'</p></div>')
    with st.expander('Ver números do histórico'):
        st.dataframe(pd.DataFrame(model['weeks']).rename(columns={'date':'Semana','new_n':'Amostra de novas','accuracy':'Acerto em novas (%)',
            'conviction_n':'Amostra com convicção','conviction':'Acerto com convicção (%)','volume':'Questões registradas','target':'Referência atual'})[
                ['Semana','Questões registradas','Referência atual','Acerto em novas (%)','Amostra de novas','Acerto com convicção (%)','Amostra com convicção']],hide_index=True,width='stretch')
