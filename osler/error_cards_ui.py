"""Recuperação do lote pessoal; decisões curtas e detalhes acessíveis."""
from datetime import date
import math
import uuid
import pandas as pd
import streamlit as st

from .error_cards import parse_error_cards
from .error_cards_service import ErrorCardsService
from .planner_service import today_local


def _n(n):return f'{n:,}'.replace(',','.')
def _date(day):return date.fromisoformat(day).strftime('%d/%m/%Y')

def _load_label(view):return f"referência {view['budget']}/dia" if view['budget'] else 'passagem automática pausada'


def open_error_cards():
    st.session_state['main_view']='Diminuir revisões';st.session_state['ec_mode']='Erros acumulados'


def render_cards_summary(repo,question_view,day=None):
    service=ErrorCardsService(repo)
    today=today_local().isoformat();day=day or today
    view=service.overview(today,question_view=question_view)
    if not view['snapshot'] and not view['has_queue'] and not view['history']:return
    with st.container(border=True):
        if day==today:
            st.markdown(f"**Cards de erros · {view['done_today']} respostas hoje · {_load_label(view)}**")
            st.caption(f"{sum(t['planned'] for t in view['items'])} cards na próxima passagem · separados das questões.")
        elif day<today:
            done=sum(r['covered']+r['repeats'] for r in view['history'] if r['day']==day)
            st.markdown(f'**Cards de erros · {done} respostas registradas em {_date(day)}**')
        else:
            horizon=min(548,max(1,(date.fromisoformat(day)-today_local()).days+1))
            forecast=service.forecast(view,horizon)
            row=next((r for r in forecast['days'] if r['date']==day),None)
            if row:
                st.markdown(f"**Cards de erros · {row['cards']} previstos em {_date(day)}**")
                st.caption('Cenário de primeira passagem: '+(' · '.join(t['path'][-1] for t in row['items'][:4]) or row['reason']))
            else:st.caption('Cards de erros: sem nova primeira passagem prevista neste cenário.')
        st.button('Abrir meu plano de cards',key='ec_open_'+day,on_click=open_error_cards)


def render_flashcards(repo):
    with st.container(key='study_navigation'):
        mode=st.radio('Flashcards',['Erros acumulados','Reduzir outras revisões'],horizontal=True,key='ec_mode',label_visibility='collapsed',width='stretch')
    if mode=='Reduzir outras revisões':
        from .reduction_ui import render_reduction
        render_reduction(repo)
    else:render_error_cards(repo)


def _start_record(item,token):
    st.session_state['ec_recording']={'topic_id':item['topic_id'],'path':item['path'],'remaining':item['remaining'],'planned':item['planned'],'token':token,'key':uuid.uuid4().hex}
    for k in ['ec_covered','ec_repeats','ec_recalled','ec_include_recalled','ec_record_day']:st.session_state.pop(k,None)


