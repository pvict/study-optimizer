"""Formulário e confirmação de estudo; persistência e validação pertencem ao serviço/modelo."""
import uuid
import streamlit as st
from .planner_service import today_local
from .study_models import StudyEntry
from .topic_picker_ui import pick_topic
from .study_activity_ui import render_result_feedback
from .study_errors_ui import render_quick_error
from .bento import area_slug,AREA_LABELS,eyebrow
from .balanced_reviews import review_parts
from .topic_catalog import is_practice_topic
from .study_components import render_bank_scope


def entry_validation(entry):
    """Apresenta o erro do modelo no campo correspondente, sem outra regra de validade."""
    try:entry.validate()
    except ValueError as exc:
        if entry.correct is not None and entry.correct>entry.questions:
            return {'correct':f'Acertos não podem passar de {entry.questions}.'}
        if entry.confident_correct is not None and entry.correct is not None and entry.confident_correct>entry.correct:
            return {'confident':f'Convicção não pode passar dos {entry.correct} acertos.'}
        return {'general':str(exc)}
    return {}


def first_block_action(item,day,strategy):
    if strategy=='balanced_v2' and item.get('review_kind') in {'lot_only','combined'}:
        parts=review_parts(item,day)
        if parts['lots']:return {'kind':'lot','entry':parts['lots'][0]}
        return {'kind':'record','topic_id':item['topic_id'],'questions':parts['complement'],'mode':'mistas'}
    if item.get('review_kind')=='lot_only':
        lots=[r for r in item.get('pending_reviews',[]) if r['due_date']<=day]
        if lots:return {'kind':'lot','entry':lots[0]}
        return {'kind':'record','topic_id':item['topic_id'],'questions':item['questions'],'mode':'mistas'}
    mode='mistas' if item['new_questions'] and item['repeat_questions'] else 'repetidas' if item['repeat_questions'] else 'novas'
    return {'kind':'record','topic_id':item['topic_id'],'questions':item['questions'],'mode':mode}


def _next(action,go_record,go_review):
    if action['kind']=='lot':go_review(action['entry'])
    else:go_record(action['topic_id'],action['questions'],action['mode'])


