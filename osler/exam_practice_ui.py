"""Treino, resultado e reforço em controles nativos no Bento existente."""
from .ui_help import explain
from .action_feedback import confirm_button,confirm_submit,notify_success,draft_editor,append_editor_draft

from datetime import date,timedelta

import pandas as pd
import streamlit as st
from .cloud_boundary import cloud_boundary

from .exam_practice import next_correction_day
from .mock_exams import MockExams
from .planner_service import today_local
from .topic_picker_ui import pick_topic


def _day(day):
    return date.fromisoformat(day).strftime('%d/%m/%Y') if day else 'Removido'


def _rows(rows):
    return pd.DataFrame([{'Tema':r['path'][-1],'Data':_day(r['date']),'Questões':r['questions']} for r in rows])


def _notice():
    message=st.session_state.pop('practice_notice',None)
    if message: st.success(message)


def _valid_choice(key,options):
    if key in st.session_state and st.session_state[key] not in options:
        st.session_state.pop(key,None)


def _apply(service,preview,key,method,label):
    if confirm_button(label,key=key,type='primary',action_key='exam_practice_ui_32',details=f"A agenda será atualizada conforme a prévia: {len(preview.get('occurrences',[]))} ocorrências e {len(preview.get('rows',[]))} reservas. Confira as datas e o impacto apresentados."):
        try:
            notify_success(getattr(service,method)(preview),'Agenda atualizada.')
            st.session_state['practice_notice']='Agenda atualizada. Confira as datas em Hoje e Calendário.'
            st.session_state.pop(key+'_preview',None)
            st.rerun()
        except ValueError as exc: st.error(str(exc))