def _record(service,view):
    item=st.session_state.get('ec_recording')
    if not item:return
    if item['token']!=view['token']:
        st.warning('A fila mudou depois que este formulário foi aberto. Confira o saldo atualizado e abra o tema novamente.')
        if st.button('Fechar registro desatualizado'):
            st.session_state.pop('ec_recording',None);st.rerun()
        return
    st.subheader('Registrar cards · '+item['path'][-1]);st.caption(' › '.join(item['path'][:-1]))
    with st.form('ec_record'):
        if item['remaining']:
            covered=st.number_input('Cards diferentes deste lote que você respondeu agora',0,item['remaining'],min(item['planned'],item['remaining']),key='ec_covered')
        else:
            covered=0;st.write('Primeira passagem deste tema já registrada. Informe somente as repetições.')
        st.caption('Conte cada card uma vez na primeira passagem. Se ele reaparecer depois, registre como repetição.')
        repeats=st.number_input('Respostas repetidas a cards já registrados',0,5000,10 if not item['remaining'] else 0,key='ec_repeats')
        with st.expander('Repetições e lembrança (opcional)'):
            include=st.checkbox('Também anotei quantas respostas lembrei antes de virar',key='ec_include_recalled')
            recalled=st.number_input('Respostas lembradas antes de virar',0,5000,0,key='ec_recalled')
        day=st.date_input('Dia de estudo (encerra às04h)',value=today_local(),min_value=date.fromisoformat(view['queue_start']),max_value=today_local(),key='ec_record_day',format='DD/MM/YYYY')
        save=st.form_submit_button('Salvar bloco de cards',type='primary')
    if st.button('Cancelar registro de cards'):st.session_state.pop('ec_recording',None);st.rerun()
    if save:
        try:
            service.record(item['topic_id'],day.isoformat(),int(covered),int(repeats),int(recalled) if include else None,item['key'],item['token'])
            st.session_state.pop('ec_recording',None)
            st.session_state['ec_notice']=f'{covered} cards diferentes registrados; {repeats} repetições. Confira os conceitos que não lembrou e siga os retornos da Osler. A primeira passagem não comprova domínio.'
            st.rerun()
        except ValueError as exc:st.error(str(exc))


def _today(service,view):
    if not view['active']:
        st.info('Seu arquivo está guardado como inventário. Importe somente os pendentes ou escolha Nova passagem por todos em Importar e ajustar. Não presumimos atraso no acervo inteiro.' if view['snapshot'] else 'Não há cards disponíveis na fila atual. Os estudos que você já registrou continuam abaixo.')
    if not view['budget']:st.info('A passagem automática pelos cards está pausada. A fila e seus registros ficam guardados. Use Temas para estudar um deck por conta própria ou ajuste apenas um dia quando houver espaço na rotina.' if not view['settings']['daily'] else view['budget_reason']+'. Nenhuma carga automática de cards hoje; você pode ajustar apenas este dia.')
    items=view['items']
    if items:
        st.markdown(f"**{sum(t['planned'] for t in items)} cards em {len(items)} {'deck inteiro' if len(items)==1 else 'decks inteiros'} para fazer**")
        st.caption(f"Referência de {view['budget']} cards/dia, com até10% de margem para completar um deck. A meta não é preenchida com fragmentos de outros decks.")
    oversized=[t for t in view['ranked'] if t.get('oversized')]
    if view['budget'] and oversized:st.info('Decks acima da referência e da margem: '+', '.join(t['path'][-1]+f" ({t['remaining']})" for t in oversized[:3])+'. Para fazê-los inteiros, aumente a referência de um dia em Importar e ajustar ou escolha o deck em Temas.')
    if not items and view['budget'] and view['active']:st.info('Nenhum novo bloco de primeira passagem hoje. Os registros abaixo e os retornos da Osler continuam disponíveis.')
    if len(items)>12:
        page=st.number_input('Página dos blocos de cards',1,math.ceil(len(items)/12),1,key='ec_today_page')
        items=items[(page-1)*12:page*12]
    for i,item in enumerate(items):
        with st.container(border=True,key='error_cards_block_'+item['topic_id']):
            st.subheader(item['path'][-1]);st.caption(' › '.join(item['path'][:-1]))
            st.markdown(f"**{item['planned']} {'card' if item['planned']==1 else 'cards'}** · Prioridade {item['priority'].lower()} · Saldo do lote: {item['remaining']}")
            st.button('Registrar cards deste tema',key='ec_start_'+item['topic_id'],type='primary' if i==0 else 'secondary',on_click=_start_record,args=(item,view['token']))
            with st.expander('Por que este deck?'):
                st.caption('Concluir o deck iniciado hoje.' if item.get('in_progress_today') else 'Deck inteiro deste tema; faça pausas se precisar.')
                st.write(item['reason'])
    st.subheader('Feito neste dia de estudo')
    done=[r for r in view['history'] if r['day']==today_local().isoformat()]
    if not done:st.caption('Nenhum bloco de cards registrado hoje.')
    for r in reversed(done):
        st.write(f"{r['path'][-1]} · {r['covered']} diferentes + {r['repeats']} repetições")
        if r['recalled'] is not None:st.caption(f"Lembrados antes de virar: {r['recalled']} de {r['covered']+r['repeats']} respostas. Não é acerto em questões.")
        if st.button('Desfazer este registro',key='ec_undo_'+str(r['id'])):
            try:service.undo(r['id'],view['token']);st.rerun()
            except ValueError as exc:st.error(str(exc))


