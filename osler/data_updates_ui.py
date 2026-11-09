"""Atualizações locais com duas fontes distintas, prévia e confirmação."""
import hashlib
import json
import sqlite3

import pandas as pd
import streamlit as st

from .action_feedback import confirm_button, notify_success, preserve_drafts
from .planner_service import today_local
from .ui_help import explain


SCOPES={'pending':'Somente não estudados ou pendentes',
        'inventory':'Todos os criados, inclusive já revisados',
        'pass':'Nova passagem por todos os cards do arquivo'}
DRAFTS={'planner':('updates_planner_paste','updates_planner_day','updates_planner_incidence','updates_planner_institutions'),
        'cards':('updates_cards_paste','updates_cards_day','updates_cards_scope','updates_cards_complete')}


def preserve_updates_drafts(active=None):
    for kind,keys in DRAFTS.items():
        if kind!=active:preserve_drafts(*keys)


def _date(day):
    return '/'.join(reversed(day.split('-')))


def open_updates(tab='Planner de questões'):
    from .study_navigation_ui import go_view
    st.session_state['updates_tab']=tab
    go_view('Atualizar dados')


def _upload_changed(kind):
    upload=st.session_state.get(f'updates_{kind}_file')
    key=f'updates_{kind}_source'
    if upload is None:st.session_state.pop(key,None)
    else:st.session_state[key]={'data':upload.getvalue(),'filename':upload.name}


def _clear_source(kind):
    for suffix in ('source','file','result'):
        st.session_state.pop(f'updates_{kind}_{suffix}',None)


def _source(kind,label):
    upload=st.file_uploader(label,type=['html','htm','txt'],key=f'updates_{kind}_file',
                            on_change=_upload_changed,args=(kind,))
    if upload is not None:
        st.session_state[f'updates_{kind}_source']={'data':upload.getvalue(),'filename':upload.name}
    with st.expander('Colar HTML'):
        pasted=st.text_area('Cole o HTML completo',key=f'updates_{kind}_paste',height=150)
    cached=st.session_state.get(f'updates_{kind}_source')
    if cached:
        if upload is None:
            st.caption('Arquivo selecionado: '+cached['filename'])
            st.button('Retirar arquivo',key=f'updates_{kind}_clear',on_click=_clear_source,args=(kind,))
        return cached['data'],cached['filename']
    return (pasted.encode('utf-8'),'html-colado.html') if pasted.strip() else (None,None)


def _help(kind):
    with st.expander('Como copiar o HTML da Osler'):
        st.markdown('1. Abra a seção correspondente na Osler e confira os filtros.\n'
                    '2. Pressione **F12** e abra **Elements / Elementos**.\n'+
                    ('3. Selecione o elemento **table** que contém os temas, questões e segurança.\n' if kind=='planner' else
                     '3. Expanda os grupos e selecione o **container da árvore inteira**, incluindo os pais.\n')+
                    '4. Clique com o botão direito → **Copy → Copy outerHTML**. Cole no campo deste app ou salve em um arquivo `.html` em UTF-8.')
        st.write('Confira o número de temas na prévia. Copiar a página só traz as linhas presentes no HTML; rolagem ou filtros podem deixar o arquivo parcial.')
        if kind=='cards':st.write('Para atualizar atrasados, copie a árvore filtrada para não estudados ou pendentes. Uma lista de todos os criados é inventário e inclui cards já feitos.')


def _signature(data,options):
    return hashlib.sha256(data+json.dumps(options,sort_keys=True,ensure_ascii=False).encode()).hexdigest() if data else None


def _capture_day(label,kind):
    key=f'updates_{kind}_day'
    value=st.date_input(label,value=None if key in st.session_state else today_local(),
                        max_value=today_local(),key=key,format='DD/MM/YYYY')
    return value.isoformat() if value else None


def _comparison(frame):
    """Rótulos legíveis sem converter a base numérica em texto para ordenar."""
    formats={}
    for column in frame.columns:
        if column.startswith('Convicção'):formats[column]='{:.1f}'
        elif column.startswith(('Contato','Último contato')):formats[column]=_date
        elif column.startswith(('Questões','Incidência','Cards','Saldo')) or column in {'Pendentes','Diferença'}:
            formats[column]='{:.0f}'
    st.dataframe(frame.style.format(formats,na_rep='—'),hide_index=True,width='stretch',
                 height=min(360,38+35*max(1,len(frame))))


