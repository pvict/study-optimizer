"""Tabela de temas e resultados com filtros de calendário e ações no contexto."""
from .ui_help import explain
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
from .topic_contacts import forecast_topic_contacts,apply_next_contacts
from .bento import area_slug,eyebrow,chip,bar
from .study_errors import ErrorStore


def _open_extra(topic_id):
    st.session_state['adaptive_view']='Meu dia'
    st.session_state['extra_topic']=topic_id


def _set_focus(focus):
    st.session_state['statistics_focus']=focus


def _select_area():
    st.session_state['statistics_area']=st.session_state.get('statistics_area_pills') or 'Todas'


def _open_errors(path):
    st.session_state['topics_tabs']='Erros abertos'
    st.session_state['study_errors_topic']=tuple(normalize_path(path))
    st.session_state.pop('study_errors_cause',None)
    st.session_state['study_errors_page']=1


def _clear_filters():
    for key in ['statistics_search','statistics_area','statistics_area_pills','statistics_focus','statistics_mode','statistics_detail']:
        st.session_state.pop(key,None)


def _topic_card_rows(rows,states,sessions,period,reference,mode='Todas'):
    """Seleciona uma base exata existente para o card; a tabela original não muda."""
    card_mode='Novas' if mode=='Todas' else mode
    measured={r['topic_id']:r for r in topic_statistics(states,sessions,period,reference,card_mode)}
    return [{**row,'card_accuracy':measured.get(row['topic_id'],{}).get('Acerto (%)'),
             'card_exact_n':measured.get(row['topic_id'],{}).get('Questões com acertos exatos',0),
             'card_accuracy_label':'Acerto em '+card_mode.lower()} for row in rows]