def _topics(view):
    if not view['active'] and not view['snapshot']:
        st.info('A fila atual está vazia. O histórico de cards realizados permanece em Hoje.');return
    query=st.text_input('Buscar tema de cards',placeholder='Ex.: diverticulite, trauma, hanseníase',key='ec_search').casefold().strip()
    topics=view['ranked'] if view['active'] else [{**t,'remaining':t['count'],'priority':'Inventário','reason':'Pendência não confirmada'} for t in view['snapshot']['tree']['topics']]
    if view['active']:
        missing={t['topic_id'] for t in topics}
        topics=[*topics,*[{**t,'remaining':0,'priority':'Primeira passagem registrada','reason':'Retornos individuais continuam na Osler'} for t in view['topics'] if t['topic_id'] not in missing]]
    topics=[t for t in topics if query in ' › '.join(t['path']).casefold()]
    layout=st.radio('Ver temas de cards',['Lista','Tabela'],horizontal=True,key='ec_layout')
    st.caption(f'{len(topics)} temas específicos nesta busca. Pais e filhos não são somados.')
    if layout=='Tabela':
        st.dataframe(pd.DataFrame([{'Tema':t['path'][-1],'A realizar nesta passagem':t['remaining'],'Prioridade':t['priority'],'Caminho':' › '.join(t['path'])} for t in topics]),hide_index=True,width='stretch')
    else:
        pages=max(1,math.ceil(len(topics)/12));key='ec_topics_page_'+str(len(topics))
        page=st.number_input('Página dos temas',1,pages,1,key=key) if pages>1 else 1
        for t in topics[(page-1)*12:page*12]:
            st.markdown('**'+t['path'][-1]+'**');st.caption(' › '.join(t['path'][:-1]))
            st.write(f"{t['remaining']} cards · {t['priority']}")
            if view['active']:st.button('Estudar este tema de cards',key='ec_manual_'+t['topic_id'],on_click=_start_record,args=({**t,'planned':t['remaining']},view['token']))
    if view['unallocated']:
        with st.expander(f"{view['unallocated']} cards ainda sem subtema visível"):
            for r in view['snapshot']['tree']['unresolved']:st.write(' › '.join(r['path'])+f" · {r['count']} cards · {r['reason']}")
            st.caption('Expanda esses grupos e envie a árvore completa novamente. Não distribuímos seus cards entre filhos por estimativa.')


