"""Planejamento diário com atualização curta, sem configuração por subtema."""
from dataclasses import replace
from datetime import date
import sqlite3
import uuid

import streamlit as st

from .adaptive_service import AdaptiveService
from .guide_settings_ui import render_guide_settings
from .planner_service import today_local
from .study_models import StudyEntry, AdaptiveProfile
from .study_day_ui import render_study_day
from .study_tables_ui import render_topic_table
from .topic_picker_ui import pick_topic, reset_picker
from .study_calendar_ui import render_calendar
from .exam_goals_ui import render_exam_goals
from .exam_goals import ExamGoals
from .study_evolution_ui import render_evolution
from .study_activity_ui import render_result_feedback
from .study_errors_ui import render_quick_error,render_errors
from .mock_exams_ui import render_mock_exams,render_mock_settings
from .final_review_ui import render_exam_weights

VIEWS=['Meu dia','Calendário','Evolução','Temas e estatísticas','Registrar resultados','Simulados','Ajustes']


def _go_record(topic_id,questions,mode='novas'):
    reset_picker('record')
    st.session_state.pop('study_saved',None)
    st.session_state['adaptive_view']='Registrar resultados'
    st.session_state['adaptive_topic']=topic_id
    st.session_state['study_n']=questions
    st.session_state['study_kind']='bloco'
    st.session_state['study_mode']=mode
    st.session_state['study_method']='acertos'
    st.session_state.pop('study_correct',None)
    st.session_state.pop('study_edit',None)
    st.session_state.pop('study_review_of',None)
    st.session_state.pop('study_confident',None)
    st.session_state.pop('study_date',None)
    st.session_state.pop('study_duration',None)
    st.session_state.pop('record_search',None)
    st.session_state['study_entry_id']=uuid.uuid4().hex


def _go_review(item):
    from .models import stable_topic_id
    _go_record(stable_topic_id(item['path']),item['questions'],'repetidas')
    st.session_state['study_review_of']=item['session_id']


def _back_to_plan():
    st.session_state['adaptive_view']='Meu dia'


def render_adaptive(repo):
    service=AdaptiveService(repo)
    if st.session_state.get('adaptive_view') not in VIEWS: st.session_state['adaptive_view']='Meu dia'
    with st.container(key='study_navigation'):
        view=st.radio('Seu estudo',VIEWS,format_func=lambda v:{'Meu dia':'Hoje','Temas e estatísticas':'Temas','Registrar resultados':'Registrar'}.get(v,v),horizontal=True,key='adaptive_view',label_visibility='collapsed',width='stretch')
    current=st.session_state['adaptive_view']
    st.title({'Meu dia':'Seu plano de hoje','Calendário':'Calendário de estudos','Temas e estatísticas':'Temas e desempenho',
              'Registrar resultados':'Registrar resultado','Ajustes':'Ajustes do plano','Evolução':'Sua evolução','Simulados':'Seus simulados'}[current])
    st.caption({'Meu dia':'Faça os blocos abaixo e registre o resultado para atualizar o plano.',
                'Calendário':'Consulte os próximos dias e abra espaço para suas revisões.',
                'Temas e estatísticas':'Encontre o que precisa de atenção e acompanhe seu rendimento.',
                'Registrar resultados':'Registre o que fez. O próximo plano acompanha seus resultados.',
                'Ajustes':'Defina sua rotina uma vez. Ajuste quando precisar.','Evolução':'Enxergue o que já construiu e explore os próximos capítulos da preparação.',
                'Simulados':'Acompanhe provas completas, com resultados separados dos blocos do dia.'}[current])
    if 'adaptive_notice' in st.session_state: st.success(st.session_state.pop('adaptive_notice'))
    if 'adaptive_error' in st.session_state: st.error(st.session_state.pop('adaptive_error'))
    if view!='Ajustes': st.session_state.pop('adaptive_profile_snapshot',None)
    if view!='Ajustes': st.session_state.pop('exam_primary_snapshot',None)
    if view!='Meu dia': st.session_state.pop('day_form_snapshot',None)
    if view!='Meu dia': st.session_state.pop('distribution_profile_snapshot',None)
    if view!='Calendário':
        for key in list(st.session_state):
            if key.startswith('calendar_snapshot_'): st.session_state.pop(key,None)
    try:
        if view=='Meu dia': render_study_day(service,_go_record,_go_review,_edit)
        elif view=='Calendário': render_calendar(service,_go_record,_go_review)
        elif view=='Registrar resultados':
            with st.container(key='study_registration'): _register(service)
        elif view=='Temas e estatísticas':
            stats,errors=st.tabs(['Desempenho dos temas','Erros abertos'])
            with stats: render_topic_table(service,_go_record)
            with errors: render_errors(service)
        elif view=='Evolução': render_evolution(service)
        elif view=='Simulados': render_mock_exams(service)
        else:
            st.subheader('Seu plano, do seu jeito')
            settings=st.radio('O que ajustar?',['Meta e rotina','Minhas provas','Instituições e incidências'],horizontal=True,key='study_settings_section')
            if settings=='Meta e rotina':
                with st.container(key='study_settings'):
                    _settings(service)
                    render_mock_settings(service)
            elif settings=='Minhas provas':
                render_exam_goals(service)
                render_exam_weights(service)
            else: render_guide_settings(repo)
    except (ValueError,sqlite3.Error,OSError) as exc:
        st.error(str(exc))


