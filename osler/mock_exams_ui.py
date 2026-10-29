"""Registro curto de simulados e detalhes opcionais, separado dos blocos de estudo."""
from dataclasses import replace
from datetime import date, timedelta
from html import escape

import pandas as pd
import streamlit as st

from .exam_goals import ExamGoals
from .bento import area_slug, bar
from .classification import wilson_interval
from .mock_exams import MockExam, MockExams, convert_to_entries, retract_conversion
from .models import normalize_path
from .planner_service import today_local
from .study_models import AdaptiveProfile


def _display_number(value):
    return f'{value:g}'.replace('.', ',')


def _summary(exam):
    """Valores informados, sem inferir nota a partir do percentual de acertos."""
    score, maximum = exam.get('score'), exam.get('max_score')
    return {
        'name': exam['name'],
        'date': date.fromisoformat(exam['day']).strftime('%d/%m/%Y'),
        'duration': '—' if exam.get('minutes_used') is None else _display_number(exam['minutes_used'])+' min',
        'score': '—' if score is None or maximum is None else f'{_display_number(score)} / {_display_number(maximum)}',
        'accuracy': f"{exam['correct']} / {exam['questions']} · {100*exam['correct']/exam['questions']:.1f}% · n={exam['questions']}".replace('.', ','),
    }


def _summary_html(exam):
    summary = _summary(exam)
    fields = [('Data', 'date'), ('Duração informada', 'duration'),
              ('Acertos / questões', 'accuracy'), ('Nota / escala informada', 'score')]
    return ('<h3 class="o-mock-name">'+escape(summary['name'])+'</h3><dl class="o-mock-summary">'
            + ''.join(f'<div><dt>{label}</dt><dd>{escape(summary[key])}</dd></div>' for label, key in fields)+'</dl>')


def _area_results_html(areas):
    rows = []
    for area in areas:
        total, correct = area['questions'], area['correct']
        percent = 100*correct/total
        low, high = wilson_interval(percent, total)
        name = escape(area['area'])
        result = f'{correct} / {total} · {percent:.1f}% · n={total}'.replace('.', ',')
        interval = f'Faixa Wilson 95%: {low:.1f}–{high:.1f}%'.replace('.', ',')
        rows.append(f'<div class="o-mock-area"><div class="o-mock-area-label"><strong>{name}</strong>'
                    f'<span>{result}</span></div>'+bar(percent/100, area_slug([area['area']]), label=area['area']+': '+result)
                    + f'<p class="o-mock-area-range">{interval}</p></div>')
    return ''.join(rows)


def _render_summary(exam, targets):
    summary, areas = st.columns([3, 2])
    with summary, st.container(key='bento-mock-summary'):
        st.subheader('Último simulado')
        st.html(_summary_html(exam))
        _comparison(exam, targets)
    with areas, st.container(key='bento-mock-areas'):
        st.subheader('Por área')
        if exam['areas']:
            st.html(_area_results_html(exam['areas']))
            st.caption('Faixa descritiva de incerteza pelo método Wilson (95%). Questões podem não ser independentes; não é previsão de nota ou aprovação.')
        else:
            st.caption('Sem resultado por área informado neste simulado.')


def _reset(row=None):
    for key in list(st.session_state):
        if key.startswith('mock_field_'): st.session_state.pop(key, None)
    if row: st.session_state['mock_editing'] = row
    else: st.session_state.pop('mock_editing', None)


def _table(rows, identity, label):
    return pd.DataFrame([{label: ' → '.join(r[identity]) if identity=='path' else r[identity],
                          'Questões': r['questions'], 'Acertos': r['correct']} for r in rows],
                        columns=[label, 'Questões', 'Acertos'])


def _details(table, identity, label):
    rows = []
    for record in table.to_dict('records'):
        if all(pd.isna(value) or value=='' for value in record.values()): continue
        name = record[label]
        if not isinstance(name, str) or not name.strip(): raise ValueError('Preencha o nome de cada área ou tema.')
        counts = []
        for field in ('Questões', 'Acertos'):
            value = record[field]
            if pd.isna(value) or isinstance(value, bool) or float(value)!=int(value):
                raise ValueError('Preencha questões e acertos inteiros em cada linha.')
            counts.append(int(value))
        path = [p.strip() for p in name.replace('>>', '→').split('→') if p.strip()]
        rows.append({identity: path if identity=='path' else name.strip(), 'questions': counts[0], 'correct': counts[1]})
    return rows