def _forecast(service,view):
    st.subheader('Primeira passagem pelos próximos dias')
    st.caption('Cenário a carga constante, sem novos cards e sem contabilizar retornos individuais da Osler. Não é previsão de domínio nem de fim de todas as revisões.')
    if not view['settings']['daily'] and not any(view['settings']['days'].values()):
        st.info('A passagem pelos cards está pausada. Sua fila fica guardada; ajuste a carga ou reserve um dia quando houver espaço na rotina.');return
    forecast=service.forecast(view,548)
    if forecast['completion']:st.write('Primeira passagem dos temas identificados: **'+_date(forecast['completion'])+'**, se este cenário for cumprido.')
    elif forecast['days']:st.write(f"Ainda restariam {forecast['remaining']} cards identificados ao fim do período de preparação neste cenário.")
    if view['unallocated']:st.caption(f"Ficam fora dessa data os {view['unallocated']} cards sem subtema visível.")
    if not forecast['days']:return
    rows=[{'Data':_date(r['date']),'Cards previstos':r['cards'],'Saldo da primeira passagem':r['remaining'],
           'Temas específicos':' · '.join(t['path'][-1]+' ('+str(t['planned'])+')' for t in r['items']) or r['reason']} for r in forecast['days']]
    frame=pd.DataFrame(rows)
    st.dataframe(frame.head(14),hide_index=True,width='stretch')
    st.download_button('Baixar cenário completo de cards',frame.map(lambda v:"'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v).to_csv(index=False,sep=';').encode('utf-8-sig'),'cenario-cards-erros.csv','text/csv')


def _import_and_settings(service,view):
    st.subheader('Trazer ou atualizar a fila')
    upload=st.file_uploader('HTML da árvore de cards de erros',type=['html','htm','txt'],key='ec_upload')
    with st.expander('Prefiro colar o HTML'):
        pasted=st.text_area('HTML completo do container da árvore',key='ec_pasted')
    data=upload.getvalue() if upload else pasted.encode('utf-8') if pasted.strip() else None
    if data:
        try:
            tree=parse_error_cards(data.decode('utf-8-sig'))
            st.write(f"Prévia: **{_n(tree['total'])} cards**, {len(tree['topics'])} temas específicos e {tree['unallocated']} cards sem subtema visível. Pais não entram duas vezes.")
            scope=st.radio('O que esse arquivo representa?',['pending','inventory','pass'],format_func={'pending':'Somente não estudados ou pendentes','inventory':'Todos os criados, incluindo já revisados','pass':'Quero uma nova passagem por todos os cards deste arquivo'}.get,key='ec_scope')
            observed=st.date_input('Dia de estudo do retrato (vira às04h)',value=today_local(),max_value=today_local(),key='ec_observed',format='DD/MM/YYYY')
            st.caption('Um novo retrato substitui o saldo atual e passa a abranger as criações já registradas até esse dia. Elas não serão somadas outra vez. Confira se o arquivo já inclui esses cards. Registros e originais ficam guardados; uma cópia idêntica não reinicia a passagem.')
            if st.button('Importar esta árvore de cards',type='primary'):
                service.import_html(data,upload.name if upload else 'arvore-colada.html',observed.isoformat(),scope,view['token'])
                st.session_state.pop('ec_recording',None);st.session_state['ec_notice']='Árvore importada. Confira o plano na aba Hoje.';st.rerun()
        except (ValueError,UnicodeError) as exc:st.error(str(exc))
    st.subheader('Carga que cabe na sua rotina')
    st.caption('Esta é uma parte da sua capacidade total de flashcards, junto dos retornos da Osler. Não some esta carga por cima do seu limite de revisões. Com muitos retornos, zero pausa novas passagens sem perder a fila.')
    with st.form('ec_settings'):
        daily=st.number_input('Cards de erros por dia',0,2000,view['settings']['daily'],step=10)
        st.caption('Referência separada das questões, com até10% de margem para fechar decks inteiros. Descansos e simulados ficam sem carga automática; os retornos individuais continuam na Osler.')
        save=st.form_submit_button('Salvar carga de cards')
    if save:
        try:service.configure(int(daily),view['settings']['days'],view['token']);st.rerun()
        except ValueError as exc:st.error(str(exc))
    with st.expander('Ajustar somente um dia'):
        with st.form('ec_day_settings'):
            selected=st.date_input('Dia para ajustar os cards',value=today_local(),min_value=today_local(),key='ec_day_override',format='DD/MM/YYYY')
            amount=st.number_input('Referência de cards nesse dia (zero para pausar)',0,2000,view['settings']['daily'],key='ec_day_amount')
            reset=st.checkbox('Voltar à carga automática nesse dia')
            save_day=st.form_submit_button('Atualizar esse dia de cards')
        if save_day:
            days=dict(view['settings']['days']);days.pop(selected.isoformat(),None) if reset else days.update({selected.isoformat():int(amount)})
            try:service.configure(view['settings']['daily'],days,view['token']);st.rerun()
            except ValueError as exc:st.error(str(exc))
    if view['snapshot']:
        with st.expander('Fonte, prioridades e limites do cálculo'):
            snapshot=view['snapshot'];st.write(f"{snapshot['filename']} · retrato de {_date(snapshot['observed_day'])} · total {_n(snapshot['tree']['total'])}")
            for source in snapshot.get('supplements',[]):st.caption('Subtemas completados com o print preservado: '+source['filename'])
            for t in snapshot['tree']['topics']:
                if len(t.get('source_paths',[]))>1:st.write('Grafias conciliadas: '+' / '.join(p[-1] for p in t['source_paths'])+f" · {t['count']} cards; contagens originais preservadas.")
            st.caption('A ordem combina incidência conhecida, acertos/erros com suavização estatística, tempo desde registro de cards e conexão com as questões de hoje. Dados ausentes recebem peso neutro. Convicção não é convertida em acerto. Pesos são uma política de triagem, sem validação como dose ótima.')
            st.caption('Não conhecemos IDs, vencimentos e estabilidade de memória de cada card. A data do arquivo não é contato; o app organiza a primeira passagem e não substitui o algoritmo individual da Osler.')
            st.markdown('[Evidência sobre recuperação e espaçamento](https://pubmed.ncbi.nlm.nih.gov/37615780/)')
            st.write(f"{len(service.history())} registros de cards preservados, incluindo os desfeitos. Nenhum é somado às questões.")


def render_error_cards(repo):
    service=ErrorCardsService(repo);view=service.overview()
    st.title('Seus cards de erros')
    st.caption('Uma passagem viável pelo que você criou, em temas específicos. As questões continuam no seu plano habitual.')
    if 'ec_notice' in st.session_state:st.success(st.session_state.pop('ec_notice'))
    show_queue=bool(view['snapshot'] or view['has_queue'] or view['history'])
    if show_queue:
        with st.container(key='error_cards_summary'):
            a,b,c=st.columns(3)
            a.metric('Respostas em cards hoje',_n(view['done_today']))
            b.metric('Cards ainda nesta passagem',_n(view['remaining']))
            c.metric('Referência de cards por dia',_n(view['budget']))
            if view['active']:st.progress(view['covered']/max(1,view['total_cards']))
            with st.expander('Entender o saldo e a carga'):
                st.caption('Respostas de hoje incluem cards diferentes e repetições. O saldo conta só os cards identificados ainda sem primeira passagem registrada.')
                st.caption(_load_label(view)+'. Esta carga faz parte da sua capacidade total de flashcards, junto dos retornos da Osler.')
                st.caption('Progresso deste lote; as revisões continuam na Osler. Repetições contam na carga diária e não reduzem novamente o saldo de cards diferentes.')
                if view['created_cards']:st.caption(f"{view['created_cards']} cards acrescentados pelos blocos de questões, sem alterar a carga diária.")
            if view['unreconciled_covered']:st.warning(f"{view['unreconciled_covered']} cards já estudados ficaram sem saldo correspondente após uma correção. O estudo foi preservado e não foi descontado de outros temas. Confira os lançamentos em Registrar.")
            if view['unallocated']:st.caption(f"Total importado: {_n(view['snapshot']['tree']['total'])} cards · {view['unallocated']} aguardam abertura dos grupos para revelar os subtemas.")
    if st.session_state.get('ec_recording'):
        with st.container(key='bento-error-cards-record'):
            _record(service,view)
    today,topics,forecast,settings=st.tabs(['Hoje','Temas','Próximos dias','Importar e ajustar'])
    with today:
        if show_queue:_today(service,view)
        else:st.info('Informe os flashcards criados ao registrar suas questões, ou envie o HTML da árvore em Importar e ajustar. Pais e filhos não entram duas vezes.')
    with topics:
        if show_queue:_topics(view)
    with forecast:
        if show_queue:_forecast(service,view)
    with settings:
        with st.container(key='bento-error-cards-settings'):
            _import_and_settings(service,view)