@st.fragment
@cloud_boundary
def render_area_practice(service):
    _notice(); today=today_local(); old=service.area_schedule(); p=service.store.profile()['profile']
    request=(old or {}).get('request',{})
    if st.session_state.pop('area_reschedule_requested',False) and old:
        st.session_state['area_apply_preview']=service.preview_area_schedule(**request)
    with st.container(key='bento-area-practice-intro'):
        st.subheader('Treine por área e instituição')
        st.write('Misture os temas de uma grande área. O rodízio percorre as cinco áreas e todas as instituições escolhidas.')
        explain('Comece com 1 treino de 20 questões por semana, dentro da meta diária. Ajuste a frequência na prévia.')
    pending=[r for r in (old or {}).get('occurrences',[]) if r.get('recovery')]
    if pending:
        st.warning(f'{len(pending)} treino(s) atrasado(s). A recuperação automática preserva a data original.')
        st.dataframe(pd.DataFrame([{'Treino':r['institution']+' · '+r['area'],'Atrasado desde':_day(r['missed_date']),
            'Recuperação':_day(r['date']) if r['status']!='waiting' else 'Sem vaga','Questões':r['questions']} for r in pending]),hide_index=True,width='stretch')
    if old and st.button('Reagendar treinos · abrir prévia',key='area_open_reschedule'):
        st.session_state['area_apply_preview']=service.preview_area_schedule(**old['request']);st.rerun()
    with st.expander('Configurar o rodízio',expanded=not bool(old)):
        institutions=st.text_area('Instituições · uma por linha',value='\n'.join(request.get('institutions') or service.guide.settings()['settings'].get('institutions') or ['UNESP']),key='area_institutions')
        with st.container(key='area_schedule_form'):
            left,right=st.columns(2)
            first=left.date_input('Primeiro treino',value=date.fromisoformat(request.get('first',max(today.isoformat(),p.get('start_date') or today.isoformat()))),key='area_first',format='DD/MM/YYYY')
            end=right.date_input('Programar até',value=date.fromisoformat(request.get('end',p['exam_date'])),key='area_end',format='DD/MM/YYYY')
            frequency=left.radio('Treinos por semana',[1,2],index=request.get('frequency',1)-1,horizontal=True,key='area_frequency')
            questions=right.number_input('Questões por treino',min_value=1,max_value=1000,value=request.get('questions',20),step=1,key='area_questions')
            st.caption('Com dois treinos, as sugestões ficam separadas por três e quatro dias. Você pode mover cada data depois. Nenhum peso de instituição é alterado.')
            submitted=st.button('Ver prévia do rodízio',key='area_preview')
        if submitted:
            try: st.session_state['area_apply_preview']=service.preview_area_schedule(first.isoformat(),end.isoformat(),frequency,int(questions),[i.strip() for i in institutions.splitlines() if i.strip()],request.get('exceptions',{}),request.get('topic_dates',{}))
            except ValueError as exc: st.error(str(exc))
    if old:
        st.subheader('Próximos treinos')
        results={r['exam'].get('practice_id') for r in MockExams(service.repository).active()}
        upcoming=[r for r in old['occurrences'] if (r['date'] or r['original_date'])>=today.isoformat()]
        st.dataframe(pd.DataFrame([{'Data':_day(r['date']),'Instituição':r['institution'],'Área':r['area'],'Questões':r['questions'],
            'Situação':'Resultado registrado' if r['id'] in results else r.get('reason','Programado') if r['date'] else 'Removido'} for r in upcoming]),hide_index=True,width='stretch')
        choices=[r for r in upcoming if r['id'] not in results]
        if choices:
            with st.expander('Mover, retirar ou pausar treinos'):
                ids={r['id']:r for r in choices}
                _valid_choice('area_move_id',ids)
                chosen=st.selectbox('Treino',list(ids),format_func=lambda k:_day(ids[k]['date'])+' · '+ids[k]['institution']+' · '+ids[k]['area'],key='area_move_id')
                move=st.date_input('Nova data',value=max(today,date.fromisoformat(ids[chosen]['date'] or ids[chosen]['original_date'])),min_value=today,key='area_move_date',format='DD/MM/YYYY')
                action=st.radio('O que deseja fazer?',['Mover este treino','Retirar este treino','Pausar todos os próximos'],horizontal=True,key='area_move_action')
                if st.button('Ver prévia da mudança',key='area_move_preview'):
                    changes=dict(request.get('exceptions',{}))
                    if action=='Pausar todos os próximos': changes.update({r['id']:None for r in choices})
                    else: changes[chosen]=None if action=='Retirar este treino' else move.isoformat()
                    try: st.session_state['area_apply_preview']=service.preview_area_schedule(**{**request,'exceptions':changes})
                    except ValueError as exc: st.error(str(exc))
    preview=st.session_state.get('area_apply_preview')
    if preview and ('topic_options' not in preview or 'topic_dates' not in preview.get('request',{})):
        st.session_state.pop('area_apply_preview',None)
        preview=None
        st.info('O agendamento foi atualizado. Gere uma nova prévia para encaixar os conflitos automaticamente.')
    if preview:
        with st.container(border=True,key='bento-area-preview'):
            st.subheader('Confira antes de aplicar')
            st.write(f"{preview['request']['questions']} questões por treino serão reservadas dentro da meta de cada dia. Os temas comuns usam o restante. Resultados anteriores ficam preservados.")
            explain('Conflitos são encaixados em até sete dias da sugestão, respeitando capacidade e compromissos protegidos. Entre datas igualmente próximas, a agenda favorece menor pressão de revisões prioritárias. Confira o impacto antes de aplicar.')
            st.dataframe(pd.DataFrame([{'Sugestão original':_day(r['original_date']),'Data prevista':_day(r['date']),'Instituição':r['institution'],'Área':r['area'],'Situação':r.get('reason','Data escolhida' if r.get('status')=='manual' else 'Programado') if r['date'] else 'Removido'} for r in preview['occurrences']]),hide_index=True,width='stretch')
            blocked=sum(r.get('status')=='blocked' for r in preview['occurrences'])
            moved=sum(r.get('status')=='moved' for r in preview['occurrences'])
            if moved: st.info(f'{moved} treinos encaixados automaticamente em datas livres. A agenda salva só muda ao aplicar.')
            if blocked: st.warning(f'{blocked} treinos sem vaga próxima. Ajuste as datas abaixo ou a carga e o período; a aplicação ficará bloqueada.')
            _edit_area_preview(service,preview)
            with st.expander('Impacto nos próximos temas'):
                st.caption(f"Comparação dos próximos {preview['window_days']} dias. Datas mais distantes serão recalculadas com o desempenho, sem presumir melhora.")
                st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Prioridade':r['priority'],'Antes':_day(r['before_date']) if r['before_date'] else 'A definir','Depois':_day(r['after_date']) if r['after_date'] else 'Fora desta prévia'} for r in preview['topic_changes']]),hide_index=True,width='stretch')
            if not blocked: _apply(service,preview,'area_apply','apply_area_schedule','Aplicar rodízio')
    _area_result(service)