def _comparison(exam, targets):
    target = next((r['target'] for r in targets if r['target_id']==exam.get('target_id')), None)
    if not target or not exam.get('institution') or normalize_path([exam['institution']])!=normalize_path([target['institution']]):
        return
    cutoff = 100*target['cutoff_score']/target['max_score']
    st.info(f"Corte informado: {cutoff:.1f}% · {target['institution']}. Fonte: {target['cutoff_source']}")
    if exam.get('score') is not None and exam.get('max_score'):
        percentage = 100*exam['score']/exam['max_score']
        st.caption(f'Nota informada no simulado: {percentage:.1f}%. Diferença para a referência: {percentage-cutoff:+.1f} pontos percentuais. Escalas e pesos podem diferir.')
    else:
        st.caption('Sem nota e nota máxima informadas, o acerto das questões não é comparado ao corte ponderado.')


def _history(mocks):
    events = mocks.events()
    if not events: return
    with st.expander('Histórico de versões dos simulados'):
        st.dataframe(pd.DataFrame([{'Data': r['exam']['day'], 'Nome': r['exam']['name'], 'Versão': r['version'],
                                    'Ação': 'Salvo' if r['action']=='save' else 'Desconsiderado', 'Registrado em': r['created_at']} for r in events]), hide_index=True, width='stretch')


def render_mock_exams(service):
    from .mock_schedule_ui import render_mock_schedule
    from .exam_practice_ui import render_area_practice,render_mock_correction
    programming,results,practice,correction=st.tabs(['Programação','Resultados','Treinos por área','Correção'])
    with programming: render_mock_schedule(service)
    with results: _render_mock_results(service)
    with practice: render_area_practice(service)
    with correction: render_mock_correction(service)