def _preview(kind,data,options,build):
    signature=_signature(data,options);key=f'updates_{kind}_result'
    cached=st.session_state.get(key)
    if cached and cached['signature']!=signature:
        st.session_state.pop(key,None);cached=None
        if kind=='cards':st.session_state.pop('updates_cards_complete',None)
        st.info('Os dados mudaram. Gere uma nova prévia.')
    if st.button('Conferir atualização',key=f'updates_{kind}_preview',disabled=not data or not options.get('day') or options.get('scope',True) is None):
        if kind=='cards':st.session_state.pop('updates_cards_complete',None)
        try:
            with st.spinner('Conferindo o arquivo…'):value=build()
            cached={'signature':signature,'preview':value}
            st.session_state[key]=cached
        except (ValueError,OSError,sqlite3.Error) as exc:
            st.session_state.pop(key,None);cached=None
            st.error(str(exc))
    return cached['preview'] if cached else None


def _planner(repo):
    from .planner_import import PlannerImportService
    service=PlannerImportService(repo)
    datasets=service.guide.datasets()
    snapshots=[d for d in datasets if d.get('source_kind')=='manual_osler_planner_export']
    if snapshots:
        latest=max(snapshots,key=lambda d:(d['observed_date'],d['id']))
        st.write(f"Última captura: **{_date(latest['observed_date'])}** · {latest.get('received_rows',len(latest['rows'])):,} temas".replace(',','.'))
    with st.container(key='bento-updates-planner'):
        data,filename=_source('planner','Tabela do Planner (HTML ou TXT)')
        day=_capture_day('Data em que você copiou a tabela','planner')
        incidence=st.checkbox('Atualizar também a incidência desta consulta',key='updates_planner_incidence')
        institutions=[]
        if incidence:
            defaults=next((d['institutions'] for d in reversed(datasets) if d.get('incidence_included') is not False),[])
            text=st.text_input('Instituições selecionadas na Osler',value='; '.join(defaults),
                               placeholder='Separe por ponto e vírgula',key='updates_planner_institutions')
            institutions=[s.strip() for s in text.split(';') if s.strip()]
        _help('planner')
        options={'day':day,'incidence':incidence,'institutions':institutions}
        preview=_preview('planner',data,options,lambda:service.preview(data,filename,day,include_incidence=incidence,institutions=institutions))
        if preview:
            st.subheader('Confira o que será atualizado')
            st.write(f"**{preview['received_rows']} temas recebidos · {preview['matched_rows']} reconhecidos**")
            if preview['preserved_topics']:st.info(f"{preview['preserved_topics']} temas ausentes neste arquivo manterão os dados anteriores.")
            unmatched=preview['received_rows']-preview['matched_rows']
            if unmatched:st.warning(f'{unmatched} temas não correspondem ao acervo atual. O arquivo será preservado; esses temas não terão dados atribuídos a outro assunto.')
            frame=pd.DataFrame(preview['comparison']).rename(columns={'Questões novas':'Questões agora','Convicção nova (%)':'Convicção agora (%)','Contato novo':'Último contato agora'})
            _comparison(frame)
            with st.expander('O que muda no plano'):
                st.write('Questões distintas, segurança acumulada, dias sem contato e pendências passam a usar esta captura nos temas recebidos. Prioridades e próximos planejamentos serão recalculados. Blocos registrados e fontes anteriores ficam preservados e não são somados ao acumulado.')
                st.write('Último contato = data da captura menos dias sem contato. Quando esse campo está ausente, o app não inventa uma data.')
                st.write('A incidência será atualizada para o conjunto informado.' if incidence else 'As incidências atuais serão mantidas.')
            stale=preview['token']!=service.adaptive.agenda.token()
            if preview['duplicate_id']:st.info('Esta atualização já foi importada. Nenhuma contagem foi repetida.')
            if stale:st.info('O plano foi atualizado em outra tela. Clique em Conferir atualização novamente.')
            if confirm_button('Atualizar Planner',key='updates_planner_apply',action_key='updates_planner_apply',type='primary',
                disabled=stale or bool(preview['duplicate_id']),
                details=f"Atualizar {preview['matched_rows']} temas com a captura de {_date(day)}. Temas ausentes e registros anteriores serão preservados. "+('A incidência também será atualizada.' if incidence else 'As incidências serão mantidas.')):
                try:
                    notify_success(service.apply(preview,data),'Planner atualizado.')
                    st.session_state.pop('updates_planner_result',None)
                    st.session_state['updates_notice']='Planner atualizado. Seus próximos planos já podem usar os novos dados.'
                    st.rerun()
                except (ValueError,OSError,sqlite3.Error) as exc:st.error(str(exc))
    if snapshots:
        with st.expander('Histórico de capturas do Planner'):
            st.dataframe(pd.DataFrame([{'Captura':d['observed_date'],'Arquivo':d.get('filename','HTML do Planner'),
                                      'Temas':d.get('received_rows'),'Com incidência':d.get('incidence_included',True)} for d in reversed(snapshots)]),hide_index=True,width='stretch')


