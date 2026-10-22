"""Lista pronta, exportação completa e uma declaração opcional por seleção."""
import sqlite3

import pandas as pd
import streamlit as st

from .classification import ClassifierConfig
from .exports import _safe_cell
from .planner_service import today_local
from .practical_reduction import PracticalReductionService


def _frame(topics):
    return pd.DataFrame([{'Tema': ' → '.join(t['path']), 'Respondidas no PDF': t['answered_pdf'],
                          'Acerto no PDF': t['accuracy_pdf'], 'Cartões já estudados': t['studied_cards'],
                          'Incidência': ' / '.join(s.get('native_incidence') or s['band'] for s in t['incidence']) or 'Não recebida',
                          'Sugestão': t['action']} for t in topics])


def render_practical(repo, open_tool):
    service = PracticalReductionService(repo)
    day = today_local().isoformat()
    st.title('Sua lista para diminuir as revisões')
    st.write('Use o que você já estudou e seu rendimento para começar por vários temas. A lista abaixo já está pronta; não precisa preencher cada assunto.')
    if 'practical_notice' in st.session_state:
        st.success(st.session_state.pop('practical_notice'))
    recommendations=st.container()
    with st.expander('Como os temas foram escolhidos? Ajuste se quiser'):
        daily_limit = st.select_slider('Referência de revisões por dia para comparar a carga', [80, 100, 120, 150, 200, 300, 400, 500], value=500, key='reduction_daily_target')
        st.write('Triagem inicial: pelo menos 30 respondidas no PDF, acerto registrado de 85% ou mais e 20 cartões já estudados. Esses valores são uma regra prática ajustável, não um limite validado para suspender cartões.')
        min_answers = st.select_slider('Mínimo de respondidas no relatório', [10, 20, 30, 40, 50, 75, 100], value=30)
        min_accuracy = st.select_slider('Acerto registrado a partir de', [75, 80, 85, 90, 95], value=85)
        min_cards = st.select_slider('Mínimo de cartões já estudados', [1, 10, 20, 50, 100], value=20)
        st.caption('Erros ou baixo desempenho informados prevalecem. Entre os temas selecionados, menor incidência conhecida vem primeiro; depois, maior volume estudado. Ausência de incidência não é tratada como baixa.')
    with recommendations:
        config = ClassifierConfig(**st.session_state.get('assessment_config', {})).validate()
        options = dict(config=config, min_answers=min_answers, min_accuracy=min_accuracy, min_cards=min_cards)
        view = service.overview(day, daily_limit, **options)
        topics = view['triage']
        st.subheader('Temas para começar')
        st.caption('Acerto no PDF tem tentativa não identificada e respondidas não significam questões distintas. Esta lista orienta redução seletiva dos cartões já estudados; não indica suspender o tema inteiro.')
        if topics:
            st.write(f"**{len(topics)} temas na lista**, com **{sum(t['studied_cards'] for t in topics):,} cartões já estudados nesses temas**.".replace(',', '.'))
            st.caption('Esse volume não é a quantidade indicada para suspender. Cartões para avaliar não são revisões por dia.')
            frame = _frame(topics)
            layout=st.radio('Visualização da lista',['Tabela','Lista'],horizontal=True,key='practical_layout')
            if layout=='Tabela':
                st.dataframe(frame, hide_index=True, width='stretch', height=min(520, 60+35*len(topics)),column_config={'Tema':st.column_config.TextColumn(width='large'),'Incidência':st.column_config.TextColumn(width='medium')})
                st.caption('Para ler os nomes completos em tela estreita, escolha Lista.')
            else:
                pages=(len(topics)+11)//12
                signature='-'.join(t['topic_id'] for t in topics)
                import hashlib
                page=st.number_input('Página da lista',1,pages,1,key='practical_page_'+hashlib.sha256(signature.encode()).hexdigest()[:12]) if pages>1 else 1
                for topic in topics[(page-1)*12:page*12]:
                    with st.container(border=True):
                        st.subheader(topic['path'][-1])
                        st.caption(' › '.join(topic['path'][:-1]))
                        st.write(f"{topic['studied_cards']} cartões já estudados · {topic['action']}")
            safe = frame.map(lambda value: _safe_cell(value) if isinstance(value, str) else value)
            st.download_button('Baixar minha lista completa', safe.to_csv(index=False, sep=';').encode('utf-8-sig'), 'minha_lista_reducao.csv', 'text/csv')
            st.write('**Na Osler:** comece pelos primeiros temas da lista. Preserve os cartões dos conceitos em que ainda erra ou tem dúvida e avalie reduzir os demais já estudados. Você faz as alterações manualmente; o app não acessa sua conta.')
            with st.expander('Registrar o que já fiz (opcional)'):
                lookup = {t['topic_id']: t for t in topics}
                selected = st.multiselect('Temas que você escolheu', list(lookup), format_func=lambda key: ' → '.join(lookup[key]['path']), key='practical_selection')
                done = st.button('Já fiz uma redução seletiva nesses temas', disabled=not selected)
                keep = st.button('Prefiro manter esses temas na revisão', disabled=not selected)
                if done or keep:
                    _record(service, 'aplicado' if done else 'manter', selected, day, view, options)
        else:
            st.info('Nenhum tema disponível com estes critérios e fontes. Você pode ajustar os mínimos acima ou trazer relatórios mais recentes. Registros anteriores ficam preservados.')
        latest = view['latest']
        st.caption(f"Registros opcionais: {view['applied_topics']} temas com redução seletiva declarada; {view['kept_topics']} escolhidos para manter. Nenhuma economia de revisões foi inferida.")
        if latest:
            with st.expander('Ver registros ou voltar um tema para a lista'):
                selected = st.multiselect('Temas registrados', list(latest), format_func=lambda key: ' → '.join(latest[key]['topic']['path']), key='practical_reopen')
                st.caption('Voltar para a lista só altera o registro local; não reativa cartões na Osler.')
                if st.button('Voltar estes temas para a lista', disabled=not selected):
                    _record(service, 'reabrir', selected, day, view, options)
        with st.expander('Ver a carga de revisões informada'):
            workload, comparison = view['workload'], view['comparison']
            if workload:
                st.write(f"Consulta de {workload['observed_date']}: {workload['count']:,} revisões em {workload['horizon_days']} dias.".replace(',', '.'))
                left, right = st.columns(2)
                left.metric('Média dessa consulta', f"{comparison['average']:.0f}/dia")
                right.metric('Referência escolhida', f'{daily_limit}/dia')
                st.write(f"Diferença para caber no total do período: {comparison['needed_reviews']:,} revisões.".replace(',', '.'))
                st.caption('O total pode caber e ainda haver picos. Teto diário não elimina pendências. Compare uma nova previsão com os mesmos filtros após suas mudanças para medir o efeito.')
            else:
                st.write('Não há uma contagem de revisões por período. Isso não impede usar a lista de temas.')


