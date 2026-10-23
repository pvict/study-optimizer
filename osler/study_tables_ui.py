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
from .confidence_presentation import confidence_presentation


def _open_extra(topic_id):
    st.session_state['adaptive_view']='Meu dia'
    st.session_state['extra_topic']=topic_id


def _set_focus(focus):
    st.session_state['statistics_focus']=focus


def _clear_filters():
    for key in ['statistics_search','statistics_area','statistics_focus','statistics_mode','statistics_detail']:
        st.session_state.pop(key,None)


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
            confidence=f"{row['Convicção principal (%)']:.1f}%" if row['Convicção principal (%)'] is not None else 'Não informada'
            due=row['Próxima revisão'] or 'Não programada'
            if cumulative:
                st.write(f"{row['Questões']} respostas no app · Acerto: {accuracy}")
                st.write('Convicção: '+confidence)
                st.caption((str(row['Questões realizadas']) if row['Questões realizadas'] is not None else 'Sem contagem')+' questões no histórico importado · '+row['Fonte do histórico'])
            else:
                st.html('<div class="study-list-summary"><span>'+escape(row['Estado'])+'</span><span><strong>'+str(row['Questões'])+
                        '</strong> questões no período</span><span>Acerto: <strong>'+escape(accuracy)+
                        '</strong></span><span>Convicção: '+escape(confidence)+'</span></div>')
            st.caption(row['Base da convicção'])
            action=row.get('Próxima ação')
            st.caption('Próxima ação: '+action if action in {'Priorizar agora','Distribuição gradual'} else 'Próxima revisão: '+due)
            if cumulative and row.get('Domínio / evidência'): st.caption(row['Domínio / evidência'])
            if row.get('Meta do tema (%)') is not None: st.caption(f"Meta do tema: {row['Meta do tema (%)']:g}% · acerto com convicção em questões novas e amostra suficiente.")
            left,right=st.columns(2)
            left.button('Registrar resultado',key='list_record_'+row['topic_id'],on_click=go_record,args=(row['topic_id'],10),disabled=not row['catalog_available'],width='stretch')
            right.button('Adiantar hoje',key='list_extra_'+row['topic_id'],on_click=_open_extra,args=(row['topic_id'],),disabled=not row['catalog_available'],width='stretch')
            if not row['catalog_available']: st.caption('Histórico preservado. Importe um relatório deste tema para planejar novos blocos.')