def render_registration(service,go_record,go_review,back_to_plan,edit_entry):
    if 'study_mode' not in st.session_state:
        previous=[r for r in service.store.active(today_local().isoformat()) if r['entry']['kind']=='bloco']
        st.session_state['study_mode']=max(previous,key=lambda r:r['id'])['entry']['mode'] if previous else 'novas'
        st.session_state['last_study_mode']=st.session_state['study_mode']
    saved=st.session_state.get('study_saved')
    if saved:
        st.subheader('Registro concluído')
        st.write(saved['topic'])
        question_view=service.overview(today_local().isoformat())
        plan=question_view['plan']
        summary=f"Salvo. Hoje: {plan['done_questions']} de {plan['target_questions']}." if plan['target_questions'] else f"Salvo. Hoje: {plan['done_questions']} questões · sem meta de blocos."
        st.html('<div class="o-record-saved"><strong>'+summary+'</strong><p>Questões registradas no seu dia de estudo.</p></div>')
        if st.session_state.pop('study_saved_toast',False):st.toast('Resultado salvo.',icon=':material/check_circle:')
        if plan['items']:
            action=first_block_action(plan['items'][0],question_view['date'],question_view['profile']['review_strategy'])
            st.button('Próximo bloco',key='study_next_block',type='primary',on_click=_next,args=(action,go_record,go_review),width='stretch')
        else:st.caption('Nenhum outro bloco no plano de hoje. Você pode voltar ao plano ou registrar outro estudo.')
        st.button('Voltar ao plano',key='study_back_to_plan',type='secondary' if plan['items'] else 'primary',on_click=back_to_plan,width='stretch')
        render_result_feedback(question_view,saved.get('session_id'))
        from .error_cards_service import ErrorCardsService
        queue=ErrorCardsService(service.repository).overview(question_view=question_view)
        event=next((r for r in service.store.active(today_local().isoformat()) if r['session_id']==saved.get('session_id')),None)
        if event and event['entry'].get('cards_created',0):
            count=event['entry']['cards_created']
            if saved['session_id'] in queue['created_session_ids']:
                st.success(f'{count} flashcards criados neste bloco foram incluídos na sua fila de cards de erros. A carga diária foi mantida.')
            else:st.caption(f'{count} flashcards criados neste bloco já estão abrangidos pelo retrato de cards importado; não foram somados outra vez.')
        render_quick_error(service,saved.get('session_id'))
        st.button('Registrar outro estudo',key='study_another_entry',on_click=go_record,args=(saved['topic_id'],20))
        return
    topics,_=service.catalog(today_local().isoformat(),include_parents=True)
    if not topics:
        st.info('Importe um relatório Qbank em Ferramentas para reconhecer os temas. Nenhum indicador por subtema é obrigatório.')
        return
    lookup={t['topic_id']:t for t in topics}
    if st.session_state.get('adaptive_topic') not in lookup:
        st.session_state['adaptive_topic']=next((t['topic_id'] for t in topics if t.get('is_leaf',True)),next(iter(lookup)))
    editing=st.session_state.get('study_edit')
    old=lookup.get(st.session_state.get('adaptive_topic')) if editing else None
    if old and not is_practice_topic(old):
        chosen=old
        st.caption('Corrigindo registro agregado antigo: '+ ' › '.join(old['path'])+'. O caminho será preservado; novos blocos usam temas específicos.')
    elif is_practice_topic(lookup.get(st.session_state.get('adaptive_topic'),{})):
        with st.expander('Trocar tema'):
            chosen=pick_topic(topics,'record',st.session_state.get('adaptive_topic'))
    else: chosen=pick_topic(topics,'record',st.session_state.get('adaptive_topic'))
    if not chosen: return
    selected=chosen['topic_id']
    slug=area_slug(chosen['path'])
    st.html(eyebrow(AREA_LABELS[slug],slug))
    st.subheader(chosen['path'][-1])
    st.caption(' › '.join(chosen['path'][:-1]))
    render_bank_scope(chosen,service.store.profile()['profile']['min_block'])
    if st.session_state.get('study_review_of'): st.info('Revisão vinculada a uma pendência. Só acertos com convicção saem dessa fila; o restante retorna em 7 dias.')
    kind=st.segmented_control('O que você está registrando?',['bloco','acumulado','contato'],format_func={'bloco':'Um bloco que fiz','acumulado':'Um total acumulado anterior','contato':'Estudei sem fazer questões'}.get,key='study_kind',default='bloco',required=True,width='stretch')
    with st.expander('Outras formas de registrar'):
        method=st.radio('Como informar o rendimento?',['acertos','percentual'],format_func={'acertos':'Quantidade de acertos','percentual':'Só tenho o percentual aproximado'}.get,horizontal=True,key='study_method') if kind!='contato' else 'acertos'
        if kind=='acumulado': st.caption('Este total ficará separado dos blocos e PDFs para evitar contar o mesmo estudo duas vezes.')
    editing=st.session_state.get('study_edit')
    if editing or st.session_state.get('study_review_of'): st.button('Registrar outro estudo',on_click=go_record,args=(selected,20))
    if editing: st.caption('Correção de um lançamento: a versão anterior será preservada.')
    with st.form('study_entry'):
        if kind!='contato':
            fields=st.columns(3 if method=='acertos' else 2)
            left,right=fields[:2]
            n=left.number_input('Quantas questões você fez?',min_value=1,max_value=1000000,value=20,key='study_n')
            correct=right.number_input('Quantas acertou?',min_value=0,max_value=1000000,value=None,key='study_correct') if method=='acertos' else None
            correct_hint=right.empty()
            percent=right.number_input('Percentual aproximado de acerto',min_value=0.,max_value=100.,value=None,key='study_percent') if method=='percentual' else None
            confident=fields[2].number_input('Desses acertos, quantos foram com convicção?',min_value=0,max_value=1000000,value=None,key='study_confident') if method=='acertos' else None
            confident_hint=fields[2].empty() if method=='acertos' else None
            st.caption('Acerto por acaso fica fora da convicção. Erros e chutes retornam para revisão em 7 dias. Deixe vazio se não souber.')
        else: n,correct,percent,confident=0,None,None,None
        cards_created=0
        if kind=='bloco' and is_practice_topic(chosen):
            with st.expander('Flashcards criados neste bloco (opcional)'):
                cards_created=st.number_input('Quantos flashcards de erros você criou?',0,5000,0,key='study_cards_created')
                st.caption('Conte apenas os cards novos que você criou neste bloco, não os que revisou. Eles entram automaticamente na fila deste tema; a meta diária de cards não muda.')
        with st.expander('Data, modalidade e detalhes'):
            day=st.date_input('Data do estudo ou corte do acumulado',value=today_local(),max_value=today_local(),key='study_date',format='DD/MM/YYYY',help='O dia de estudo vai das 04h até antes das 04h do dia seguinte, no horário de Brasília. Registros anteriores mantêm a data informada.')
            mode=st.selectbox('Essas questões eram',['novas','repetidas','mistas'],format_func={'novas':'Novas para mim','repetidas':'Questões que já fiz antes','mistas':'Mistura ou não sei separar'}.get,key='study_mode') if kind!='contato' else 'mistas'
            duration=st.number_input('Minutos gastos neste estudo',min_value=0.1,max_value=1440.,value=None,key='study_duration')
            last=st.text_input('Último contato conhecido no acumulado (AAAA-MM-DD)',key='study_last_contact') if kind=='acumulado' else None
        submitted=st.form_submit_button('Salvar resultado e atualizar meu plano',type='primary')
        general_hint=st.empty()
    if submitted:
        entry=StudyEntry(lookup[selected]['path'],day.isoformat(),int(n),int(correct) if correct is not None else None,percent,kind,mode,duration,last or None,
                         confident_correct=int(confident) if confident is not None else None,review_of=st.session_state.get('study_review_of'),
                         cards_created=int(cards_created))
        errors=entry_validation(entry)
        if errors:
            if 'correct' in errors:correct_hint.error(errors['correct'])
            elif 'confident' in errors:confident_hint.error(errors['confident'])
            else:general_hint.error(errors['general'])
            return
        sid=editing['session_id'] if editing else st.session_state.setdefault('study_entry_id',uuid.uuid4().hex)
        service.save_entry(entry,sid,editing['version'] if editing else 0)
        st.session_state['last_study_mode']=entry.mode
        st.session_state['study_saved']={'topic':chosen['path'][-1],'topic_id':selected,'session_id':sid}
        for key in ['study_edit','study_entry_id','study_correct','study_percent','study_confident','study_review_of','study_cards_created']: st.session_state.pop(key,None)
        st.session_state['study_saved_toast']=True
        st.rerun()
    with st.expander('Importar vários resultados de uma vez'):
        st.write('CSV/TSV de blocos ou acumulados, ou tabela colada. Use id_sessao para identificar cada lançamento; reimportar o mesmo arquivo não duplica o histórico. Acertos e percentual são alternativas.')
        template='id_sessao;tema;data;tipo;modalidade;questoes;acertos;percentual;minutos;ultimo_contato;versao;acertos_conviccao;revisao_de;cards_criados\n'
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
            st.button('Editar este lançamento',on_click=edit_entry,args=(event,))
            if st.button('Desconsiderar este lançamento'):
                service.store.void(chosen,event['version'])
                st.session_state['adaptive_notice']='Lançamento desconsiderado. O histórico foi preservado.'
                st.rerun()