def _topic_list(rows,signature,go_record,cumulative=False,objective_goal=False,*,open_error_paths=()):
    if not rows:
        st.info('Nenhum tema nesses filtros. Tente outra busca ou escolha Todos os temas.')
        return
    pages=(len(rows)+11)//12
    page=int(st.number_input('Página de temas',1,pages,1,key='statistics_list_page_'+signature)) if pages>1 else 1
    st.caption(f'{len(rows)} temas · página {page} de {pages}')
    visible=rows[(page-1)*12:page*12]
    with st.container(key='bento_topics_grid'):
        for start in range(0,len(visible),2):
            columns=st.columns(2,gap='medium')
            for column,row in zip(columns,visible[start:start+2]):
                path=row['Caminho'].split(' → ');slug=area_slug(path)
                value=row.get('card_accuracy',row['Acerto (%)'])
                exact_n=row.get('card_exact_n',row['Questões com acertos exatos'])
                accuracy=f'{value:.1f}%' if value is not None else '—'
                accuracy_label=row.get('card_accuracy_label','Acerto no recorte')
                confidence=f"{row['Convicção principal (%)']:.1f}%" if row['Convicção principal (%)'] is not None else '—'
                due=row['Próxima revisão'] or 'Não programada'
                target=row.get('Meta do tema (%)')
                with column,st.container(key='bento-topic-'+row['topic_id']):
                    st.html('<div class="o-topic-meta">'+eyebrow(row['Área'],slug)+chip(row['Estado'],{'Dominado':'dominado','Aprendendo':'aprendendo','Em alerta':'alerta','Não visto':'sem_registro'}.get(row['Estado']))+'</div>'+
                            '<h3>'+escape(row['Tema'])+'</h3><p class="o-topic-path">'+escape(row['Caminho'])+'</p>'+
                            '<div class="o-topic-results"><p>'+escape(accuracy_label)+' <strong>'+accuracy+'</strong> <span>(n='+str(exact_n)+')</span></p>'+
                            '<p>Convicção <strong>'+confidence+'</strong></p></div>')
                    st.html(bar(value/100 if value is not None else None,slug,target/100 if target is not None else None,
                                accuracy_label+': '+accuracy+f' (n={exact_n})'+(f' · meta {target:g}%' if target is not None else '')))
                    if value is None: st.caption('Sem acertos exatos registrados nesta base. O traço indica ausência de medição.')
                    st.caption(str(row['Questões'])+(' questões no app' if cumulative else ' questões no período')+(f' · meta do tema {target:g}%' if target is not None else ' · meta do tema não informada'))
                    st.caption(row['Base da convicção'])
                    action=row.get('Próxima ação')
                    if action in {'Priorizar agora','Distribuição gradual'}: st.caption('Próxima ação: '+action)
                    if 'Revisão devida' in row or action not in {'Priorizar agora','Distribuição gradual'}:
                        st.caption('Próxima revisão: '+due+(' · '+row['Tipo do próximo bloco'] if row.get('Tipo do próximo bloco') else ''))
                    st.button('Registrar resultado',key='list_record_'+row['topic_id'],on_click=go_record,args=(row['topic_id'],10),disabled=not row['catalog_available'],width='stretch')
                    with st.expander('Detalhes e outras ações'):
                        overall=f"{row['Acerto (%)']:.1f}%" if row['Acerto (%)'] is not None else '—'
                        st.write(f"{row['Questões']} respostas no app · Acerto: {overall} (n={row['Questões com acertos exatos']})")
                        if cumulative:
                            st.caption((str(row['Questões realizadas']) if row['Questões realizadas'] is not None else 'Sem contagem')+' questões no histórico importado · '+row['Fonte do histórico'])
                            if row.get('Domínio / evidência'): st.caption(row['Domínio / evidência'])
                        st.caption(f"Novas: {row['Novas']} · Repetidas: {row['Repetidas']} · Mistas: {row['Mistas']}. Bases separadas.")
                        st.caption(f"Questões aproximadas: {row['Questões aproximadas']}. Não entram na amostra exata de acerto.")
                        if row.get('Revisão devida'): st.caption('Vencimento original: '+row['Revisão devida'])
                        if target is not None: st.caption(f'Meta do tema: {target:g}% · '+('acerto em questões novas e amostra suficiente; convicção complementar.' if objective_goal else 'acerto com convicção em questões novas e amostra suficiente.'))
                        st.button('Adiantar hoje',key='list_extra_'+row['topic_id'],on_click=_open_extra,args=(row['topic_id'],),disabled=not row['catalog_available'],width='stretch')
                        if tuple(normalize_path(path)) in open_error_paths:
                            st.button('Ver erros',key='list_errors_'+row['topic_id'],on_click=_open_errors,args=(path,),width='stretch')
                    if not row['catalog_available']: st.caption('Histórico preservado. Importe um relatório deste tema para planejar novos blocos.')