def render_legacy_details(repo,open_tool):
    config=ClassifierConfig(**st.session_state.get('assessment_config',{})).validate()
    view=PracticalReductionService(repo).overview(today_local().isoformat(),500,config=config)
    st.caption('Legado · lotes e avaliações anteriores. Aplicação na Osler continua manual.')
    with st.expander('Abrir lotes e avaliações detalhadas anteriores',expanded=True):
        for candidate in view['candidates']:
            st.text(candidate['path'][-1])
            st.text(f"{candidate['cards']} cartões no registro anterior")
            st.button('Acompanhar esta redução' if candidate['batch_id'] else 'Preparar esta redução', key=f"reduce_{candidate['row_id']}", on_click=open_tool,
                      args=('Planejador de Suspensões', view['sources'], candidate['batch_id'], candidate['item_id'], candidate['row_id']))


def _record(service, kind, selected, day, view, options):
    try:
        service.record(kind, selected, day, view['signature'], view['event_id'], **options)
        st.session_state.pop('practical_selection', None)
        st.session_state.pop('practical_reopen', None)
        st.session_state['practical_notice'] = 'Registro salvo. A lista foi atualizada sem alterar seus relatórios.'
        st.rerun()
    except (ValueError, sqlite3.Error) as exc:
        st.error(str(exc))
