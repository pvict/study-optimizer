"""Totais descritivos de blocos por calendário; PDFs e acumulados não são sessões."""
from collections import defaultdict
from datetime import timedelta

from .models import normalize_path, stable_topic_id
from .planning import _date
from .review_queue import review_progress

PERIODS=['Dia','Semana','Mês','Todo o período']
MODES={'Todas':None,'Novas':'novas','Repetidas':'repetidas','Mistas':'mistas'}


def period_bounds(period,reference):
    day=_date(reference)
    if period=='Dia': start=day
    elif period=='Semana': start=day-timedelta(days=day.weekday())
    elif period=='Mês': start=day.replace(day=1)
    elif period=='Todo o período': start=None
    else: raise ValueError('Período inválido.')
    return start.isoformat() if start else None,reference


def topic_statistics(states,sessions,period,reference,mode='Todas'):
    start,end=period_bounds(period,reference)
    if mode not in MODES: raise ValueError('Modalidade inválida.')
    grouped=defaultdict(list)
    histories=[s for s in sessions if s['entry']['day']<=end]
    progress=review_progress(histories) if all('session_id' in s for s in histories) else []
    recorded={}
    for event in sessions:
        e=event['entry']
        if e['kind']!='bloco' or e['day']>end or start and e['day']<start: continue
        if MODES[mode] and e['mode']!=MODES[mode]: continue
        grouped[tuple(normalize_path(e['path']))].append(e)
        recorded[tuple(normalize_path(e['path']))]=e['path']
    known={tuple(normalize_path(t['path'])) for t in states}
    states=list(states)
    for key,path in recorded.items():
        if key not in known:
            states.append({'topic_id':stable_topic_id(path),'path':path,'priority':'sem_avaliacao','status':'fora_catalogo','importance':None,
                           'last_contact':max(e['day'] for e in grouped[key]),'answered_pdf':None,'pdf_accuracy':{'raw':'—'},'catalog_available':False})
    rows=[]
    for t in states:
        snapshot=t.get('planner_safety') or {}
        entries=grouped[tuple(normalize_path(t['path']))]
        exact=[e for e in entries if e.get('correct') is not None]
        approx=[e for e in entries if e.get('percent') is not None]
        n=sum(e['questions'] for e in exact)
        approximate_n=sum(e['questions'] for e in approx)
        correct=sum(e['correct'] for e in exact)
        confident=[e for e in entries if e.get('confident_correct') is not None]
        cn=sum(e['questions'] for e in confident)
        cohorts=[p for p in progress if normalize_path(p['path'])==normalize_path(t['path']) and (not start or p['day']>=start)]
        cohort_n=sum(p['questions'] for p in cohorts)
        rows.append({'topic_id':t['topic_id'],'Tema':t['path'][-1],'Área':t['path'][0],'Caminho':' → '.join(t['path']),
                     'Prioridade':{'urgente':'Urgente','alta':'Alta','normal':'Manutenção','sem_avaliacao':'Sem avaliação'}[t['priority']],
                     'Situação':{'sem_registro':'Sem estudo registrado','diagnostico':'Precisa de medição','revisao':'Em revisão','fora_catalogo':'Fora do catálogo atual'}[t['status']],
                     'Questões':sum(e['questions'] for e in entries),'Acertos':correct,'Questões com acertos exatos':n,
                     'Com convicção (%)':100*sum(e['confident_correct'] for e in confident)/cn if cn else None,
                     'Lotes consolidados (%)':100*sum(p['consolidated'] for p in cohorts)/cohort_n if cohort_n else None,
                     'Questões com convicção informada':cn,'Estado':'Não visto' if t.get('status')=='sem_registro' else {'dominado':'Dominado','aprendendo':'Aprendendo','alerta':'Em alerta'}.get(t.get('learning_state'),'Sem avaliação'),
                     'Domínio / evidência':t.get('domain_evidence','Medição pendente'),
                     'Próxima ação':('Priorizar agora' if t.get('initial_focus') else 'Distribuição gradual') if t.get('review_committed') is False else t.get('next_review'),
                     'Posição na fila inicial':t.get('initial_rank'),
                     'Próxima revisão':t.get('next_review'),'Meta do tema (%)':t.get('target_accuracy'),
                     'Segurança acumulada Osler (%)':snapshot.get('confident_accuracy_pct'),
                     'Questões realizadas':snapshot.get('unique_questions',t.get('answered_pdf')),
                     'Convicção (%)':snapshot.get('confident_accuracy_pct'),
                     'Fonte do histórico':'Osler · '+snapshot['observed_date'] if snapshot else 'PDF · '+(t.get('report_date') or 'sem data') if t.get('answered_pdf') is not None else 'Sem histórico importado',
                     'Questões distintas Osler':snapshot.get('unique_questions'),'Retrato Osler':snapshot.get('observed_date'),
                     'Pendências no retrato Osler':snapshot.get('pending_reviews'),
                     'Acerto (%)':100*correct/n if n else None,'Questões aproximadas':approximate_n,
                     'Acerto aproximado (%)':sum(e['questions']*e['percent'] for e in approx)/approximate_n if approximate_n else None,
                     **{label:sum(e['questions'] for e in entries if e['mode']==value) for label,value in MODES.items() if value},
                     'Último contato':t['last_contact'],'Incidência relativa (%)':100*t['importance'] if t['importance'] is not None else None,
                     'Respondidas no PDF':t['answered_pdf'],'Acerto no PDF':t['pdf_accuracy']['raw'],'catalog_available':t.get('catalog_available',True)})
    return rows
