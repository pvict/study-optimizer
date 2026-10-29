"""Lista pronta, exportação completa e uma declaração opcional por seleção."""
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

from .classification import ClassifierConfig
from .exports import _safe_cell
from .planner_service import today_local
from .practical_reduction import PracticalReductionService


def _date_label(value):return date.fromisoformat(value).strftime('%d/%m/%Y')

def _pct(value):return f'{value:.1f}%'.replace('.',',')


def _frame(topics):
    return pd.DataFrame([{'Tema': ' → '.join(t['path']), 'Respondidas no PDF': t['answered_pdf'],
                          'Acerto no PDF': t['accuracy_pdf'], 'Cartões já estudados': t['studied_cards'],
                          'Incidência': ' / '.join(s.get('native_incidence') or s['band'] for s in t['incidence']) or 'Não recebida',
                          'Sugestão': t['action']} for t in topics])


def _current_frame(topics):
    return pd.DataFrame([{'Tema': ' → '.join(t['path']),
                          'Orientação': 'Manutenção seletiva' if t['recommendation'] == 'manutencao_seletiva' else 'Pausa seletiva por capacidade' if t['recommendation'] == 'pausa_capacidade' else 'Manter na revisão' if t['recommendation'] == 'proteger' else 'Evidência insuficiente',
                          'Motivo': ' '.join(t['reasons']),
                          'Reavaliar em': t.get('review_on') if t['recommendation'] in {'manutencao_seletiva', 'pausa_capacidade'} else None,
                          'PDF': t['evidence_dates']['pdf'],
                          'Observações': ', '.join(t['evidence_dates']['manual']),
                          'Segurança acumulada': t['evidence_dates']['safety'],
                          'Blocos': ', '.join(t['evidence_dates']['blocks'])} for t in topics])


def reduction_summary(repo, view, day):
    """Três fontes descritivas, sem inferir cartões suspensos ou carga poupada."""
    from .planning_service import PlanningService
    source=view['sources']['reports']['flashcards']
    report=repo.get_report(source['sha256']) if source else None
    topics=view.get('all_suggestions',[])
    counts=[t.get('studied_cards') for t in topics]
    measurements=[m for m in PlanningService(repo).measurements()
                  if m['kind']=='revisoes_periodo' and m['observed_date']<=day]
    workload=max(measurements,key=lambda m:(m['observed_date'],m['id']),default=None)
    return {'studied':report.summary.get('estudados') if report else None,
            'studied_date':source['report_date'] if source else None,
            'review_cards':sum(counts) if counts and all(n is not None for n in counts) else None,
            'reviews_per_day':workload['count']/workload['horizon_days'] if workload else None,
            'workload':workload}


