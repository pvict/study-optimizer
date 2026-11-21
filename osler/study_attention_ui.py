"""Painel de atenção e lacunas de cobertura."""
import hashlib
from inspect import signature
import json

import streamlit as st

from .study_attention import GROUPS,HIGH_INCIDENCE,attention_overview,attention_filter,attention_table
from .ui_help import explain


TABLE_OPTIONS={'placeholder':'—'} if 'placeholder' in signature(st.dataframe).parameters else {}


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
        st.write(f"**{counts['Atenção']} temas em atenção** · {model['incident_unpracticed']} incidentes sem prática")
        if model['max_gap'] is not None:
            count=model['over_gap_count']
            noun='tema' if count==1 else 'temas'
            summary=f"**{count} {noun} há mais de {model['max_gap']} dias sem contato**"
            share=model['over_gap_share']
            if share is not None:
                summary+=' · '+f'{share:.1%}'.replace('.',',')+' da incidência documentada'
            if model['unknown_contact']:
                summary+=f" · {model['unknown_contact']} sem data de contato"
            st.markdown(summary)
        explain('Sem prática significa sem questões registradas nesta base.')
        explain('Sugestões de estudo com os dados locais. A ordem segue a política atual do plano; não é previsão de aprovação.')
        explain('Próxima revisão mostra o prazo atual por tema; consultar ou abrir um tema não reserva outro bloco hoje.')
        filters,search=st.columns([1,2])
        group=filters.selectbox('Ver temas',GROUPS,key='attention_group')
        if group=='Nunca praticados':explain('Ordem pela importância institucional já calculada no plano; temas com incidência específica vêm primeiro. Sem questões registradas não significa nunca estudado.')
        query=search.text_input('Buscar nos temas de atenção',placeholder='Digite um tema ou parte do caminho',key='attention_search')
        rows=attention_filter(model['rows'],group,query)
        st.caption(f'{len(rows)} de {counts[group]} temas')
        if rows:
            table=attention_table(rows)
            config={'Dias sem contato':st.column_config.NumberColumn(format='%d dias'),
                    'Fonte da incidência':None,'Por que olhar':None}
            for column in table[0]:
                if column.startswith('Incidência'):
                    config[column]=st.column_config.NumberColumn(
                        format='%.2f%%' if column.startswith('Incidência (%)') else '%d questões',
                        help='Valor específico do tema. — indica ausência de contagem individual; consulte a fonte nos detalhes do tema.')
            fingerprint=hashlib.sha256(json.dumps([r['topic_id'] for r in rows]).encode()).hexdigest()[:16]
            selected=st.dataframe(table,hide_index=True,width='stretch',height=min(350,72+35*len(rows)),
                         column_order=['Tema',*[c for c in table[0] if c.startswith('Incidência')],
                                       'Dias sem contato','Próxima revisão','Acerto','Convicção','Último contato','Caminho'],
                         column_config=config,key='attention_table_'+fingerprint,on_select='rerun',selection_mode='single-row',
                         **TABLE_OPTIONS)
            indexes=selected.selection.rows
            index=indexes[0] if indexes else 0 if len(rows)==1 else None
            if index is None:
                st.caption('Selecione uma linha para abrir ou registrar o tema.')
            elif 0<=index<len(rows):
                row=rows[index]
                st.markdown('**'+table[index]['Caminho']+'**')
                left,right=st.columns(2)
                left.button('Abrir tema',key='attention_open',on_click=_open_topic,args=(row['path'],),width='stretch')
                right.button('Registrar resultado',key='attention_record',on_click=go_record,
                             args=(row['topic_id'],row['questions']),width='stretch',type='primary')
                explain(row['reason'])
                with st.expander('Fonte da incidência deste tema'):
                    st.write(table[index]['Fonte da incidência'])
        else:
            st.info('Nenhum tema neste recorte. Limpe a busca ou escolha Todos para consultar os demais.')
        with st.expander('Como ler os dados e a ordem'):
            st.write('Fora do intervalo conta subtemas cujo último contato documentado passou do limite da rotina. A parcela de incidência usa as linhas específicas desses subtemas em relação às linhas de todos os subtemas mapeados, ponderadas pelos pesos das fontes ativas. Temas sem data conhecida ficam fora da contagem de atraso.')
            st.write(f'Pouca prática e alta incidência usa o critério de prática do plano e requer incidência específica, com peso de pelo menos {HIGH_INCIDENCE:.0%} do maior peso entre os temas.')
            st.write('Atenção reúne sinais do plano: dificuldade, revisões previstas, afastamento, temas incidentes sem questões registradas e medições ausentes. Sem contato inclui datas desconhecidas, identificadas sem atraso inventado.')
            st.write('Nunca praticados significa sem questões nos registros disponíveis. Um tema pode já ter contato por cartões. Ausência de registro não prova que você nunca estudou o assunto.')
            st.write('Acerto mostra a base selecionada pelo plano e sua modalidade; novas, mistas, repetidas e acumulados permanecem separados. Percentuais informados sem contagens exatas aparecem como aproximados. Convicção acumulada da Osler não mede acerto de primeira tentativa.')
            st.write('Incidência mostra a quantidade de questões do tema na tabela local. Instituições, data e valores de grupos ficam em Fonte da incidência deste tema. Fontes diferentes aparecem em colunas separadas, sem soma; percentuais mantêm sua unidade. Uma linha de grupo não vira incidência individual. Tabelas conjuntas não são separadas por instituição. Ausência não significa zero; data de PDF ou retrato não é data de estudo.')
            st.write('Recuperar de memória e distribuir contatos no tempo têm apoio experimental; estes intervalos e pesos são uma política operacional, sem calibração pessoal. Amostras pequenas e questões repetidas limitam a interpretação. A meta de 90% não é garantia de aprovação.')
            st.markdown('[Prática de recuperação](https://learninglab.psych.purdue.edu/downloads/2007/2007_Karpicke_Roediger_JML.pdf) · [Prática distribuída](https://escholarship.org/uc/item/3rr6q10c) · [Incerteza amostral (NIST)](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)')
            st.caption('Os parâmetros do app são uma política de planejamento, não coeficientes científicos calibrados para sua aprovação. Consultar o painel não muda as datas nem registra estudo.')