def render_topic_table(service,go_record):
    view=service.overview(today_local().isoformat())
    counts={phase:sum(t.get('learning_state')==phase and t['status']!='sem_registro' for t in view['planning_states']) for phase in ['dominado','aprendendo','alerta']}
    st.caption('Situação atual dos temas · selecione um grupo para filtrar')
    with st.container(key='topic_states'):
        panels=st.columns(4)
        for panel,phase,label in zip(panels[:3],['dominado','aprendendo','alerta'],['Dominados','Aprendendo','Em alerta']):
            panel.button(f'{label} · {counts[phase]}',key='focus_'+phase,on_click=_set_focus,args=(label,),width='stretch',type='primary' if st.session_state.get('statistics_focus')==label else 'secondary')
        panels[3].button('Não vistos · '+str(sum(t['status']=='sem_registro' for t in view['planning_states'])),key='focus_unseen',on_click=_set_focus,args=('Sem estudo registrado',),width='stretch',type='primary' if st.session_state.get('statistics_focus')=='Sem estudo registrado' else 'secondary')
    with st.container(key='topic_filters'):
        search_col,focus_col=st.columns([2,1])
        search=search_col.text_input('Buscar tema',placeholder='Ex.: trauma, diabetes, pediatria',key='statistics_search')
        focus=focus_col.selectbox('Mostrar',['Todos os temas','Priorizar agora','Segurança alta na Osler','Dominados','Aprendendo','Em alerta','Sem estudo registrado','Erros abaixo de 60%','Com questões no período'],key='statistics_focus')
    has_snapshot=any(t.get('planner_safety') for t in view['states'])
    cumulative=has_snapshot and st.radio('Histórico ou resultados registrados?',['Histórico da Osler','Blocos registrados no app'],horizontal=True,key='statistics_source')=='Histórico da Osler'
    if cumulative:
        period='Todo o período'; reference=today_local().isoformat()
        st.caption('Uma convicção principal, com fonte e base identificadas. Questões no app e no histórico permanecem separadas; as duas medições originais ficam nos detalhes.')
    else:
        period=st.radio('Ver resultados de',PERIODS,horizontal=True,key='statistics_period')
    more_filters=st.expander('Mais filtros e definições')
    if not cumulative:
        reference=more_filters.date_input('Data de referência',value=today_local(),max_value=today_local(),key='statistics_date',format='DD/MM/YYYY').isoformat()
    specific_states=[t for t in view['states'] if not t.get('historical_aggregate')]
    all_rows=topic_statistics(specific_states,view['sessions'],period,reference)
    aggregate_paths={tuple(normalize_path(t['path'])) for t in view['states'] if t.get('historical_aggregate')}
    all_rows=[r for r in all_rows if tuple(normalize_path(r['Caminho'].split(' → '))) not in aggregate_paths]
    areas=sorted({r['Área'] for r in all_rows})
    area=more_filters.selectbox('Área',['Todas',*areas],key='statistics_area')
    mode='Todas' if cumulative else more_filters.selectbox('Questões',list(MODES),key='statistics_mode')
    detail=more_filters.checkbox('Exibir mais estatísticas',key='statistics_detail')
    more_filters.caption('Estado atual: Dominados têm convicção em blocos, amostra suficiente e revisão em dia; Aprendendo inclui medição pendente; Em alerta inclui baixo rendimento ou revisão vencida. Não vistos entram por incidência. O período filtra os resultados, sem redefinir o estado atual.')
    rows=topic_statistics(specific_states,view['sessions'],period,reference,mode)
    rows=[r for r in rows if tuple(normalize_path(r['Caminho'].split(' → '))) not in aggregate_paths]
    if search:
        query=normalize_path([search])[0]
        rows=[r for r in rows if query in normalize_path([r['Caminho']])[0]]
    if area!='Todas': rows=[r for r in rows if r['Área']==area]
    if focus=='Em alerta': rows=[r for r in rows if r['Estado']=='Em alerta']
    elif focus=='Priorizar agora': rows=[r for r in rows if r['Prioridade'] in {'Alta','Urgente'}]
    elif focus=='Segurança alta na Osler': rows=[r for r in rows if r['Domínio / evidência']=='Segurança alta na Osler']
    elif focus=='Dominados': rows=[r for r in rows if r['Estado']=='Dominado']
    elif focus=='Aprendendo': rows=[r for r in rows if r['Estado']=='Aprendendo']
    elif focus=='Sem estudo registrado':
        rows=[r for r in rows if r['Situação']=='Sem estudo registrado']
        rows.sort(key=lambda r:-(r['Incidência relativa (%)'] or 0))
    elif focus=='Erros abaixo de 60%':
        by_id={t['topic_id']:t for t in view['states']}
        rows=[r for r in rows if by_id.get(r['topic_id'],{}).get('low_accuracy')]
    elif focus=='Com questões no período': rows=[r for r in rows if r['Questões']>0]
    rows=confidence_presentation(rows,view['sessions'],period,reference,mode,include_snapshot=cumulative)
    n=sum(r['Questões com acertos exatos'] for r in rows)
    correct=sum(r['Acertos'] for r in rows)
    with st.container(key='topic_summary'):
        a,b,c=st.columns(3)
    if cumulative:
        a.metric('Questões no app',sum(r['Questões'] for r in rows))
        b.metric('Acerto no app',f'{100*correct/n:.1f}%' if n else '—')
        c.metric('Temas com histórico Osler',sum(r['Retrato Osler'] is not None for r in rows))
    else:
        a.metric('Questões no período',sum(r['Questões'] for r in rows))
        b.metric('Acerto no período',f'{100*correct/n:.1f}%' if n else '—')
        c.metric('Temas praticados',sum(r['Questões']>0 for r in rows))
        if not n: st.caption('Acerto no período: ainda não há registro com quantidade exata de acertos nesses filtros.')
    start,end=period_bounds(period,reference)
    def label(day): return '/'.join(reversed(day.split('-')))
    st.caption(f"{len(rows)} temas nos filtros · histórico importado mais recente por tema." if cumulative else f"{label(start) if start else 'Todo o histórico'} até {label(end)} · {len(rows)} temas nos filtros. Semana começa na segunda; mês segue o calendário.")
    st.button('Limpar filtros',key='statistics_clear',on_click=_clear_filters,disabled=not(search or area!='Todas' or focus!='Todos os temas' or mode!='Todas' or detail))
    fields=['Tema','Estado','Questões','Acerto (%)','Convicção principal (%)','Base da convicção','Questões realizadas','Domínio / evidência','Último contato','Prioridade','Próxima ação','Fonte do histórico'] if cumulative else ['Tema','Área','Estado','Questões','Acerto (%)','Convicção principal (%)','Base da convicção','Próxima revisão']
    has_planner=any(r.get('Retrato Osler') for r in rows)
    if detail: fields+=['Meta do tema (%)','Lotes consolidados (%)','Questões com convicção informada','Prioridade','Último contato','Incidência relativa (%)','Respondidas no PDF','Acerto no PDF','Situação','Novas','Repetidas','Mistas','Questões com acertos exatos','Questões aproximadas','Acerto aproximado (%)','Caminho']
    if detail and has_planner: fields+=['Questões distintas Osler','Retrato Osler','Pendências no retrato Osler','Posição na fila inicial']
    fields=list(dict.fromkeys(fields))
    frame=pd.DataFrame(rows,columns=['topic_id',*fields])
    displayed=frame[fields].rename(columns={'Convicção principal (%)':'Convicção (%)'})
    if cumulative:
        displayed=displayed.rename(columns={'Questões':'Questões no app','Acerto (%)':'Acerto no app (%)',
            'Questões realizadas':'Questões no histórico'})
    signature=hashlib.sha256(json.dumps([cumulative,period,reference,mode,[r['topic_id'] for r in rows]]).encode()).hexdigest()[:16]
    layout=st.radio('Como visualizar?',['Tabela','Lista'],horizontal=True,key='statistics_layout')
    selected=None
    if layout=='Lista': _topic_list(rows,signature,go_record,cumulative)
    else:
        st.caption('Selecione uma linha para agir no tema. Deslize a tabela para ver mais colunas ou escolha Lista.')
        selected=st.dataframe(displayed,hide_index=True,width='stretch',height=510,key='study_topics_table_'+signature,on_select='rerun',selection_mode='single-row',
                          column_config={'Acerto (%)':st.column_config.NumberColumn(format='%.1f%%'),
                                         'Acerto no app (%)':st.column_config.NumberColumn(format='%.1f%%'),
                                         'Convicção (%)':st.column_config.NumberColumn(format='%.1f%%',help='Uma medição identificada na coluna Base da convicção. Fontes não são somadas nem ponderadas entre si. Zero informado é preservado.'),
                                         'Incidência relativa (%)':st.column_config.NumberColumn(format='%.2f%%'),
                                         'Acerto aproximado (%)':st.column_config.NumberColumn(format='%.1f%%')})
    with st.expander('Ver fontes e medições originais'):
        st.caption('A convicção principal mostra uma medição existente. Na visão de histórico, usamos a fonte com a data mais recente; em empate de dia, mostramos o app sem presumir a ordem das horas. Nos blocos por período, usamos apenas os registros filtrados. Nenhuma média entre fontes é calculada.')
        st.dataframe(pd.DataFrame([{'Tema':r['Tema'],'Caminho':r['Caminho'],
            'Convicção no app (%)':r['Com convicção (%)'],'Tentativas com convicção informada':r['Questões com convicção informada'],
            'Convicção na Osler (%)':r['Convicção (%)'],'Questões distintas Osler':r['Questões distintas Osler'],
            'Data do retrato Osler':r['Retrato Osler'],'Base exibida':r['Base da convicção']} for r in rows]),hide_index=True,width='stretch')
        st.caption('No app: tentativas e rendimento dos blocos registrados em todo o período. No histórico: questões distintas e segurança acumulada no retrato da Osler, incluindo recuperações. Para temas sem retrato, mostramos o PDF com sua fonte e convicção desconhecida. Não somamos essas bases: podem se sobrepor. Prioridade e último contato usam os registros atuais.' if cumulative else 'Acerto e convicção medem tentativas do período. Lotes consolidados acompanha os lotes iniciados no período e incorpora revisões vinculadas sem aumentar seu denominador. São contagens de lotes, não IDs individuais de questões. Contexto de prioridade, contato, incidência e PDF é atual.')
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