def _edit_area_preview(service,preview):
    """Edits only regenerate a preview; the single apply remains transactional."""
    today=today_local()
    def recalculate(request):
        try:
            st.session_state['area_apply_preview']=service.preview_area_schedule(**request)
            st.rerun()
        except ValueError as exc: st.error(str(exc))
    with st.expander('Ajustar um treino nesta prévia',expanded=True):
        recorded={r['exam'].get('practice_id') for r in MockExams(service.repository).active()}
        choices={r['id']:r for r in preview['occurrences'] if r['id'] not in recorded and r.get('date')}
        if choices:
            _valid_choice('area_preview_train',choices)
            key=st.selectbox('Treino a ajustar',list(choices),format_func=lambda k:_day(choices[k]['date'])+' · '+choices[k]['institution']+' · '+choices[k]['area'],key='area_preview_train')
            row=choices[key]
            day=st.date_input('Data do treino',value=max(today,date.fromisoformat(row['date'] or row['original_date'])),min_value=today,max_value=date.fromisoformat(preview['request']['end']),key='area_preview_date_'+key,format='DD/MM/YYYY')
            if st.button('Recalcular com esta data',key='area_preview_move'):
                recalculate({**preview['request'],'exceptions':{**preview['request']['exceptions'],key:day.isoformat()}})
    with st.expander('Ajustar a data de um tema nesta prévia'):
        options={r['topic_id']:r for r in preview['topic_options']}
        if not options:
            st.caption('Não há temas comuns previstos neste horizonte.')
            return
        st.caption('Escolha um tema e recalcule sua reserva. A dose precisa caber inteira; simulados, descanso e resultados são preservados. A escolha manual pode mudar a divisão entre novos e revisões, sem aumentar a meta. Adiar pode aumentar o tempo sem contato.')
        _valid_choice('area_preview_topic',options)
        key=st.selectbox('Tema',list(options),format_func=lambda k:' › '.join(options[k]['path']),key='area_preview_topic')
        item=options[key]
        current=preview['request']['topic_dates'].get(key,item['date'])
        st.caption(f"Prioridade: {item['priority']} · {item['questions']} questões · Antes do rodízio: {_day(item['date'])}")
        last=min(date.fromisoformat(preview['request']['end']),today+timedelta(days=preview['window_days']-1))
        day=st.date_input('Data do tema',value=date.fromisoformat(current),min_value=today,max_value=last,key='area_preview_topic_date_'+key,format='DD/MM/YYYY')
        if st.button('Recalcular data do tema',key='area_preview_topic_move'):
            recalculate({**preview['request'],'topic_dates':{**preview['request']['topic_dates'],key:day.isoformat()}})
        if key in preview['request']['topic_dates'] and st.button('Voltar à prioridade automática',key='area_preview_topic_reset'):
            recalculate({**preview['request'],'topic_dates':{k:v for k,v in preview['request']['topic_dates'].items() if k!=key}})
        if preview['rows']: st.dataframe(_rows(preview['rows']),hide_index=True,width='stretch')