def render_topic_table(service,go_record):
    view=service.overview(today_local().isoformat())
    specific_states=[t for t in view['states'] if not t.get('historical_aggregate')]
    counts={phase:sum(t.get('learning_state')==phase and t['status']!='sem_registro' for t in specific_states) for phase in ['dominado','aprendendo','alerta']}
    with st.container(key='bento-topics-filters'):
        explain('Situação atual dos temas · selecione um grupo para filtrar')
        with st.container(key='topic_states'):
            panels=st.columns(4)
            for panel,phase,label,icon in zip(panels[:3],['dominado','aprendendo','alerta'],['Dominados','Aprendendo','Em alerta'],['check_circle','trending_up','priority_high']):
                panel.button(f'{label} · {counts[phase]}',key='focus_'+phase,on_click=_set_focus,args=(label,),icon=':material/'+icon+':',width='stretch',type='primary' if st.session_state.get('statistics_focus')==label else 'secondary')
            panels[3].button('Não vistos · '+str(sum(t['status']=='sem_registro' for t in specific_states)),key='focus_unseen',on_click=_set_focus,args=('Sem estudo registrado',),icon=':material/radio_button_unchecked:',width='stretch',type='primary' if st.session_state.get('statistics_focus')=='Sem estudo registrado' else 'secondary')
        with st.container(key='topic_filters'):
            search_col,focus_col=st.columns([2,1])
            search=search_col.text_input('Buscar tema',placeholder='Ex.: trauma, diabetes, pediatria',key='statistics_search')
            focus=focus_col.selectbox('Mostrar',['Todos os temas','Priorizar agora','Segurança alta na Osler','Dominados','Aprendendo','Em alerta','Sem estudo registrado','Erros abaixo de 60%','Com questões no período'],key='statistics_focus')
        has_snapshot=any(t.get('planner_safety') for t in view['states'])
        source_column,layout_column=st.columns([2,1])
        cumulative=has_snapshot and source_column.radio('Histórico ou resultados registrados?',['Histórico da Osler','Blocos registrados no app'],horizontal=True,key='statistics_source',label_visibility='collapsed')=='Histórico da Osler'
        layout=layout_column.radio('Como visualizar?',['Tabela','Lista'],horizontal=True,key='statistics_layout',label_visibility='collapsed')
        if cumulative:
            period='Todo o período'; reference=today_local().isoformat()
            explain('Uma convicção principal, com fonte e base identificadas. Questões no app e no histórico permanecem separadas; as duas medições originais ficam nos detalhes.')
        else:
            period=st.radio('Ver resultados de',PERIODS,horizontal=True,key='statistics_period')
        more_filters=st.expander('Mais filtros e definições')
        if not cumulative:
            reference=more_filters.date_input('Data de referência',value=today_local(),max_value=today_local(),key='statistics_date',format='DD/MM/YYYY').isoformat()
        all_rows=topic_statistics(specific_states,view['sessions'],period,reference)
        aggregate_paths={tuple(normalize_path(t['path'])) for t in view['states'] if t.get('historical_aggregate')}
        all_rows=[r for r in all_rows if tuple(normalize_path(r['Caminho'].split(' → '))) not in aggregate_paths]
        areas=sorted({r['Área'] for r in all_rows})
        area=more_filters.selectbox('Área',['Todas',*areas],key='statistics_area')
        area_counts={name:sum(r['Área']==name for r in all_rows) for name in areas}
        st.session_state['statistics_area_pills']=area
        st.pills('Filtrar por área',['Todas',*areas],key='statistics_area_pills',on_change=_select_area,
                 format_func=lambda name: name+' · '+str(len(all_rows) if name=='Todas' else area_counts[name]))
        mode='Todas' if cumulative else more_filters.selectbox('Questões',list(MODES),key='statistics_mode')
        detail=more_filters.checkbox('Exibir mais estatísticas',key='statistics_detail')
        more_filters.caption(('Estado atual: na estratégia equilibrada, Dominados exigem acerto na meta, amostra suficiente, encontros espaçados e revisão em dia; convicção é complementar. ' if view['profile'].get('review_strategy')=='balanced_v2' else 'Estado atual: Dominados têm convicção em blocos, amostra suficiente e revisão em dia; ')+ 'Aprendendo inclui medição pendente; Em alerta inclui baixo rendimento ou revisão vencida. Não vistos entram por incidência. O período filtra os resultados, sem redefinir o estado atual.')
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
    if view['planning_token']!=service.agenda.token():
        st.info('O plano mudou durante a consulta. Atualize a tabela para ver as próximas revisões.')
        st.button('Atualizar tabela',on_click=st.rerun)
        return
    contact_key=[str(service.repository.root),view['date'],view['planning_token']]
    cached=st.session_state.get('statistics_next_contacts',{})
    if cached.get('key')!=contact_key:
        with st.spinner('Consultando as próximas revisões no calendário...'):
            try: cached={'key':contact_key,'forecast':forecast_topic_contacts(service,view)}
            except ValueError as exc:
                st.info(str(exc))
                st.button('Atualizar tabela',on_click=st.rerun)
                return
        st.session_state['statistics_next_contacts']=cached
    rows=apply_next_contacts(rows,cached['forecast'])
    coverage=cached['forecast'].get('coverage')
    if coverage:
        st.caption(f"{len(specific_states)} subtemas · {coverage['scheduled']} de {coverage['total']} blocos de agenda com data")
        if coverage['scheduled']<coverage['total']:
            st.warning('Há temas sem encaixe com a carga, os dias de descanso e a divisão atuais. A cobertura completa exige reorganizar esses limites; não foi criada uma data fictícia.')
    n=sum(r['Questões com acertos exatos'] for r in rows)
    correct=sum(r['Acertos'] for r in rows)
    with st.expander('Resumo dos resultados'),st.container(key='topic_summary'):
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
    explain(f'Base do acerto: {n} tentativas com contagem exata de acertos no recorte. Fontes importadas permanecem separadas.')
    start,end=period_bounds(period,reference)
    def label(day): return '/'.join(reversed(day.split('-')))
    st.caption(f"{len(rows)} temas nos filtros · histórico importado mais recente por tema." if cumulative else f"{label(start) if start else 'Todo o histórico'} até {label(end)} · {len(rows)} temas nos filtros. Semana começa na segunda; mês segue o calendário.")
    st.button('Limpar filtros',key='statistics_clear',on_click=_clear_filters,disabled=not(search or area!='Todas' or focus!='Todos os temas' or mode!='Todas' or detail))
    fields=['Tema','Estado','Próxima revisão','Questões','Acerto (%)','Convicção principal (%)','Base da convicção','Questões realizadas','Domínio / evidência','Último contato','Prioridade','Próxima ação','Fonte do histórico'] if cumulative else ['Tema','Estado','Próxima revisão','Área','Questões','Acerto (%)','Convicção principal (%)','Base da convicção']
    explain('Próxima revisão: vaga prevista no calendário atual, até '+cached['forecast']['end']+'. Para temas não vistos, é o primeiro contato. As datas serão recalculadas com seus resultados; o vencimento original fica nos detalhes.')
    has_planner=any(r.get('Retrato Osler') for r in rows)
    if detail: fields+=['Tipo do próximo bloco','Revisão devida','Meta do tema (%)','Lotes consolidados (%)','Questões com convicção informada','Prioridade','Último contato','Incidência relativa (%)','Respondidas no PDF','Acerto no PDF','Situação','Novas','Repetidas','Mistas','Questões com acertos exatos','Questões aproximadas','Acerto aproximado (%)','Caminho']
    if detail and has_planner: fields+=['Questões distintas Osler','Retrato Osler','Pendências no retrato Osler','Posição na fila inicial']
    fields=list(dict.fromkeys(fields))
    frame=pd.DataFrame(rows,columns=['topic_id',*fields])
    displayed=frame[fields].rename(columns={'Convicção principal (%)':'Convicção (%)'})
    if cumulative:
        displayed=displayed.rename(columns={'Questões':'Questões no app','Acerto (%)':'Acerto no app (%)',
            'Questões realizadas':'Questões no histórico'})
    signature=hashlib.sha256(json.dumps([cumulative,period,reference,mode,[r['topic_id'] for r in rows]]).encode()).hexdigest()[:16]
    selected=None
    if layout=='Lista':
        cards=_topic_card_rows(rows,specific_states,view['sessions'],period,reference,mode)
        open_paths={tuple(normalize_path(e['path'])) for e in ErrorStore(service.repository).active(today_local().isoformat())}
        _topic_list(cards,signature,go_record,cumulative,view['profile'].get('review_strategy')=='balanced_v2',open_error_paths=open_paths)
    else:
        explain('Selecione uma linha para agir no tema. Deslize a tabela para ver mais colunas ou escolha Lista.')
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
