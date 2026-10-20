"""Tabela de temas e resultados com filtros de calendário e ações no contexto."""
import pandas as pd
import streamlit as st
import hashlib
import json
from html import escape

from .exports import _safe_cell
from .models import normalize_path
from .planner_service import today_local
from .study_statistics import topic_statistics, period_bounds, PERIODS, MODES
from .study_trajectory_ui import render_trajectories


def _open_extra(topic_id):
    st.session_state['adaptive_view']='Meu dia'
    st.session_state['extra_topic']=topic_id


def _set_focus(focus):
    st.session_state['statistics_focus']=focus


def _topic_list(rows,signature,go_record,cumulative=False):
    if not rows:
        st.info('Nenhum tema nesses filtros. Tente outra busca ou escolha Todos os temas.')
        return
    pages=(len(rows)+11)//12
    page=int(st.number_input('Página de temas',1,pages,1,key='statistics_list_page_'+signature)) if pages>1 else 1
    st.caption(f'{len(rows)} temas · página {page} de {pages}')
    for row in rows[(page-1)*12:page*12]:
        with st.container(border=True):
            st.markdown('**'+row['Tema']+'**')
            st.caption(row['Caminho'])
            accuracy=f"{row['Acerto (%)']:.1f}%" if row['Acerto (%)'] is not None else 'Sem medição exata'
            confidence=f"{row['Com convicção (%)']:.1f}%" if row['Com convicção (%)'] is not None else 'Não informada'
            due=row['Próxima revisão'] or 'Não programada'
            if cumulative:
                conviction=f"{row['Convicção (%)']:g}%" if row['Convicção (%)'] is not None else 'Não informada'
                st.write((str(row['Questões realizadas']) if row['Questões realizadas'] is not None else 'Sem contagem')+' questões realizadas · Convicção: '+conviction)
                st.caption(row['Fonte do histórico'])
            else:
                st.html('<div class="study-list-summary"><span>'+escape(row['Estado'])+'</span><span><strong>'+str(row['Questões'])+
                        '</strong> questões no período</span><span>Acerto: <strong>'+escape(accuracy)+
                        '</strong></span><span>Convicção: '+escape(confidence)+'</span></div>')
            st.caption('Próxima revisão: '+due)
            if row.get('Meta do tema (%)') is not None: st.caption(f"Meta do tema: {row['Meta do tema (%)']:g}% · acerto com convicção em questões novas e amostra suficiente.")
            if row.get('Segurança acumulada Osler (%)') is not None:
                st.caption(f"Segurança acumulada Osler: {row['Segurança acumulada Osler (%)']:g}% em {row['Questões distintas Osler']} questões distintas · retrato de {row['Retrato Osler']}. Inclui recuperações nas revisões.")
            left,right=st.columns(2)
            left.button('Registrar resultado',key='list_record_'+row['topic_id'],on_click=go_record,args=(row['topic_id'],10),disabled=not row['catalog_available'],width='stretch')
            right.button('Adiantar hoje',key='list_extra_'+row['topic_id'],on_click=_open_extra,args=(row['topic_id'],),disabled=not row['catalog_available'],width='stretch')
            if not row['catalog_available']: st.caption('Histórico preservado. Importe um relatório deste tema para planejar novos blocos.')


