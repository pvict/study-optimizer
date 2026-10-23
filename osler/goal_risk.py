"""Faixas descritivas, sem combinar fontes ou prever aprovação."""
from collections import defaultdict,Counter
from datetime import timedelta
from .classification import wilson_interval
from .planning import _date
from .models import normalize_path
from .exam_goals import active_exams
from .study_models import AdaptiveProfile
from .study_read_model import read_events,latest_active
from .adaptive_planning import incidence_weights

NOTICE='Referência baseada nos seus registros e no corte que você informou. Não é uma previsão de aprovação.'


def evidence_label(correct,n,cutoff,*,comparable=True,min_sample=30):
    if not comparable or n<min_sample: return 'Sem dados suficientes'
    lower,upper=wilson_interval(100*correct/n,n)
    return 'Abaixo do corte de referência' if upper<cutoff else 'Acima' if lower>cutoff else 'Próximo'


def measure(correct,n):
    return {'correct':correct,'n':n,'accuracy_pct':100*correct/n if n else None,
            'wilson95':list(wilson_interval(100*correct/n,n)) if n else None}


def goal_risk_report(service,as_of):
    p=AdaptiveProfile(**service.store.profile()['profile'])
    start=(_date(as_of)-timedelta(days=p.recent_days-1)).isoformat()
    sessions=[r for r in latest_active(read_events(service.repository,'study_events'),'session_id') if
              start<=r['data']['day']<=as_of and r['data']['kind']=='bloco' and r['data']['mode']=='novas' and
              r['data'].get('correct') is not None and not r['session_id'].startswith('mock-') and not r['data'].get('source','').startswith('Simulado ')]
    blocks=defaultdict(list)
    for r in sessions: blocks[tuple(normalize_path(r['data']['path']))].append(r['data'])
    q=service.guide._report('qbank',as_of)
    counts=Counter(tuple(normalize_path(t.path)) for t in q.records) if q else {}
    topics=[{'topic_id':t.topic_id,'path':t.path} for t in q.records if t.is_leaf and counts[tuple(normalize_path(t.path))]==1] if q else []
    present={tuple(normalize_path(t['path'])) for t in topics}
    for key,values in blocks.items():
        if key not in present: topics.append({'topic_id':' → '.join(key),'path':values[0]['path']})
    mocks=[r for r in latest_active(read_events(service.repository,'mock_exams'),'exam_key') if start<=r['data']['day']<=as_of]
    result=[]
    for e in active_exams(service.repository):
        target=e['target']; bank=normalize_path([target['institution']])[0]
        datasets=service.guide.datasets()
        individual=[d for d in datasets if normalize_path(d['institutions'])==[bank]]
        incidence=incidence_weights(topics,individual,{target['institution']:1},as_of,p.parameters)
        known=bool(incidence['contexts'])
        known_ids=set(incidence.get('known_topic_ids',[]))
        measured_mass=sum(w for key,w in incidence['weights'].items() if key in known_ids)
        warnings=[] if known else ['Sem tabela individual aplicável. Uma tabela conjunta não fornece a incidência desta banca.']
        area_rows=defaultdict(list)
        for t in topics:
            entries=blocks.get(tuple(normalize_path(t['path'])),[])
            m=measure(sum(s['correct'] for s in entries),sum(s['questions'] for s in entries))
            # A reserva de exploração serve à agenda, não mede incidência da banca.
            weight=incidence['weights'].get(t['topic_id'],0)/measured_mass if known and t['topic_id'] in known_ids and measured_mass else None
            goal=p.target_for_area(t['path'][0])
            gap=weight*max(0,goal-m['accuracy_pct']) if weight is not None and m['n'] else None
            band=[weight*max(0,goal-m['wilson95'][1]),weight*max(0,goal-m['wilson95'][0])] if gap is not None else None
            area_rows[t['path'][0]].append({**t,**m,'incidence_weight':weight,'weighted_gap_pp':gap,'gap_interval_pp':band})
        areas=[]
        for area,ts in sorted(area_rows.items()):
            m=measure(sum(t['correct'] for t in ts),sum(t['n'] for t in ts))
            areas.append({'area':area,**m,'label':'Sem dados suficientes','topics':sorted(ts,key=lambda t:-(t['weighted_gap_pp'] or 0)),
                          'weighted_gap_pp':sum(t['weighted_gap_pp'] for t in ts if t['weighted_gap_pp'] is not None) if any(t['weighted_gap_pp'] is not None for t in ts) else None})
        mock_rows=[]
        cutoff=100*target['cutoff_score']/target['max_score']
        for r in mocks:
            mock=r['data']
            if normalize_path([mock.get('institution') or 'não informada'])[0]!=bank: continue
            equal_score=mock.get('score') is None or abs(100*mock['score']/mock['max_score']-100*mock['correct']/mock['questions'])<1e-9
            comparable=(target.get('score_basis')=='percentual_objetivo' and mock.get('target_id')==e['target_id'] and mock['conditions']=='realista' and mock['unseen_questions'] and equal_score)
            m=measure(mock['correct'],mock['questions'])
            mock_rows.append({**m,'exam_key':r['exam_key'],'day':mock['day'],'name':mock['name'],'conditions':mock['conditions'],
                              'score':mock.get('score'),'max_score':mock.get('max_score'),
                              'label':evidence_label(mock['correct'],mock['questions'],cutoff,comparable=comparable),
                              'comparison_reason':'Escala objetiva confirmada; resultado observado, não previsão.' if comparable else 'Escala, vínculo, ineditismo ou condições não permitem comparar com o corte.'})
        latest=sorted(mock_rows,key=lambda m:m['day'])[-1] if mock_rows else None
        result.append({'target_id':e['target_id'],'institution':target['institution'],'exam_date':target['exam_date'],
                       'days_remaining':(_date(target['exam_date'])-_date(as_of)).days,'cutoff_pct':cutoff,
                       'cutoff_score':target['cutoff_score'],'max_score':target['max_score'],'cutoff_source':target['cutoff_source'],
                       'label':latest['label'] if latest else 'Sem dados suficientes','mocks':mock_rows,'areas':areas,
                       'incidence_contexts':incidence['contexts'],'warnings':warnings})
    return {'as_of':as_of,'window_start':start,'targets':result,'notice':NOTICE}