def _register(service):
    saved=st.session_state.get('study_saved')
    if saved:
        st.subheader('Registro concluído')
        st.write(saved['topic'])
        render_result_feedback(service.overview(today_local().isoformat()),saved.get('session_id'))
        render_quick_error(service,saved.get('session_id'))
        st.button('Voltar ao plano',key='study_back_to_plan',type='primary',on_click=_back_to_plan)
        st.button('Registrar outro estudo',key='study_another_entry',on_click=_go_record,args=(saved['topic_id'],20))
        return
    topics,_=service.catalog(today_local().isoformat(),include_parents=True)
    if not topics:
        st.info('Importe um relatório Qbank em Ferramentas para reconhecer os temas. Nenhum indicador por subtema é obrigatório.')
        return
    lookup={t['topic_id']:t for t in topics}
    if st.session_state.get('adaptive_topic') not in lookup: st.session_state['adaptive_topic']=next(iter(lookup))
    editing=st.session_state.get('study_edit')
    old=lookup.get(st.session_state.get('adaptive_topic')) if editing else None
    if old and not old.get('is_leaf',True):
        chosen=old
        st.caption('Corrigindo registro agregado antigo: '+ ' › '.join(old['path'])+'. O caminho será preservado; novos blocos usam temas específicos.')
    elif st.session_state.get('study_n') and lookup.get(st.session_state.get('adaptive_topic'),{}).get('is_leaf',True):
        with st.expander('Trocar tema'):
            chosen=pick_topic(topics,'record',st.session_state.get('adaptive_topic'))
    else: chosen=pick_topic(topics,'record',st.session_state.get('adaptive_topic'))
    if not chosen: return
    selected=chosen['topic_id']
    st.subheader(chosen['path'][-1])
    st.caption(' › '.join(chosen['path'][:-1]))
    if st.session_state.get('study_review_of'): st.info('Revisão vinculada a uma pendência. Só acertos com convicção saem dessa fila; o restante retorna em 7 dias.')
    with st.expander('Outras formas de registrar'):
        kind=st.radio('O que você está registrando?',['bloco','acumulado','contato'],format_func={'bloco':'Um bloco que fiz','acumulado':'Um total acumulado anterior','contato':'Estudei sem fazer questões'}.get,horizontal=True,key='study_kind')
        method=st.radio('Como informar o rendimento?',['acertos','percentual'],format_func={'acertos':'Quantidade de acertos','percentual':'Só tenho o percentual aproximado'}.get,horizontal=True,key='study_method') if kind!='contato' else 'acertos'
        if kind=='acumulado': st.caption('Este total ficará separado dos blocos e PDFs para evitar contar o mesmo estudo duas vezes.')
    editing=st.session_state.get('study_edit')
    if editing or st.session_state.get('study_review_of'): st.button('Registrar outro estudo',on_click=_go_record,args=(selected,20))
    if editing: st.caption('Correção de um lançamento: a versão anterior será preservada.')
    with st.form('study_entry'):
        if kind!='contato':
            left,right=st.columns(2)
            n=left.number_input('Quantas questões você fez?',min_value=1,max_value=1000000,value=20,key='study_n')
            correct=right.number_input('Quantas acertou?',min_value=0,max_value=1000000,value=None,key='study_correct') if method=='acertos' else None
            percent=right.number_input('Percentual aproximado de acerto',min_value=0.,max_value=100.,value=None,key='study_percent') if method=='percentual' else None
            confident=st.number_input('Desses acertos, quantos foram com convicção?',min_value=0,max_value=1000000,value=None,key='study_confident') if method=='acertos' else None
            st.caption('Acerto por acaso fica fora da convicção. Erros e chutes retornam para revisão em 7 dias. Deixe vazio se não souber.')
        else: n,correct,percent,confident=0,None,None,None
        with st.expander('Data, modalidade e detalhes'):
            day=st.date_input('Data do estudo ou corte do acumulado',value=today_local(),max_value=today_local(),key='study_date',format='DD/MM/YYYY',help='O dia de estudo vai das 04h até antes das 04h do dia seguinte, no horário de Brasília. Registros anteriores mantêm a data informada.')
            mode=st.selectbox('Essas questões eram',['novas','repetidas','mistas'],format_func={'novas':'Novas para mim','repetidas':'Questões que já fiz antes','mistas':'Mistura ou não sei separar'}.get,key='study_mode') if kind!='contato' else 'mistas'
            duration=st.number_input('Minutos gastos neste estudo',min_value=0.1,max_value=1440.,value=None,key='study_duration')
            last=st.text_input('Último contato conhecido no acumulado (AAAA-MM-DD)',key='study_last_contact') if kind=='acumulado' else None
        submitted=st.form_submit_button('Salvar resultado e atualizar meu plano',type='primary')
    if submitted:
        entry=StudyEntry(lookup[selected]['path'],day.isoformat(),int(n),int(correct) if correct is not None else None,percent,kind,mode,duration,last or None,
                         confident_correct=int(confident) if confident is not None else None,review_of=st.session_state.get('study_review_of'))
        sid=editing['session_id'] if editing else st.session_state.setdefault('study_entry_id',uuid.uuid4().hex)
        service.save_entry(entry,sid,editing['version'] if editing else 0)
        st.session_state['study_saved']={'topic':chosen['path'][-1],'topic_id':selected,'session_id':sid}
        for key in ['study_edit','study_entry_id','study_correct','study_percent','study_confident','study_review_of']: st.session_state.pop(key,None)
        st.session_state['adaptive_notice']='Resultado salvo. O plano, os alertas e a evolução foram atualizados.'
        st.rerun()
    with st.expander('Importar vários resultados de uma vez'):
        st.write('CSV/TSV de blocos ou acumulados, ou tabela colada. Use id_sessao para identificar cada lançamento; reimportar o mesmo arquivo não duplica o histórico. Acertos e percentual são alternativas.')
        template='id_sessao;tema;data;tipo;modalidade;questoes;acertos;percentual;minutos;ultimo_contato;versao;acertos_conviccao;revisao_de\n'
        st.download_button('Baixar cabeçalho da tabela',template.encode('utf-8-sig'),'resultados_modelo.csv','text/csv')
        upload=st.file_uploader('Resultados CSV ou TSV',type=['csv','tsv'],key='study_upload')
        pasted=st.text_area('Ou cole a tabela de resultados',key='study_paste')
        if st.button('Importar resultados',disabled=not upload and not pasted.strip()):
            text=upload.getvalue().decode('utf-8-sig') if upload else pasted
            count=service.import_text(text)
            st.session_state['adaptive_notice']=f'{count} lançamentos processados. Reenvios idênticos foram reconhecidos.'
            st.rerun()
    with st.expander('Corrigir ou desconsiderar um lançamento'):
        active=service.store.active(today_local().isoformat())
        if active:
            by_id={s['session_id']:s for s in active}
            chosen=st.selectbox('Registro',list(by_id),format_func=lambda key:f"{by_id[key]['entry']['day']} · {' → '.join(by_id[key]['entry']['path'])} · {by_id[key]['entry']['questions']} questões")
            event=by_id[chosen]
            st.caption('Desconsiderar remove a contribuição do cálculo, preservando o histórico.')
            st.button('Editar este lançamento',on_click=_edit,args=(event,))
            if st.button('Desconsiderar este lançamento'):
                service.store.void(chosen,event['version'])
                st.session_state['adaptive_notice']='Lançamento desconsiderado. O histórico foi preservado.'
                st.rerun()