def _area_result(service):
    schedule=service.area_schedule()
    if not schedule: return
    results={r['exam'].get('practice_id') for r in MockExams(service.repository).active()}
    available={r['id']:r for r in schedule['occurrences'] if r['date'] and r.get('status')!='blocked' and r['id'] not in results}
    with st.container(key='bento-area-result'):
        st.subheader('Registrar treino realizado')
        if not available:
            st.caption('Todos os treinos disponíveis já têm resultado ou estão pausados.')
            return
        requested=st.session_state.pop('area_result_pending',None)
        if requested in available:st.session_state['area_result_id']=requested
        _valid_choice('area_result_id',available)
        chosen=st.selectbox('Qual treino você fez?',list(available),format_func=lambda k:_day(available[k]['date'])+' · '+available[k]['institution']+' · '+available[k]['area'],key='area_result_id')
        row=available[chosen]
        if st.session_state.get('area_result_current')!=chosen:
            for key in ('area_result_day','area_result_questions','area_result_correct','area_result_unseen'): st.session_state.pop(key,None)
            st.session_state['area_result_current']=chosen
        with st.container(key='area_result_form'):
            day=st.date_input('Data em que foi realizado',value=min(today_local(),date.fromisoformat(row['date'])),max_value=today_local(),key='area_result_day',format='DD/MM/YYYY')
            total=st.number_input('Questões realizadas',min_value=1,max_value=1000000,value=row['questions'],key='area_result_questions')
            correct=st.number_input('Acertos no treino',min_value=0,max_value=1000000,value=None,key='area_result_correct')
            unseen=st.checkbox('Todas eram questões inéditas para mim',key='area_result_unseen')
            def validate():
                if day is None:raise ValueError('Informe a data do treino.')
                if correct is None:raise ValueError('Informe o número de acertos.')
                if correct>total:raise ValueError('Acertos não podem passar do total de questões.')
            submitted=confirm_button('Salvar resultado do treino',key='area_result_save',type='primary',action_key='exam_practice_ui_163',details=f"{row['institution']} · {row['area']} · {total} questões · {correct} acertos · {day.strftime('%d/%m/%Y') if day else 'não informada'}",validate=validate)
        if submitted:
            try:
                if correct is None: raise ValueError('Informe o número de acertos.')
                saved=notify_success(service.register_area_result(chosen,day.isoformat(),int(total),int(correct),unseen=unseen,token=service.agenda.token()),'Resultado registrado.')
                st.session_state['mock_selection_pending']=saved['exam_key']
                from .mock_result_followup_ui import request_error_topics
                request_error_topics(saved)
                st.session_state['practice_notice']='Treino salvo. Na aba Correção, informe os temas errados agora ou depois.'
                st.rerun()
            except ValueError as exc: st.error(str(exc))


