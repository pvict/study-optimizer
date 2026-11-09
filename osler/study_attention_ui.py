"""Painel nativo de temas que merecem atenção em Hoje."""
from .ui_help import explain
import streamlit as st
from .study_attention import GROUPS,attention_overview,attention_filter,attention_table


def _open_topic(path):
    from .study_tables_ui import _clear_filters
    from .study_navigation_ui import go_view
    _clear_filters()
    st.session_state['statistics_search']=' → '.join(path)
    st.session_state['statistics_area']=path[0]
    st.session_state['statistics_focus']='Todos os temas'
    st.session_state['topics_tabs']='Desempenho dos temas'
    go_view('Plano de questões','Temas e estatísticas')


def render_attention(service,view,day,go_record):
    model=attention_overview(view,service.guide.datasets(),day)
    with st.container(key='bento-attention'):
        if not model['rows']:
            st.caption('Importe um relatório com temas específicos para cruzar incidência, resultados e contatos.')
            return
        counts=model['counts']
        st.write(f"**{counts['Atenção']} temas para olhar** · {model['incident_unpracticed']} incidentes sem prática")
        explain(f"{model['unknown_contact']} temas com último contato desconhecido. Sem prática significa sem questões registradas nesta base.")
        explain('Sugestões de estudo com os dados locais. A ordem segue a política atual do plano; não é previsão de aprovação.')
        explain('Próxima revisão mostra o prazo atual por tema; consultar ou abrir um tema não reserva outro bloco hoje.')
        group=st.segmented_control('Ver temas',GROUPS,default='Atenção',key='attention_group') or 'Atenção'
        if group=='Nunca praticados':explain('Ordem pela importância institucional já calculada no plano; temas com incidência específica vêm primeiro. Sem questões registradas não significa nunca estudado.')
        query=st.text_input('Buscar nos temas de atenção',placeholder='Digite um tema ou parte do caminho',key='attention_search')
        rows=attention_filter(model['rows'],group,query)
        st.caption(f'{len(rows)} de {counts[group]} temas')
        if rows:
            table=attention_table(rows)
            config={'Dias sem contato':st.column_config.NumberColumn(format='%d dias'),
                    'Fonte da incidência':None}
            for column in table[0]:
                if column.startswith('Incidência'):
                    config[column]=st.column_config.NumberColumn(
                        format='%.2f%%' if column.startswith('Incidência (%)') else '%d questões',
                        help='Valor específico do tema. — indica ausência de contagem individual; consulte a fonte nos detalhes do tema.')
            st.dataframe(table,hide_index=True,width='stretch',height=min(260,72+35*len(rows)),
                         column_config=config)
            by_id={r['topic_id']:r for r in rows}
            selected=st.selectbox('Escolha um tema para abrir ou registrar',list(by_id),
                                  format_func=lambda key:' → '.join(by_id[key]['path']),
                                  key='attention_selected_'+group)
            row=by_id[selected]
            explain(row['reason'])
            with st.expander('Fonte da incidência deste tema'):
                st.write(attention_table([row])[0]['Fonte da incidência'])
            left,right=st.columns(2)
            left.button('Abrir tema',key='attention_open',on_click=_open_topic,args=(row['path'],),width='stretch')
            right.button('Registrar resultado',key='attention_record',on_click=go_record,
                         args=(row['topic_id'],row['questions']),width='stretch')
        else:
            st.info('Nenhum tema neste recorte. Limpe a busca ou escolha Todos para consultar os demais.')
        with st.expander('Como ler os dados e a ordem'):
            st.write('Atenção reúne sinais do plano: dificuldade, revisões previstas, afastamento, temas incidentes sem questões registradas e medições ausentes. Sem contato inclui datas desconhecidas, identificadas sem atraso inventado.')
            st.write('Nunca praticados significa sem questões nos registros disponíveis. Um tema pode já ter contato por cartões. Ausência de registro não prova que você nunca estudou o assunto.')
            st.write('Acerto mostra a base selecionada pelo plano e sua modalidade; novas, mistas, repetidas e acumulados permanecem separados. Percentuais informados sem contagens exatas aparecem como aproximados. Convicção acumulada da Osler não mede acerto de primeira tentativa.')
            st.write('Incidência mostra a quantidade de questões do tema na tabela local. Instituições, data e valores de grupos ficam em Fonte da incidência deste tema. Fontes diferentes aparecem em colunas separadas, sem soma; percentuais mantêm sua unidade. Uma linha de grupo não vira incidência individual. Tabelas conjuntas não são separadas por instituição. Ausência não significa zero; data de PDF ou retrato não é data de estudo.')
            st.write('Recuperar de memória e distribuir contatos no tempo têm apoio experimental; estes intervalos e pesos são uma política operacional, sem calibração pessoal. Amostras pequenas e questões repetidas limitam a interpretação. A meta de 90% não é garantia de aprovação.')
            st.markdown('[Prática de recuperação](https://learninglab.psych.purdue.edu/downloads/2007/2007_Karpicke_Roediger_JML.pdf) · [Prática distribuída](https://escholarship.org/uc/item/3rr6q10c) · [Incerteza amostral — NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)')
            st.caption('Os parâmetros do app são uma política de planejamento, não coeficientes científicos calibrados para sua aprovação. Consultar o painel não muda as datas nem registra estudo.')