def render_topic_table(service,go_record):
    view=service.overview(today_local().isoformat())
    counts={phase:sum(t.get('learning_state')==phase for t in view['planning_states']) for phase in ['dominado','aprendendo','alerta']}
    st.caption('Situação atual dos temas · selecione um grupo para filtrar')
    with st.container(key='topic_states'):
        panels=st.columns(3)
        for panel,phase,label in zip(panels,['dominado','aprendendo','alerta'],['Dominados','Aprendendo','Em alerta']):
            panel.button(f'{label} · {counts[phase]}',key='focus_'+phase,on_click=_set_focus,args=(label,),width='stretch')
    with st.expander('O que significa cada grupo?'):
        st.caption('Dominados: acerto com convicção, amostra suficiente e revisão em dia. Aprendendo: desenvolvimento ou medição pendente. Em alerta: sem estudo registrado, baixo rendimento ou revisão vencida.')
    has_snapshot=any(t.get('planner_safety') for t in view['states'])
    cumulative=has_snapshot and st.radio('Histórico ou resultados registrados?',['Histórico da Osler','Blocos registrados no app'],horizontal=True,key='statistics_source')=='Histórico da Osler'
    if cumulative:
        period='Todo o período'; reference=today_local().isoformat()
        st.caption('Questões realizadas são questões distintas já vistas. Convicção é a segurança acumulada da Osler, incluindo recuperações nas revisões. Dados do último arquivo importado; não são questões feitas hoje.')
        search=st.text_input('Buscar tema',placeholder='Ex.: trauma, diabetes, pediatria',key='statistics_search')
    else:
        period=st.radio('Ver resultados de',PERIODS,horizontal=True,key='statistics_period')
        date_col,search_col=st.columns([1,2])
        reference=date_col.date_input('Data de referência',value=today_local(),max_value=today_local(),key='statistics_date').isoformat()
        search=search_col.text_input('Buscar tema',placeholder='Ex.: trauma, diabetes, pediatria',key='statistics_search')
    area_col,focus_col,mode_col=st.columns([1,1.3,1])
    specific_states=[t for t in view['states'] if not t.get('historical_aggregate')]
    all_rows=topic_statistics(specific_states,view['sessions'],period,reference)
    aggregate_paths={tuple(normalize_path(t['path'])) for t in view['states'] if t.get('historical_aggregate')}
    all_rows=[r for r in all_rows if tuple(normalize_path(r['Caminho'].split(' → '))) not in aggregate_paths]
    areas=sorted({r['Área'] for r in all_rows})
    area=area_col.selectbox('Área',['Todas',*areas],key='statistics_area')
    focus=focus_col.selectbox('Mostrar',['Todos os temas','Dominados','Aprendendo','Em alerta','Sem estudo registrado','Erros abaixo de 60%','Com questões no período'],key='statistics_focus')
    mode='Todas' if cumulative else mode_col.selectbox('Questões',list(MODES),key='statistics_mode')
    rows=topic_statistics(specific_states,view['sessions'],period,reference,mode)
    rows=[r for r in rows if tuple(normalize_path(r['Caminho'].split(' → '))) not in aggregate_paths]
    if search:
        query=normalize_path([search])[0]
        rows=[r for r in rows if query in normalize_path([r['Caminho']])[0]]
    if area!='Todas': rows=[r for r in rows if r['Área']==area]
    if focus=='Em alerta': rows=[r for r in rows if r['Estado']=='Em alerta']
    elif focus=='Dominados': rows=[r for r in rows if r['Estado']=='Dominado']
    elif focus=='Aprendendo': rows=[r for r in rows if r['Estado']=='Aprendendo']
    elif focus=='Sem estudo registrado':
        rows=[r for r in rows if r['Situação']=='Sem estudo registrado']
        rows.sort(key=lambda r:-(r['Incidência relativa (%)'] or 0))
    elif focus=='Erros abaixo de 60%':
        by_id={t['topic_id']:t for t in view['states']}
        rows=[r for r in rows if by_id.get(r['topic_id'],{}).get('low_accuracy')]
    elif focus=='Com questões no período': rows=[r for r in rows if r['Questões']>0]
    n=sum(r['Questões com acertos exatos'] for r in rows)
    correct=sum(r['Acertos'] for r in rows)
    a,b,c=st.columns(3)
    if cumulative:
        a.metric('Temas com histórico Osler',sum(r['Retrato Osler'] is not None for r in rows))
        b.metric('Temas em alerta',sum(r['Estado']=='Em alerta' for r in rows))
        c.metric('Início do cronograma','/'.join(reversed(view['profile']['start_date'].split('-'))) if view['profile'].get('start_date') else 'Não definido')
    else:
        a.metric('Questões no período',sum(r['Questões'] for r in rows))
        b.metric('Acerto no período',f'{100*correct/n:.1f}%' if n else 'Sem registro exato')
        c.metric('Temas praticados',sum(r['Questões']>0 for r in rows))
    start,end=period_bounds(period,reference)
    def label(day): return '/'.join(reversed(day.split('-')))
    st.caption(f"{len(rows)} temas nos filtros · histórico importado mais recente por tema." if cumulative else f"{label(start) if start else 'Todo o histórico'} até {label(end)} · {len(rows)} temas nos filtros. Semana começa na segunda; mês segue o calendário.")
    detail=st.checkbox('Exibir mais estatísticas',key='statistics_detail')
    fields=['Tema','Estado','Questões realizadas','Convicção (%)','Último contato','Próxima revisão','Prioridade','Fonte do histórico'] if cumulative else ['Tema','Área','Estado','Questões','Acerto (%)','Com convicção (%)','Próxima revisão']
    has_planner=any(r.get('Retrato Osler') for r in rows)
    if has_planner and not cumulative:
        fields.insert(-1,'Segurança acumulada Osler (%)')
        st.caption('Segurança acumulada Osler inclui acertos recuperados em revisões. É um retrato datado, separado dos resultados do período e do acerto em questões novas.')
    if detail: fields+=['Meta do tema (%)','Lotes consolidados (%)','Questões com convicção informada','Prioridade','Último contato','Incidência relativa (%)','Respondidas no PDF','Acerto no PDF','Situação','Novas','Repetidas','Mistas','Questões com acertos exatos','Questões aproximadas','Acerto aproximado (%)','Caminho']
    if detail and has_planner: fields+=['Questões distintas Osler','Retrato Osler','Pendências no retrato Osler']
    fields=list(dict.fromkeys(fields))
    frame=pd.DataFrame(rows,columns=['topic_id',*fields])
    displayed=frame[fields]
    signature=hashlib.sha256(json.dumps([cumulative,period,reference,mode,[r['topic_id'] for r in rows]]).encode()).hexdigest()[:16]
    layout=st.radio('Como visualizar?',['Tabela','Lista'],horizontal=True,key='statistics_layout')
    selected=None
    if layout=='Lista': _topic_list(rows,signature,go_record,cumulative)
    else:
        st.caption('Selecione uma linha para agir no tema. Deslize a tabela para ver mais colunas ou escolha Lista.')
        selected=st.dataframe(displayed,hide_index=True,width='stretch',height=510,key='study_topics_table_'+signature,on_select='rerun',selection_mode='single-row',
                          column_config={'Acerto (%)':st.column_config.NumberColumn(format='%.1f%%'),
                                         'Incidência relativa (%)':st.column_config.NumberColumn(format='%.2f%%'),
                                         'Acerto aproximado (%)':st.column_config.NumberColumn(format='%.1f%%')})
    with st.expander('Entender os números'):
        st.caption('Nesta visão, convicção é o percentual de questões distintas já acertadas com segurança na Osler, incluindo revisões. Para temas sem retrato, o total do PDF aparece com sua fonte e a convicção fica desconhecida. O retrato não é somado aos blocos registrados.' if cumulative else 'Acerto e convicção medem tentativas do período. Lotes consolidados acompanha os lotes iniciados no período e incorpora revisões vinculadas sem aumentar seu denominador. São contagens de lotes, não IDs individuais de questões. Contexto de prioridade, contato, incidência e PDF é atual.')
    if selected is not None and selected.selection.rows and selected.selection.rows[0]<len(rows):
        chosen=rows[selected.selection.rows[0]]
        st.write('**'+chosen['Caminho']+'**')
        left,right=st.columns(2)
        left.button('Registrar resultado deste tema',on_click=go_record,args=(chosen['topic_id'],10),disabled=not chosen['catalog_available'])
        right.button('Adiantar este tema hoje',on_click=_open_extra,args=(chosen['topic_id'],),disabled=not chosen['catalog_available'])
        if not chosen['catalog_available']: st.caption('Histórico preservado. Para planejar novos blocos deste tema, importe um relatório que o contenha.')
    safe=displayed.map(lambda value:_safe_cell(value) if isinstance(value,str) else value)
    st.download_button('Baixar tabela filtrada',safe.to_csv(index=False,sep=';').encode('utf-8-sig'),'temas_'+reference+'.csv','text/csv')
    render_trajectories(service,view)
    aggregates=[t for t in view['states'] if t.get('historical_aggregate')]
    if aggregates:
        with st.expander('Histórico antigo sem tema específico'):
            st.caption('Resultados agregados preservados. Não foram atribuídos aos subtemas e não geram blocos amplos no planejamento.')
            st.dataframe(pd.DataFrame([{'Registro agregado':' → '.join(t['path']),'Tentativas registradas':t['recorded_attempts']} for t in aggregates]),hide_index=True,width='stretch')
    with st.expander('Estatística e evolução em detalhe'):
        st.caption('Amostras pequenas exigem cautela. PDFs não informam primeira/última tentativa e sua data não representa último contato. As estimativas por tema usam modalidades separadas; esta tabela mostra totais descritivos segundo seu filtro.')
        measured=[]
        for t in view['states']:
            p=t['performance']
            if not p['reported_n']: continue
            interval=p['interval']
            measured.append({'Tema':' → '.join(t['path']),'Base':t['performance_source'],'Amostra exata':p['exact_n'],
                             'Média estimada (%)':round(p['mean']*100,1),
                             'Faixa Wilson 95%':f'{interval[0]*100:.1f} a {interval[1]*100:.1f}%' if interval else 'Sem contagem exata'})
        st.dataframe(pd.DataFrame(measured),hide_index=True,width='stretch')
        st.caption('Esta análise usa a janela recente do planejador, separada do filtro de totais acima. Beta(1,1) é o prior explícito; Wilson é um intervalo frequentista distinto. Não são probabilidades de aprovação.')
