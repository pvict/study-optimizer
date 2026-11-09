"""Comparação de fronteiras e agenda; detalhes técnicos ficam recolhidos."""
import json
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
from .planner_service import today_local
from .grouping_service import preview_grouping,apply_grouping,history
from .action_feedback import confirm_button,notify_success
from .backups import create_backup

MODES={'osler':'Planner Osler · temas separados','balanced':'Balanceado · grupos recomendados','custom':'Escolher categorias'}


def _preview(service,mode,paths):
    st.session_state.pop('grouping_preview',None)
    with st.status('Comparando calendários até a prova…',expanded=True) as status:
        bar=st.progress(0,text='Preparando os dados…')
        def update(stage,done,total):
            fraction=done/max(1,total)
            value=.05 if stage=='Preparando os dados' else .05+.45*fraction if stage=='Calendário atual' else .5+.5*fraction
            bar.progress(value,text=stage+(f' · {done} de {total} dias' if total>1 else '…'))
        try:
            preview=preview_grouping(service,mode,paths,progress=update)
        except (ValueError,OSError,sqlite3.Error) as exc:
            status.update(label='Não foi possível gerar a prévia',state='error',expanded=True)
            st.error(str(exc));return
        st.session_state['grouping_preview']=preview
        bar.progress(1.,text='Prévia pronta. Confira abaixo antes de aplicar.')
        status.update(label='Comparação concluída — prévia abaixo',state='complete',expanded=True)


def _apply(service,p):
    apply_grouping(service,p)
    st.session_state.pop('grouping_preview',None)
    notify_success(True,'Divisão de revisões atualizada. Backup salvo.')