def render_practical(repo, open_tool):
    service = PracticalReductionService(repo)
    day = today_local().isoformat()
    st.title('Sua lista para diminuir as revisões')
    st.write('Comece pelos temas de menor retorno com evidência atual. As mudanças na Osler continuam manuais.')
    if 'practical_notice' in st.session_state:
        st.success(st.session_state.pop('practical_notice'))
    try:
        view = service.current_overview(day)
    except (ValueError, sqlite3.Error) as exc:
        st.error(str(exc))
        return
    summary=reduction_summary(repo,view,day)
    with st.container(key='bento-reduction-summary'):
        a,b,c=st.columns(3)
        a.metric('Cartões já estudados','—' if summary['studied'] is None else f"{summary['studied']:,}".replace(',','.'))
        a.caption('Total declarado no PDF de '+_date_label(summary['studied_date']) if summary['studied_date'] else 'Sem total declarado no PDF.')
        b.metric('Cartões para avaliar','—' if summary['review_cards'] is None else f"{summary['review_cards']:,}".replace(',','.'))
        b.caption('Estudados nos temas sugeridos; não significa suspensão do deck inteiro.')
        c.metric('Revisões por dia','—' if summary['reviews_per_day'] is None else f"{summary['reviews_per_day']:.1f}".replace('.',','))
        workload=summary['workload']
        c.caption(f"{'Consulta aproximada' if workload.get('approximate') else 'Consulta'} de {_date_label(workload['observed_date'])}: {workload['count']} em {workload['horizon_days']} dias. Fonte: {workload['source']}. Não inclui erros futuros." if workload else 'Sem contagem de revisões por período informada.')
    st.subheader('Sugestões com os dados atuais')
    st.caption('Preserve High Yield e os conceitos em que ainda erra. A indicação é seletiva; os dados não identificam quais cartões são High Yield nem comprovam que o deck inteiro pode ser suspenso.')
    topics = view['suggestions']
    if topics:
        for topic in topics:
            with st.container(key='bento-reduction-topic-'+topic['topic_id']):
                st.subheader(topic['path'][-1])
                st.caption(' › '.join(topic['path'][:-1]))
                st.write('**Manutenção seletiva**' if topic['recommendation'] == 'manutencao_seletiva' else '**Pausa seletiva por capacidade · 7 dias**')
                if topic['evidence_kind'] == 'objetiva':
                    st.write(f"{_pct(topic['exact_accuracy_pct'])} de acerto em {topic['objective_n']} questões com contagem exata, em pelo menos dois dias.")
                    st.caption(f"Limite inferior Wilson 95%: {_pct(topic['wilson_lower_pct'])}. Não é probabilidade de aprovação.")
                else:
                    st.write(f"Segurança acumulada de {_pct(topic['safety_pct'])} em {topic['safety_n']} questões distintas. É um indício indireto para aliviar a carga; não é taxa de acerto nem domínio comprovado.")
                st.caption(f"Incidência relativa: {_pct(topic['incidence_strength']*100)} do maior sinal conhecido. Reavalie em {_date_label(topic['review_on'])} ou antes se surgirem erros.")
        with st.expander('Registrar uma ação que já fiz (opcional)'):
            lookup = {t['topic_id']: t for t in view['all_suggestions']}
            selected = st.multiselect('Temas em que você já fez a mudança', list(lookup),
                                      format_func=lambda key: ' → '.join(lookup[key]['path']), key='current_reduction_selection')
            st.caption('O registro é local. O app não suspende nem reativa cartões na Osler.')
            if st.button('Já fiz essa redução seletiva na Osler', disabled=not selected):
                _record_current(service, 'aplicado', selected, day, view)
            if st.button('Escolhi manter esses temas na revisão', disabled=not selected):
                _record_current(service, 'manter', selected, day, view)
    else:
        st.info('Sem nova sugestão justificável agora. Faltam evidências atuais suficientes ou há sinais que pedem manter a revisão. PDF e percentual revisado, sozinhos, não autorizam uma pausa.')
    if view['reevaluate']:
        st.subheader('Reavaliar pausas anteriores')
        st.write('O prazo chegou ou surgiu um sinal de atenção. Confira esses temas e reabra a revisão na Osler quando necessário; não há reativação automática.')
        for topic in view['reevaluate']:
            st.write(f"**{' → '.join(topic['path'])}** — {' '.join(topic['reasons'])}")
    with st.expander(f"Temas protegidos · {len(view['protected'])}"):
        if view['protected']:
            st.dataframe(_current_frame(view['protected']).drop(columns=['Reavaliar em']), hide_index=True, width='stretch')
        else:
            st.write('Nenhum sinal atual de proteção encontrado. Isso não comprova domínio dos demais temas.')
    with st.expander('Lista completa e temas com evidência insuficiente'):
        complete = [*view['all_suggestions'], *view['conditional'], *view['protected']]
        if complete:
            frame = _current_frame(complete)
            st.dataframe(frame, hide_index=True, width='stretch')
            safe = frame.map(lambda value: _safe_cell(value) if isinstance(value, str) else value)
            st.download_button('Baixar avaliação atual completa', safe.to_csv(index=False, sep=';').encode('utf-8-sig'), 'reducao_atual.csv', 'text/csv')
        else:
            st.write('Os demais temas estão protegidos ou já têm uma escolha registrada.')
    with st.expander('Fontes, critérios e histórico'):
        st.write(f"Leitura de {view['date']}; janela recente de {view['recent_days']} dias. Cards criados nos últimos 14 dias protegem o tema.")
        for kind, label in [('qbank', 'PDF de questões'), ('flashcards', 'PDF de cartões')]:
            source = view['sources']['reports'][kind]
            st.caption(f"{label}: {source['report_date']} · {source['sha256'][:12]}" if source else f'{label}: não recebido.')
        for source in view['sources']['incidence']:
            st.caption(f"Incidência: {' / '.join(source['institutions'])} · {source['observed_date']}")
        st.caption('Baixa incidência significa até 15% do maior sinal conhecido. Este corte e a pausa de sete dias são regras operacionais, não limites científicos universais. Não calculamos revisões por dia economizadas.')
        st.caption('Segurança acumulada e convicção ficam separadas do acerto objetivo. A data do PDF não é data de contato.')
        for topic in topics:
            dates = topic['evidence_dates']
            if dates['manual'] or dates['safety'] or dates['blocks']:
                st.caption(f"{' → '.join(topic['path'])} · observações: {', '.join(dates['manual']) or 'não recebidas'}; segurança: {dates['safety'] or 'não recebida'}; blocos: {', '.join(dates['blocks']) or 'não registrados'}")
        if view['legacy_history']:
            st.write('Aplicações manuais já registradas nos lotes anteriores:')
            st.dataframe(pd.DataFrame([{'Tema': ' → '.join(item['path']), 'Aplicado em': item['day'],
                                        'Reavaliar em': item['review_on'], 'Lote anterior': item['planner_batch_id']}
                                       for item in view['legacy_history']]), hide_index=True, width='stretch')
        if view['history'] or view['legacy_history']:
            labels = {'aplicado': 'redução seletiva declarada', 'manter': 'manter na revisão', 'reabrir': 'voltar para a lista'}
            for event in reversed(view['history']):
                st.write(f"{event['day']} · {labels[event['kind']]} · {len(event['topics'])} tema(s)")
            latest = view['latest']
            selected = st.multiselect('Voltar temas registrados para a lista local', list(latest),
                                      format_func=lambda key: ' → '.join(latest[key]['topic']['path']), key='current_reduction_reopen')
            st.caption('Voltar à lista local preserva o histórico. A reativação de cartões na Osler continua manual.')
            if st.button('Voltar estes temas para a avaliação atual', disabled=not selected):
                _record_current(service, 'reabrir', selected, day, view)
        else:
            st.write('Nenhuma ação manual registrada.')
    with st.expander('Triagem anterior por PDF e recursos legados'):
        st.caption('Consulta anterior com critérios ajustáveis. A leitura atual acima tem precedência para decidir uma redução.')
        _render_documentary_details(repo, open_tool)


def _record_current(service, kind, selected, day, view):
    try:
        service.record_current(kind, selected, day, view['signature'], view['event_id'])
        st.session_state.pop('current_reduction_selection', None)
        st.session_state.pop('current_reduction_reopen', None)
        st.session_state['practical_notice'] = 'Registro salvo. A avaliação atual e o histórico foram atualizados.'
        st.rerun()
    except (ValueError, sqlite3.Error) as exc:
        st.error(str(exc))


def _render_documentary_details(repo, open_tool):
    service = PracticalReductionService(repo)
    day = today_local().isoformat()
    st.subheader('Triagem anterior por PDF')
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