def _render_mock_results(service):
    mocks = MockExams(service.repository)
    rows = mocks.active()
    targets = ExamGoals(service.repository).active()
    if st.session_state.pop('mock_reset_pending', False): _reset()
    st.caption('Um simulado não é a prova real; bancas diferem. Os resultados ficam separados dos PDFs e dos blocos registrados. Não representam probabilidade de aprovação.')
    notice = st.session_state.pop('mock_notice', None)
    if notice: st.success(notice)
    if rows:
        _render_summary(rows[-1]['exam'], targets)
    else:
        with st.container(key='bento-mock-empty'):
            st.info('Registre seu primeiro simulado com data, total e acertos. Os detalhes podem ficar para depois.')
    edit = st.session_state.get('mock_editing')
    initial = edit['exam'] if edit else MockExam(today_local().isoformat(), 100, 0).to_dict()
    with st.container(key='bento-mock-form'):
        st.subheader('Corrigir simulado' if edit else 'Registrar simulado')
        with st.form('mock_form'):
            name = st.text_input('Nome', value=initial['name'], key='mock_field_name')
            day = st.date_input('Data', value=date.fromisoformat(initial['day']), max_value=today_local(), key='mock_field_day')
            total = st.number_input('Total de questões', min_value=1, max_value=1000000, value=initial['questions'] if edit else None, step=1, key='mock_field_questions')
            correct = st.number_input('Acertos', min_value=0, max_value=1000000, value=initial['correct'] if edit else None, step=1, key='mock_field_correct')
            with st.expander('Detalhes opcionais: prova, tempo, áreas e temas'):
                kind = st.selectbox('Tipo', ['outro', 'prova_anterior', 'simulado_cursinho'],
                                    index=['outro', 'prova_anterior', 'simulado_cursinho'].index(initial['kind']),
                                    format_func=lambda v: {'outro': 'Outro', 'prova_anterior': 'Prova anterior', 'simulado_cursinho': 'Simulado de cursinho'}[v], key='mock_field_kind')
                options = ['', *[r['target_id'] for r in targets]]
                target_id = st.selectbox('Prova-alvo (opcional)', options,
                                         index=options.index(initial['target_id']) if initial['target_id'] in options else 0,
                                         format_func=lambda v: next((r['target']['institution']+' · '+r['target']['exam_date'] for r in targets if r['target_id']==v), 'Sem vínculo'), key='mock_field_target')
                institution = st.text_input('Instituição ou banca do simulado (opcional)', value=initial['institution'] or '', key='mock_field_institution')
                blank = st.number_input('Em branco (opcional)', min_value=0, value=initial['blank'], step=1, key='mock_field_blank')
                minutes = st.number_input('Minutos usados (opcional)', min_value=0.0, value=float(initial['minutes_used']) if initial['minutes_used'] else None, key='mock_field_minutes')
                allowed = st.number_input('Tempo permitido em minutos (opcional)', min_value=0.0, value=float(initial['minutes_allowed']) if initial['minutes_allowed'] else None, key='mock_field_allowed')
                score = st.number_input('Nota (opcional)', min_value=0.0, value=float(initial['score']) if initial['score'] is not None else None, key='mock_field_score')
                max_score = st.number_input('Nota máxima (opcional)', min_value=0.0, value=float(initial['max_score']) if initial['max_score'] else None, key='mock_field_max_score')
                realistic = st.checkbox('Fiz em condições realistas de prova', value=initial['conditions']=='realista', key='mock_field_realistic')
                unseen = st.checkbox('As questões eram inéditas para mim', value=initial['unseen_questions'], key='mock_field_unseen')
                note = st.text_area('Observação curta (opcional)', value=initial['note'], max_chars=1000, key='mock_field_note')
                st.caption('Por grande área (opcional). Ajuda a identificar onde revisar; não cria blocos por subtema.')
                areas = st.data_editor(_table(initial['areas'], 'area', 'Área'), num_rows='dynamic', hide_index=True, width='stretch',
                                       column_config={'Área': st.column_config.TextColumn(required=True),
                                                      'Questões': st.column_config.NumberColumn(min_value=1, step=1, required=True),
                                                      'Acertos': st.column_config.NumberColumn(min_value=0, step=1, required=True)}, key='mock_field_areas')
                st.caption('Por tema específico (opcional). Use o caminho completo do relatório, separado por →. Informe apenas o conceito, sem enunciados de questões.')
                topics = st.data_editor(_table(initial['topics'], 'path', 'Tema completo'), num_rows='dynamic', hide_index=True, width='stretch',
                                        column_config={'Tema completo': st.column_config.TextColumn(required=True),
                                                       'Questões': st.column_config.NumberColumn(min_value=1, step=1, required=True),
                                                       'Acertos': st.column_config.NumberColumn(min_value=0, step=1, required=True)}, key='mock_field_topics')
            submitted = st.form_submit_button('Salvar simulado', type='primary', key='mock_save')
            if submitted:
                try:
                    if day is None or total is None or correct is None: raise ValueError('Informe a data, o total de questões e os acertos.')
                    exam = MockExam(day.isoformat(), int(total), int(correct), name=name, kind=kind, institution=institution.strip() or None,
                                    target_id=target_id or None, blank=blank, minutes_used=minutes, minutes_allowed=allowed,
                                    score=score, max_score=max_score, conditions='realista' if realistic else 'nao_realista',
                                    unseen_questions=unseen, note=note, areas=_details(areas, 'area', 'Área'), topics=_details(topics, 'path', 'Tema completo'),practice_id=initial.get('practice_id'))
                    saved = mocks.save(exam, exam_key=edit['exam_key'] if edit else None, expected_version=edit['version'] if edit else 0)
                    st.session_state['mock_selected'] = saved['exam_key']
                    st.session_state['correction_exam'] = saved['exam_key']
                    st.session_state['mock_reset_pending'] = True
                    st.session_state['mock_notice'] = 'Simulado salvo. Informe os temas errados na aba Correção agora ou depois; nada foi somado aos blocos automaticamente.'
                    st.rerun()
                except ValueError as exc: st.error(str(exc))
        if edit: st.button('Cancelar correção', key='mock_cancel', on_click=_reset)
    cadence = service.store.profile()['profile'].get('mock_cadence_days', 0)
    if cadence and rows:
        suggested = date.fromisoformat(rows[-1]['exam']['day'])+timedelta(days=cadence)
        st.caption(f'Próximo simulado sugerido: {suggested.strftime("%d/%m/%Y")} · intervalo de {cadence} dias. A sugestão não cria dívida nem altera o calendário.')
    if not rows:
        _history(mocks)
        return
    with st.container(key='bento-mock-details'):
        by_key = {r['exam_key']: r for r in rows}
        selected = st.selectbox('Consultar ou corrigir simulado', list(by_key),
                                format_func=lambda key: by_key[key]['exam']['day']+' · '+by_key[key]['exam']['name'], key='mock_selected')
        row = by_key[selected]
        exam = row['exam']
        if selected != rows[-1]['exam_key']:
            _comparison(exam, targets)
        if exam['areas']:
            st.write('Resultado por grande área')
            st.html(_area_results_html(exam['areas']))
            st.caption('Faixa Wilson 95% descritiva; não representa probabilidade de aprovação.')
        if exam['topics']:
            with st.expander('Resultados por tema específico'):
                st.dataframe(_table(exam['topics'], 'path', 'Tema completo'), hide_index=True, width='stretch')
        st.button('Corrigir simulado', key='mock_edit', on_click=_reset, args=(row,))
        if st.button('Desconsiderar simulado', key='mock_void'):
            try:
                mocks.void(selected, row['version'])
                _reset()
                st.session_state['mock_notice'] = 'Simulado desconsiderado; histórico preservado.'
                st.rerun()
            except ValueError as exc: st.error(str(exc))
        with st.expander('Adicionar resultados ao estudo ou retirar conversão'):
            st.caption('Só questões inéditas com resultado por tema específico viram blocos novos. A área isolada não permite inferir subtemas. Não registre estas mesmas questões novamente no Registro.')
            if exam['unseen_questions'] and exam['topics']:
                if st.button('Adicionar como blocos de questões novas', key='mock_convert'):
                    try:
                        ids = convert_to_entries(service, selected, row['version'])
                        st.success(f'{len(ids)} bloco(s) disponível(is) no estudo. Repetir esta ação não duplica blocos.')
                    except ValueError as exc: st.error(str(exc))
                st.caption('Antes de corrigir ou desconsiderar um simulado convertido, retire os blocos abaixo. O histórico dos blocos será preservado.')
                if st.button('Retirar blocos desta conversão', key='mock_retract'):
                    try: st.success(f'{retract_conversion(service, selected, row["version"])} bloco(s) retirado(s). Agora é possível corrigir o simulado.')
                    except ValueError as exc: st.error(str(exc))
        if not exam.get('practice_id'):
            with st.expander('Considerar este dia como feito'):
                st.caption('Veja a prévia antes de substituir a meta normal do dia. Isso não soma o simulado ao desempenho dos blocos.')
                if st.button('Ver prévia do dia de simulado', key='mock_day_preview'):
                    try: st.session_state['mock_day_preview_data'] = service.preview_mock_day(selected, row['version'])
                    except ValueError as exc: st.error(str(exc))
                preview = st.session_state.get('mock_day_preview_data')
                if preview and preview['exam_key']==selected and preview['version']==row['version']:
                    st.write(f"Em {preview['day']}: meta normal de {preview['replaced_questions']} questões → dia feito por simulado de {preview['questions']} questões, sem dívida.")
                    if st.button('Aplicar dia feito por simulado', key='mock_day_apply'):
                        try:
                            st.session_state['mock_day_undo'] = service.mark_mock_day(selected, row['version'], preview)
                            st.session_state.pop('mock_day_preview_data', None)
                            st.success('Dia considerado feito por simulado.')
                        except ValueError as exc: st.error(str(exc))
                if st.session_state.get('mock_day_undo') and st.button('Desfazer dia feito por simulado', key='mock_day_undo_button'):
                    try:
                        service.cancel_replan(st.session_state['mock_day_undo'])
                        st.session_state.pop('mock_day_undo', None)
                        st.success('Meta normal do dia restaurada.')
                    except ValueError as exc: st.error(str(exc))
        _history(mocks)

    with st.container(key='bento-mock-history'):
        with st.expander('Evolução dos simulados'):
            history = pd.DataFrame([{'Data': r['exam']['day'], 'Nome': r['exam']['name'], 'Instituição': r['exam']['institution'] or 'Não informada',
                                     'Questões': r['exam']['questions'], 'Acertos': r['exam']['correct'],
                                     'Acerto (%)': 100*r['exam']['correct']/r['exam']['questions']} for r in rows])
            st.dataframe(history, hide_index=True, width='stretch')
            chart = history.copy()
            chart['Data'] = pd.to_datetime(chart['Data'])
            st.scatter_chart(chart, x='Data', y='Acerto (%)', color='Instituição')
            st.caption('Cada ponto representa um simulado. Resultados de bancas e condições diferentes não são equivalentes.')


def render_mock_settings(service):
    st.subheader('Frequência de simulados')
    st.caption('Intervalo sugerido para novas programações. Reserve ou mova datas em Simulados → Programação ou no Calendário. Alterar este valor não muda uma série já programada; 0 desliga apenas o lembrete.')
    snapshot = st.session_state.setdefault('mock_profile_snapshot', service.store.profile())
    profile = AdaptiveProfile(**snapshot['configured_profile'])
    with st.form('mock_settings'):
        cadence = st.number_input('Sugerir simulado a cada quantos dias?', min_value=0, max_value=365, value=profile.mock_cadence_days, step=1, key='mock_cadence')
        if st.form_submit_button('Salvar frequência de simulados', key='mock_save_settings'):
            try:
                service.store.save_profile(replace(profile, mock_cadence_days=cadence), snapshot['id'])
                st.session_state.pop('mock_profile_snapshot', None)
                st.success('Frequência salva.')
            except ValueError as exc: st.error(str(exc))