def render_grouping(service):
    view=service.overview(today_local().isoformat());p=view['profile'];rows=view['grouping_candidates']
    st.write('Modo atual: **'+MODES[p['grouping_mode']]+'**')
    mode=st.segmented_control('Divisão das revisões',list(MODES),format_func=MODES.get,default=p['grouping_mode'],required=True,key='grouping_mode_choice')
    with st.container(border=True):
        st.subheader('Categorias e subtemas')
        search=st.text_input('Buscar categoria',placeholder='Ex.: infecções congênitas',key='grouping_search')
        table=[{'Categoria':' › '.join(r['path']),'Subtemas':len(r['members']),
                **{'Incidência · fonte '+str(d['dataset_id']):d['value'] for d in r['evidence']},
                'Sugestão':'Recomendado' if r['recommended'] else 'Disponível' if r['eligible'] else 'Manter separado',
                'Motivo':r['reason']} for r in rows if search.casefold() in ' '.join(r['path']).casefold()]
        if table:
            formats={'Incidência · fonte '+str(d['dataset_id']):st.column_config.NumberColumn(format='%d questões' if d['unit']=='questoes' else '%.2f%%') for r in rows for d in r['evidence']}
            st.dataframe(pd.DataFrame(table),hide_index=True,width='stretch',column_config=formats)
            st.download_button('Exportar sugestões visíveis',pd.DataFrame(table).to_csv(index=False).encode('utf-8-sig'),
                               'categorias-agrupamentos.csv','text/csv')
        else:st.info('Nenhuma categoria encontrada nesses dados e filtros.')
        eligible={r['topic_id']:r for r in rows if r['eligible']}
        selected=st.multiselect('Categorias para reunir',list(eligible),format_func=lambda i:' › '.join(eligible[i]['path']),
            default=[i for i,r in eligible.items() if r['path'] in p['grouping_paths']],disabled=mode!='custom') if eligible else []
        with st.expander('Composição e incidência por fonte'):
            for r in rows:
                if search.casefold() not in ' '.join(r['path']).casefold():continue
                st.markdown('**'+' › '.join(r['path'])+'**')
                st.write(' · '.join(path[-1] for path in r['member_paths']))
                for d in r['evidence']:
                    st.write(', '.join(d['institutions'])+(': pelo menos ' if d.get('partial') else ': ')+f"{d['value']:g} "+('questões' if d['unit']=='questoes' else '%'))
                    if d['observed_area_share_pct'] is not None:
                        st.write(f"{d['observed_area_share_pct']:.1f}% da incidência informada em {r['path'][0]} ({d['value']:g} de {d['area_total']:g}).")
        if st.button('Comparar calendário',type='primary'):
            _preview(service,mode,[eligible[i]['path'] for i in selected] if mode=='custom' else [])
    preview=st.session_state.get('grouping_preview')
    if preview:
        st.subheader('Prévia da alteração')
        if not preview['changes']:
            st.info('Não há mudanças de calendário nesta comparação. Para reunir os temas, escolha Balanceado ou selecione categorias e compare novamente.')
        st.write(f"{preview['before_units']} → {preview['after_units']} unidades de revisão · {len(preview['changes'])} dias alterados")
        st.info('Projeção condicional até a prova. Um bloco conjunto não comprova domínio de todos os filhos. Agendamentos individuais protegidos ficam separados.')
        comparisons=[]
        def desc(plan):return '; '.join(i['path'][-1]+f" ({i['questions']})" for i in plan['items']) or 'Sem bloco'
        for c in preview['changes']:
            comparisons.append({'Dia':c['date'],'Antes':desc(c['before']),'Depois':desc(c['after']),
                                'Questões antes':c['before']['questions'],'Questões depois':c['after']['questions']})
        st.dataframe(pd.DataFrame(comparisons),hide_index=True,width='stretch')
        with st.expander('Próximo bloco de cada tema · antes e depois'):
            def contacts(calendar):
                result={}
                for day in calendar:
                    for item in day['items']:
                        result.setdefault(' › '.join(item['path']),(day['date'],'Individual' if not item['members'] else 'Conjunto'))
                        for path in item['members']:result.setdefault(' › '.join(path),(day['date'],'Bloco conjunto: '+item['path'][-1]))
                return result
            a,b=contacts(preview['before_calendar']),contacts(preview['after_calendar'])
            st.dataframe(pd.DataFrame([{'Tema':name,'Antes':a.get(name,('Sem vaga na projeção',''))[0],
                'Depois':b.get(name,('Sem vaga na projeção',''))[0],'Forma':b.get(name,('',''))[1]}
                for name in sorted(a.keys()|b.keys())]),hide_index=True,width='stretch')
            st.caption('A data do bloco conjunto é uma oportunidade de prática; não representa contato já realizado em todos os filhos.')
        with st.expander('Todos os dias e integrantes dos grupos'):
            st.json({'groups':preview['groups'],'before':preview['before_calendar'],'after':preview['after_calendar']},expanded=False)
        st.download_button('Baixar prévia completa',json.dumps(preview,ensure_ascii=False,indent=2),'previa-agrupamentos.json','application/json')
        if confirm_button('Aplicar esta divisão',action_key='grouping_apply',details='O calendário será recalculado conforme a prévia. Um backup integral dos dados será salvo antes da alteração.'):
            _apply(service,preview);st.rerun()
    with st.expander('Backup e reversão'):
        if st.button('Salvar backup dos dados e agendamentos'):
            st.session_state['grouping_backup']=str(create_backup(service.repository))
            st.success('Backup verificado e salvo.')
        backup=Path(st.session_state.get('grouping_backup',''))
        if backup.is_file():st.download_button('Baixar backup',backup.read_bytes(),backup.name,'application/zip')
        records=history(service)
        if records:
            options={r['id']:r for r in records}
            chosen=st.selectbox('Alteração para desfazer',list(reversed(options)),format_func=lambda i:f"Alteração #{i} · {options[i]['preview']['created_day']}")
            previous=options[chosen]['preview']['previous']
            if st.button('Preparar prévia de reversão'):
                _preview(service,previous['grouping_mode'],previous['grouping_paths']);st.rerun()
            st.caption('A reversão recupera a divisão anterior e preserva estudos posteriores. A agenda exata anterior está na prévia salva; restauração integral em Arquivos e ferramentas → Backup e restauração.')
            st.download_button('Baixar histórico e calendários anteriores',json.dumps(records,ensure_ascii=False,indent=2),'historico-agrupamentos.json','application/json')
    with st.expander('Critérios e evidências'):
        st.write('Reunimos apenas subárvores completas de categorias específicas, com 2 a 12 subtemas. Lacunas de incidência da fonte não impedem a recomendação automática quando os demais critérios são atendidos; contagens ausentes permanecem desconhecidas. Filhos com incidência igual ou maior que um bloco mínimo ficam separados. Contagens contraditórias ou compromissos individuais impedem o agrupamento. Categorias mais específicas têm preferência. Retornos de blocos conjuntos já registrados são preservados ao mudar de modo. Os limites são heurísticas operacionais auditáveis, não constantes científicas.')
        st.write('A incidência do grupo usa a contagem do pai ou a soma das raízes descendentes disjuntas, dentro da mesma fonte. Não somamos instituições de tabelas sobrepostas. Ausência de informação não equivale a zero.')
        st.markdown('[Estudo sobre prática intercalada](https://www.nature.com/articles/s41539-021-00110-x) · [Limites conforme a semelhança entre categorias](https://pmc.ncbi.nlm.nih.gov/articles/PMC4141442/)')