def _edit(event):
    from .models import stable_topic_id
    reset_picker('record')
    st.session_state['adaptive_view']='Registrar resultados'
    st.session_state.pop('study_saved',None)
    e=event['entry']
    st.session_state['study_edit']=event
    st.session_state.pop('record_search',None)
    st.session_state['study_review_of']=e.get('review_of')
    st.session_state['study_confident']=e.get('confident_correct')
    st.session_state['study_method']='percentual' if e['percent'] is not None else 'acertos'
    st.session_state['adaptive_topic']=stable_topic_id(e['path'])
    for key,value in {'study_n':e['questions'] or 1,'study_correct':e['correct'],'study_percent':e['percent'],'study_kind':e['kind'],
                      'study_mode':e['mode'],'study_duration':e['minutes'],'study_date':date.fromisoformat(e['day']),'study_last_contact':e.get('last_contact') or ''}.items():
        st.session_state[key]=value


def _settings(service):
    if st.button('Recarregar ajustes salvos'):
        st.session_state.pop('adaptive_profile_snapshot',None)
        st.rerun()
    record=st.session_state.setdefault('adaptive_profile_snapshot',service.store.profile())
    p=AdaptiveProfile(**record['configured_profile'])
    st.write('Ajustes globais. Não é necessário configurar cada tema.')
    with st.form('adaptive_profile'):
        st.subheader('Rotina diária')
        count=st.number_input('Meta padrão de questões por dia',min_value=1,max_value=1000,value=p.max_questions)
        st.caption('O tempo disponível não limita essa meta. Você pode mudar um dia específico na tela Hoje.')
        share_percent=st.slider('Questões em temas novos (%)',0,100,round(p.new_share*100),step=5,key='settings_new_share')
        share=share_percent/100
        workload_mode=st.radio('Como distribuir a rotina?',['adaptive','fixed'],index=0 if p.workload_mode=='adaptive' else 1,
                               format_func={'adaptive':'Adaptativa — abre espaço para revisões','fixed':'Fixa — mantém a proporção escolhida'}.get,key='settings_workload_mode')
        st.divider()
        st.subheader('Objetivos e datas')
        start=st.date_input('Início do cronograma',value=date.fromisoformat(p.start_date) if p.start_date else None,key='settings_start_date',format='DD/MM/YYYY')
        st.caption('Antes dessa data, o app não cobra metas nem faltas. O histórico anterior continua valendo para as revisões.')
        target=st.number_input('Meta de acerto nos temas (%)',min_value=1.,max_value=100.,value=float(p.target_accuracy))
        st.caption('Objetivo de aprendizagem: acerto com convicção em questões novas e amostra suficiente. Não é nota de prova nem probabilidade de aprovação.')
        if ExamGoals(service.repository).active():
            exam=date.fromisoformat(p.exam_date)
            st.caption('Data efetiva do plano: '+record['profile']['exam_date']+'. Gerencie em Minhas provas.')
        else: exam=st.date_input('Data de referência da prova',value=date.fromisoformat(p.exam_date),format='DD/MM/YYYY')
        with st.expander('Metas por grande área (opcional)'):
            catalog,_=service.catalog(today_local().isoformat())
            from .models import normalize_path
            areas={normalize_path([t['path'][0]])[0]:t['path'][0] for t in catalog}
            for name in p.area_targets: areas.setdefault(normalize_path([name])[0],name)
            values=[{'Área':name,'Usar meta própria':any(normalize_path([name])==normalize_path([k]) for k in p.area_targets),
                     'Meta (%)':float(p.target_for_area(name))} for name in sorted(areas.values())]
            import pandas as pd
            area_frame=st.data_editor(pd.DataFrame(values,columns=['Área','Usar meta própria','Meta (%)']),hide_index=True,width='stretch',disabled=['Área'],key='area_targets_'+str(record['id']),
                                      column_config={'Meta (%)':st.column_config.NumberColumn(min_value=1.,max_value=100.,step=1.)})
            st.caption('Ative só as áreas que quiser personalizar. As demais usam a meta global; não há configuração por subtema.')
        st.caption(f"{share_percent}% de questões em temas novos · {100-share_percent}% em revisões e diagnósticos. A proporção pode ser aproximada se faltarem temas elegíveis ou vagas por dia.")
        with st.expander('Instituições, distribuição e detalhes'):
            weights=st.text_area('Instituições e importância (uma por linha: nome;peso)',value='\n'.join(f'{k};{v:g}' for k,v in p.institution_weights.items()),placeholder='USP;60\nPSU-MG;40')
            st.caption('Use os nomes das tabelas importadas. Uma tabela conjunta não informa a incidência individual dos seus membros.')
            max_topics=st.number_input('Máximo de temas por dia',min_value=1,max_value=10,value=p.max_topics)
            recent=st.number_input('Janela recente em dias',min_value=1,max_value=730,value=p.recent_days)
            minimum=st.number_input('Mínimo de questões por bloco automático',min_value=1,max_value=100,value=p.min_block)
            gap=st.number_input('Máximo de dias entre contatos',min_value=1,max_value=90,value=p.max_contact_gap)
        save=st.form_submit_button('Salvar planejamento',type='primary')
    if save:
        institutions={}
        for line in weights.splitlines():
            if not line.strip(): continue
            parts=[s.strip() for s in line.split(';')]
            if len(parts)!=2 or parts[0] in institutions: raise ValueError('Use instituição;peso, sem nomes repetidos.')
            institutions[parts[0]]=float(parts[1].replace(',','.'))
        service.store.save_profile(replace(p,target_accuracy=target,exam_date=exam.isoformat(),start_date=start.isoformat() if start else None,max_questions=int(count),
                                           institution_weights=institutions,new_share=share,workload_mode=workload_mode,max_topics=int(max_topics),recent_days=int(recent),min_block=int(minimum),max_contact_gap=int(gap),
                                           area_targets={r['Área']:float(r['Meta (%)']) for _,r in area_frame.iterrows() if r['Usar meta própria']}),record['id'])
        st.session_state.pop('adaptive_profile_snapshot',None)
        st.session_state['adaptive_notice']='Planejamento atualizado. As próximas quantidades já seguem esses ajustes.'
        st.rerun()
