"""Controles da retomada; dados pessoais ficam somente no banco privado."""
from datetime import date
import streamlit as st
from .recovery import RecoveryService
from .planner_service import today_local
from .action_feedback import confirm_submit,notify_success


def render_recovery(service,view):
    recovery=RecoveryService(service.repository)
    projection=view['agenda'].get('quantity_recovery')
    if projection and view['date']>=projection['config']['start']:
        reserved=view['plan'].get('routine_override',{}).get('recovery_reserved',0)
        done=projection['done_today'];pending=max(0,reserved-done)
        if projection['remaining'] or done:
            with st.container(border=True):
                st.subheader('Revisões de questões na Osler')
                st.write(f"{pending} para fazer hoje · {projection['due_now']} já venceram · {projection['remaining']} no saldo total")
                st.caption(f"{done} registradas hoje. Esta cota já está reservada dentro da carga total; sem temas ou acertos inventados.")
                if pending:
                    for key in ('recovery_count','recovery_return_count'):
                        if st.session_state.get(key) is not None:st.session_state[key]=min(int(st.session_state[key]),pending)
                    with st.form('quantity_recovery_record'):
                        count=st.number_input('Quantidade de revisões que fiz agora',1,pending,pending,key='recovery_count')
                        returning=st.number_input('Dessas revisões, quantas devem voltar em 7 dias?',0,pending,value=None,
                                                  placeholder='Em branco se não anotou; zero se nenhuma',key='recovery_return_count')
                        known=returning is not None
                        save=confirm_submit('Registrar revisões feitas',action_key='quantity_recovery_record_submit',
                                            details=f'{count} questões revisadas. '+(f'{returning} voltam em sete dias.' if known else 'Quantidade de retornos não informada; nenhum retorno será inventado.'))
                    if save:
                        try:
                            notify_success(recovery.record(view['date'],int(count),view['planning_token'],returning=int(returning) if known else None),'Revisões registradas.')
                            st.rerun()
                        except ValueError as exc:st.error(str(exc))
        if projection['future_returns']:
            with st.expander('Revisões com vencimento futuro'):
                st.dataframe([{'Vencimento':r['due'],'Quantidade':r['count']} for r in projection['future_returns']],hide_index=True)
                st.caption('Vencimento em sete dias corridos. A execução aguarda uma vaga na carga diária; não presume novos erros.')
        with st.expander('Registrar revisões geradas por outras questões'):
            st.caption('Use apenas para questões fora do registro acima e ainda não incluídas no saldo informado. Não conta como estudo adicional.')
            with st.form('recovery_generated_form'):
                generated=st.number_input('Quantas erradas ou sem convicção geraram revisão?',1,100000,1,key='recovery_generated_count')
                source_day=st.date_input('Dia em que fiz essas questões',value=today_local(),min_value=date.fromisoformat(projection['config']['start']),
                                         max_value=today_local(),format='DD/MM/YYYY',key='recovery_generated_day')
                add=confirm_submit('Agendar retorno em 7 dias',action_key='recovery_generated_submit',details=f'{generated} revisões, sete dias após {source_day:%d/%m/%Y}. Sem duplicar o registro anterior.')
            if add:
                try:
                    notify_success(recovery.add_generated(source_day.isoformat(),int(generated),view['planning_token']),'Retorno agendado.')
                    st.rerun()
                except ValueError as exc:st.error(str(exc))
    with st.expander('Reorganizar minha retomada'):
        st.caption('Defina o saldo ainda não feito. Os dias perdidos não dobram a carga. Simulados e descansos continuam reservados.')
        with st.form('quantity_recovery_settings'):
            total=st.number_input('Revisões de questões pendentes na Osler',0,100000,0,key='recovery_total')
            daily=st.number_input('Revisões de questões por dia',1,500,30,key='recovery_daily')
            limit=st.number_input('Limite total de questões por dia, incluindo essas revisões',2,1000,80,key='recovery_limit')
            target=st.number_input('Referência diária de flashcards manuais',1,2000,50,key='recovery_card_target')
            ceiling=st.number_input('Limite habitual para terminar decks inteiros',1,2000,70,key='recovery_card_ceiling')
            start=st.date_input('Começar em',value=today_local(),min_value=today_local(),format='DD/MM/YYYY',key='recovery_start')
            upload=st.file_uploader('HTML dos meus flashcards (opcional)',type=['html','htm','txt'],key='recovery_html')
            st.caption('O HTML será uma nova passagem do acervo, não uma declaração de cartões vencidos. Sem arquivo, usamos o saldo do lote já importado. Decks grandes ficam sozinhos, com no máximo 30 questões totais nesse dia.')
            preview=st.form_submit_button('Conferir retomada')
        if preview:
            try:
                if not daily<limit or target>ceiling:raise ValueError('A cota de revisões deve ser menor que o total; a referência de cards não pode superar o limite.')
                from .error_cards_service import ErrorCardsService
                cards=ErrorCardsService(service.repository)
                if upload:
                    parsed=cards.preview_html(upload.getvalue(),upload.name,today_local().isoformat(),'pass')
                    if parsed['tree']['unallocated']:raise ValueError('Expanda todos os grupos do HTML antes de reservar decks completos.')
                    topics=parsed['tree']['topics'];card_count=parsed['tree']['total']
                else:
                    current=cards.overview(view['date'],question_view=view)
                    topics=current['topics']
                    card_count=sum(t['count'] for t in topics)
                config={'id':-1,'total':int(total),'daily':int(daily),'limit':int(limit),'card_target':int(target),
                    'card_ceiling':int(ceiling),'start':start.isoformat(),'topics':topics,
                    'snapshot_id':-1 if upload else current['snapshot_id'],'carried_returns':recovery.future_carry(view['date'])}
                projected=recovery.projection(view['date'],service.store.days(),view['agenda']['overrides'],view['profile']['exam_date'],config)
                if projected['unassigned_questions'] or projected['unassigned_cards']:
                    raise ValueError('A carga não cabe até a prova. Ajuste os limites ou a data antes de aplicar.')
                st.session_state['quantity_recovery_preview']={'token':service.agenda.token(),'total':int(total),'daily':int(daily),
                    'limit':int(limit),'target':int(target),'ceiling':int(ceiling),'start':start.isoformat(),
                    'raw':upload.getvalue() if upload else None,'filename':upload.name if upload else None,
                    'observed_day':view['date'],'question_rows':projected['questions'],'deck_rows':projected['decks']}
            except ValueError as exc:st.error(str(exc))
        p=st.session_state.get('quantity_recovery_preview')
        if p:
            st.write(f"{p['total']} revisões externas · até {p['limit']} questões totais/dia · decks completos")
            st.caption('As datas são condicionadas aos registros. O saldo não feito ocupa as próximas vagas, sem marcar estudo automaticamente.')
            st.dataframe([{'Data':r['date'],'Cards':r['cards'],'Decks':' · '.join(d['path'][-1] for d in r['decks'])} for r in p['deck_rows'][:14]],hide_index=True)
            from .action_feedback import confirm_button
            if confirm_button('Aplicar retomada',action_key='quantity_recovery_apply',
                              details='Será criado um backup atual. Apenas a organização e as cotas mudam; resultados e histórico ficam preservados.'):
                try:
                    if p['observed_day']!=today_local().isoformat():raise ValueError('O dia de estudo mudou. Confira novamente a retomada.')
                    from .recovery_apply import apply_recovery
                    notify_success(apply_recovery(service.repository,p),'Retomada salva com seu histórico preservado.')
                    st.session_state.pop('quantity_recovery_preview',None);st.rerun()
                except (ValueError,OSError) as exc:st.error(str(exc))