@st.fragment
@cloud_boundary
def render_mock_correction(service):
    _notice()
    with st.container(key='bento-correction-intro'):
        st.subheader('Transforme os erros em próximos passos')
        st.write('Confira as respostas do simulado. Depois, pratique os temas errados em uma data própria, dentro da sua carga habitual.')
        explain('Quarta-feira é apenas uma sugestão de organização. Os temas recebem quantidades diferentes conforme incidência disponível, dificuldade registrada e erros informados.')
    sources=service.exam_learning_agenda()
    if sources:
        with st.expander('Agenda de correção · ver ou mudar datas'):
            st.dataframe(pd.DataFrame([{'Simulado':r['name'],'Realização':_day(r['source_day']),'Correção':_day(r['date']),
                'Próximo passo':'Reconferir erros' if r['stale'] else 'Informar os temas errados' if r['needs_details'] else f"{r['scheduled_topics']} temas distribuídos"} for r in sources]),hide_index=True,width='stretch')
            options={r['source_id']:r for r in sources if r['needs_details']}
            if options:
                _valid_choice('correction_day_source',options)
                source=st.selectbox('Qual data de correção mudar?',list(options),format_func=lambda k:options[k]['name']+' · '+_day(options[k]['source_day']),key='correction_day_source')
                day=st.date_input('Dia para corrigir',value=max(today_local(),date.fromisoformat(options[source]['date'])),min_value=today_local(),key='correction_day_date',format='DD/MM/YYYY')
                if st.button('Ver prévia da data',key='correction_day_preview'):
                    try: st.session_state['correction_day_apply_preview']=service.preview_correction_day(source,day.isoformat())
                    except ValueError as exc: st.error(str(exc))
                preview=st.session_state.get('correction_day_apply_preview')
                if preview:
                    st.info(f"Correção: {_day(preview['before_date'])} → {_day(preview['date'])}. Os blocos comuns não mudam até você informar os temas e aplicar sua distribuição.")
                    _apply(service,preview,'correction_day_apply','apply_correction_day','Aplicar data de correção')
    exams={r['exam_key']:r for r in MockExams(service.repository).active()}
    if not exams:
        st.info('Registre um resultado na aba Resultados ou Treinos por área. Os temas errados podem ser informados depois.')
        return
    _valid_choice('correction_exam',exams)
    selected=st.selectbox('Simulado a corrigir',list(exams),format_func=lambda k:exams[k]['exam']['name']+' · '+_day(exams[k]['exam']['day']),key='correction_exam')
    if st.session_state.get('correction_current_exam')!=selected:
        for key in ('correction_start','correction_budget','correction_error_count'): st.session_state.pop(key,None)
        st.session_state['correction_current_exam']=selected
    context=service.mock_errors(selected); row=exams[selected]; errors=context['errors']; exam=row['exam']
    if exam['questions']==exam['correct']:
        st.success('Nenhum erro ou branco neste resultado. Não há reforço de erros para distribuir.')
        return
    st.caption(f"{exam['questions']-exam['correct']} erros ou brancos no simulado. Não é necessário informar o total de questões de cada tema.")
    if context['stale']: st.warning('O resultado foi corrigido. Confira os temas e salve novamente antes de distribuí-los.')
    draft_key=f"correction_draft_{selected}_{row['version']}_{context['annotation_id']}"
    draft=st.session_state.setdefault(draft_key,[{'Tema completo':' → '.join(r['path']),'Erros':r.get('errors')} for r in errors])
    catalog,_=service.catalog(today_local().isoformat())
    with st.expander('Adicionar um tema errado',expanded=not bool(draft)):
        topic=pick_topic(catalog,'correction_picker_'+selected)
        count=st.number_input('Quantos erros nesse tema? · opcional',min_value=1,max_value=1000000,value=None,key='correction_error_count')
        if topic and st.button('Adicionar tema à correção',key='correction_add_topic'):
            path=' → '.join(topic['path'])
            if any(r['Tema completo']==path for r in draft): st.info('Esse tema já está na lista abaixo.')
            else:
                new={'Tema completo':path,'Erros':count}
                draft.append(new)
                append_editor_draft(draft_key+'_editor',new)
                st.rerun()
    with st.container(key='correction_errors_form'):
        edited=draft_editor(pd.DataFrame(draft,columns=['Tema completo','Erros']),num_rows='dynamic',hide_index=True,width='stretch',
            column_config={'Tema completo':st.column_config.TextColumn('Tema específico · caminho completo',required=True),
                           'Erros':st.column_config.NumberColumn('Erros · opcional',min_value=1,step=1)},key=draft_key+'_editor')
        explain('Se não souber a quantidade, deixe Erros vazio. O app usa o tema para o reforço sem inventar seu percentual de acerto. Exclua uma linha para retirar um tema.')
        submitted=confirm_button('Salvar temas errados',key='correction_save_errors',action_key='exam_practice_ui_230')
    if submitted:
        try:
            checked=[]
            for r in edited.to_dict('records'):
                name=r['Tema completo']; n=r['Erros']
                if pd.isna(name) and pd.isna(n): continue
                if not isinstance(name,str) or not name.strip(): raise ValueError('Informe o caminho completo do tema.')
                if not pd.isna(n) and (isinstance(n,bool) or float(n)!=int(n)): raise ValueError('Informe uma quantidade inteira de erros.')
                checked.append({'path':[p.strip() for p in name.replace('>>','→').split('→') if p.strip()],'errors':None if pd.isna(n) else int(n)})
            notify_success(service.save_mock_errors(selected,row['version'],checked,context['annotation_id'],service.agenda.token()),'Alterações salvas.')
            st.session_state['practice_notice']='Temas salvos. Confira a distribuição abaixo antes de reservar os blocos.'
            st.rerun()
        except ValueError as exc: st.error(str(exc))
    with st.container(key='bento-correction-distribute'):
        st.subheader('Distribuir a prática dos erros')
        active=service.correction_schedule(selected)
        marker=next((r for r in sources if r['exam_key']==selected),{})
        start=st.date_input('Primeiro dia de prática',value=max(today_local(),date.fromisoformat((active or {}).get('start',marker.get('date',next_correction_day(exam['day']))))),min_value=today_local(),key='correction_start',format='DD/MM/YYYY')
        budget=st.number_input('Até quantas questões de correção por dia?',min_value=1,max_value=1000,value=(active or {}).get('questions',40),key='correction_budget')
        explain('Essa quantidade faz parte da meta diária. Os temas comuns usam o restante. Doses limitadas à recomendação atual; não aumentamos o bloco apenas para preencher espaço.')
        if st.button('Ver prévia da distribuição',key='correction_distribution_preview'):
            try: st.session_state['correction_apply_preview']=service.preview_mock_correction(selected,start.isoformat(),int(budget))
            except ValueError as exc: st.error(str(exc))
        preview=st.session_state.get('correction_apply_preview')
        if preview and preview['exam_key']==selected:
            st.dataframe(_rows(preview['rows']),hide_index=True,width='stretch')
            st.caption(preview['basis']+' Não é incidência específica da banca quando a fonte reúne instituições.')
            if preview['replaced']:
                with st.expander('Reservas destes temas que serão substituídas'):
                    st.dataframe(_rows(preview['replaced']),hide_index=True,width='stretch')
            if preview['unassigned']:
                st.warning('Alguns temas não cabem no período. Antecipe o início ou amplie a carga de correção. Nada será aplicado com temas sem vaga.')
                st.dataframe(pd.DataFrame([{'Tema':r['path'][-1],'Questões':r['questions'],'Motivo':r['reason']} for r in preview['unassigned']]),hide_index=True,width='stretch')
            else: _apply(service,preview,'correction_apply','apply_mock_correction','Reservar prática dos erros')
        if active:
            explain('Programação aplicada. Registre os blocos em Hoje; fazer o reforço não apaga os erros do simulado nem comprova domínio.')
            st.dataframe(_rows(active['rows']),hide_index=True,width='stretch')
            if confirm_button('Desfazer esta distribuição',key='correction_undo',action_key='exam_practice_ui_268'):
                try: notify_success(service.cancel_replan(active['id']),'Agenda atualizada.');st.rerun()
                except ValueError as exc: st.error(str(exc))
    with st.expander('Por que esse método?'):
        st.write('Recuperar a resposta, conferir o feedback e retomar depois ajudam a retenção. Um treino misturado por área reduz a pista oferecida por listas de um único tema. A frequência e os pesos são escolhas práticas que devem ser revistas com seus resultados; não garantem 90% nem aprovação.')
        st.markdown('[Revisão em profissões da saúde](https://pubmed.ncbi.nlm.nih.gov/37615780/) · [Evidências sobre recuperação e feedback](https://pmc.ncbi.nlm.nih.gov/articles/PMC10409703/)')