def _cards(repo):
    from .error_cards_service import ErrorCardsService
    service=ErrorCardsService(repo);latest=service.latest_snapshot()
    if latest:st.write(f"Última captura: **{_date(latest['observed_day'])}** · {latest['tree']['total']:,} cards".replace(',','.'))
    with st.container(key='bento-updates-cards'):
        data,filename=_source('cards','Árvore dos seus flashcards de erros (HTML ou TXT)')
        day=_capture_day('Data em que você copiou a árvore','cards')
        scope=st.radio('O que os números desse arquivo representam?',list(SCOPES),format_func=SCOPES.get,index=None,key='updates_cards_scope')
        _help('cards')
        preview=_preview('cards',data,{'day':day,'scope':scope},lambda:service.preview_html(data,filename,day,scope))
        if preview:
            tree=preview['tree']
            st.subheader('Confira o novo saldo')
            st.write(f"**{tree['total']} cards · {len(tree['topics'])} temas específicos**")
            if scope=='inventory':st.info('Este arquivo ficará como inventário. O total não será tratado como atraso; o lote anterior deixará de ser a fila ativa.')
            else:st.write(f"Saldo pendente atual: {preview['current_remaining']} · Saldo após atualização: {preview['pending_after']}")
            if preview['retained_creations']:
                st.info(f"{preview['retained_creations']} cards criados depois da captura serão mantidos na fila, além dos cards do arquivo.")
            if tree['unallocated']:st.warning(f"{tree['unallocated']} cards estão em grupos sem subtemas visíveis. Expanda esses grupos na Osler para conseguir organizá-los por tema.")
            complete=True
            if preview['missing_roots']:
                st.warning('Grupos da captura anterior não aparecem neste arquivo: '+', '.join(preview['missing_roots']))
                complete=st.checkbox('Confirmo que o arquivo contém toda a fila que quero acompanhar',key='updates_cards_complete')
            _comparison(pd.DataFrame(preview['comparison']))
            with st.expander('Como o saldo é atualizado'):
                st.write('O arquivo substitui o saldo da passagem atual. Os estudos antigos continuam no histórico, sem serem descontados novamente. As criações já registradas até a captura passam a estar abrangidas pelo arquivo, para evitar soma duplicada. Confirme que a exportação já as inclui. Pais e filhos não são contados duas vezes.')
            stale=preview['token']!=service.token()
            if preview['duplicate_id']:st.info('Este arquivo já foi importado com essa finalidade. A passagem não será reiniciada.')
            if stale:st.info('Os cards ou as questões mudaram. Clique em Conferir atualização novamente.')
            if confirm_button('Atualizar cards de erros',key='updates_cards_apply',action_key='updates_cards_apply',type='primary',
                disabled=stale or bool(preview['duplicate_id']) or not complete,
                details=f"Usar a captura de {_date(day)}: {tree['total']} cards. Finalidade: {SCOPES[scope]}. O saldo anterior será substituído; registros e originais ficarão preservados."):
                try:
                    notify_success(service.import_html(data,filename,day,scope,preview['token']),'Cards de erros atualizados.')
                    st.session_state.pop('ec_recording',None)
                    st.session_state.pop('updates_cards_result',None)
                    st.session_state['updates_notice']='Cards de erros atualizados. Confira a fila em Flashcards.'
                    st.rerun()
                except (ValueError,OSError,sqlite3.Error) as exc:st.error(str(exc))
    snapshots=[r for r in service._events() if r['kind']=='error_cards.snapshot']
    if snapshots:
        with st.expander('Histórico das árvores de cards'):
            st.dataframe(pd.DataFrame([{'Captura':r['observed_day'],'Arquivo':r['filename'],'Cards':r['tree']['total'],'Finalidade':SCOPES[r['scope']]} for r in reversed(snapshots)]),hide_index=True,width='stretch')


def render_updates(repo):
    st.title('Atualizar dados')
    explain('Envie os arquivos que você copiou da Osler. Confira a prévia antes de aplicar; tudo fica no seu computador.')
    if st.session_state.get('updates_notice'):st.success(st.session_state.pop('updates_notice'))
    preserve_updates_drafts('cards' if st.session_state.get('updates_tab')=='Flashcards de erros' else 'planner')
    planner,cards=st.tabs(['Planner de questões','Flashcards de erros'],key='updates_tab',on_change='rerun')
    if planner.open:
        with planner:_planner(repo)
    if cards.open:
        with cards:_cards(repo)
