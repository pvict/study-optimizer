"""Análise descritiva estritamente somente leitura; nunca ajusta parâmetros."""
from bisect import bisect_left
from collections import defaultdict
from contextlib import closing
import csv,json,sqlite3
from pathlib import Path
from datetime import timedelta
from .classification import wilson_interval
from .planning import _date
from .models import normalize_path
from .exports import _safe_cell
from .study_read_model import waived_days


REPEAT_LAG_RANGES = ((2, 4), (5, 9), (10, 18), (19, 25), (26, 35))


def _band(rate):
    return '<60%' if rate<.6 else '60–79%' if rate<.8 else '80–89%' if rate<.9 else '≥90%'


def analyze_database(db_path,as_of):
    path=Path(db_path).resolve(); _date(as_of)
    if not path.is_file(): raise FileNotFoundError(path)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row; db.execute('PRAGMA query_only=ON')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        events=[dict(r) for r in db.execute('SELECT * FROM study_events ORDER BY id')] if 'study_events' in tables else []
        plans=[{**dict(r),'data':json.loads(r['payload'])} for r in db.execute('SELECT * FROM study_plan_runs ORDER BY id')] if 'study_plan_runs' in tables else []
    latest={r['session_id']:{**r,'entry':json.loads(r['payload'])} for r in events}
    active={k:r for k,r in latest.items() if r['action']=='save' and r['entry']['day']<=as_of}
    sources={k:r['entry'] for k,r in active.items() if r['entry']['kind']=='bloco' and r['entry']['mode']!='repetidas' and r['entry'].get('correct') is not None}
    repeats=[(k,r['entry']) for k,r in active.items() if r['entry']['kind']=='bloco' and r['entry']['mode']=='repetidas' and r['entry'].get('correct') is not None]
    source_topics={k:tuple(normalize_path(s['path'])) for k,s in sources.items()}
    histories=defaultdict(list)
    for key,source in sources.items():
        histories[source_topics[key]].append((source['day'],key))
    for history in histories.values():
        history.sort()
    linked={e['review_of'] for _,e in repeats if e.get('review_of')}
    pairs={}
    for sid,e in sorted(repeats,key=lambda pair:(pair[1]['day'],pair[0])):
        topic=tuple(normalize_path(e['path']))
        origin=e.get('review_of')
        linkage='review_of'
        if origin not in sources:
            if origin: continue
            history=histories.get(topic,())
            # A chave só com a data fica antes de todos os registros do próprio dia.
            before=bisect_left(history,(e['day'],))
            if not before: continue
            origin=history[before-1][1]; linkage='same_topic_nearest_prior'
            if origin in linked: continue
        if source_topics[origin]!=topic or e['day']<=sources[origin]['day'] or origin in pairs: continue
        pairs[origin]=(sid,e,linkage)
    groups=defaultdict(list)
    repeat_pairs=0
    for origin,(_,e,linkage) in pairs.items():
        source=sources[origin]; lag=(_date(e['day'])-_date(source['day'])).days
        initial=_band(source['correct']/source['questions'])
        bounds=next((r for r in REPEAT_LAG_RANGES if r[0]<=lag<=r[1]),None)
        if bounds:
            groups[('repeat_accuracy',bounds,initial,'',linkage,source['mode'])].append(e)
            repeat_pairs+=1
        if source.get('confident_correct') is not None:
            groups[('confidence_next_review',(lag,lag),initial,_band(source['confident_correct']/source['questions']),linkage,source['mode'])].append(e)
    rows=[]
    for (measurement,bounds,initial,confidence,linkage,mode),entries in sorted(groups.items()):
        n=sum(e['questions'] for e in entries); correct=sum(e['correct'] for e in entries)
        lower,upper=wilson_interval(100*correct/n,n)
        topicdays=len({(tuple(normalize_path(e['path'])),e['day']) for e in entries})
        lag_fields=({'lag_days':None,'lag_min_days':bounds[0],'lag_max_days':bounds[1]} if measurement=='repeat_accuracy'
                    else {'lag_days':bounds[0]})
        rows.append({'measurement':measurement,**lag_fields,'initial_band':initial,'confidence_band':confidence,'linkage':linkage,'mode':mode,
                     'n_attempts':n,'n_sessions':len(entries),'n_topicdays':topicdays,'correct':correct,'value':100*correct/n,
                     'wilson_low_pct':lower,'wilson_high_pct':upper,'warning':'Dados insuficientes' if n<30 or topicdays<5 else 'Tentativas correlacionadas; apenas descrição'})
    times=defaultdict(list)
    for record in active.values():
        e=record['entry']
        if e['kind']=='bloco' and e.get('minutes') is not None and e['questions']>0:
            times[(e['path'][0],e['mode'])].append(e)
    for (area,mode),entries in sorted(times.items()):
        n=sum(e['questions'] for e in entries)
        rows.append({'measurement':'time_per_question','area':area,'mode':mode,'value':sum(e['minutes'] for e in entries)/n,
                     'n_attempts':n,'n_sessions':len(entries),'n_topicdays':len({(tuple(normalize_path(e['path'])),e['day']) for e in entries}),
                     'warning':'Média ponderada pelos blocos com duração informada'})
    waived=waived_days(plans,as_of)
    saved={r['data']['plan']['date']:r['data']['plan'] for r in plans if r['data'].get('kind')=='daily_schedule' and r['data']['plan']['date']<=as_of}
    done=defaultdict(int)
    for record in active.values():
        e=record['entry']
        if e['kind']=='bloco': done[(e['day'],tuple(normalize_path(e['path'])))]+=e['questions']
    planned=actual=blocks=completed=0
    for day,p in saved.items():
        if day in waived: continue
        for item in p['items']:
            n=item['questions']; used=done[(day,tuple(normalize_path(item['path'])))]; planned+=n; actual+=min(n,used); blocks+=1; completed+=used>=n
    for name,numerator,denominator in [('adherence_questions',actual,planned),('adherence_topicdays',completed,blocks)]:
        rows.append({'measurement':name,'numerator':numerator,'denominator':denominator,'value':100*numerator/denominator if denominator else None,
                     'warning':'Dados insuficientes' if not denominator else 'Planos salvos; execução limitada ao previsto por tema/dia'})
    if not repeat_pairs: rows.append({'measurement':'repeat_accuracy','n_attempts':0,'n_sessions':0,'n_topicdays':0,'warning':'Dados insuficientes'})
    adequate=any(r.get('measurement')=='repeat_accuracy' and r.get('n_attempts',0)>=30 and r.get('n_topicdays',0)>=5 for r in rows)
    status='Há grupos com amostra descritiva; isso não valida um modelo pessoal nem autoriza ajuste automático.' if adequate else 'Dados insuficientes para avaliar um modelo pessoal. As tabelas descrevem registros disponíveis; não preveem aprovação.'
    lag_labels=', '.join(f'{lo}–{hi}' for lo,hi in REPEAT_LAG_RANGES)
    lines=['# Análise de calibração — '+as_of,'','Somente leitura. Nenhum parâmetro foi ajustado ou selecionado.','',status,'',
           f'Acerto em repetidas por faixas inclusivas de {lag_labels} dias. {repeat_pairs} de {len(pairs)} pares de origem e revisão entram nessas faixas. A análise de convicção usa os dias exatos.',
           'Usamos a primeira revisão seguinte de cada origem e damos preferência ao vínculo explícito. A associação pelo tema indica apenas que os blocos tratam do mesmo assunto.',
           'O desempenho anterior influencia a data escolhida pelo agendador. A comparação entre faixas descreve associações e não estima o efeito de mudar um intervalo.',
           'Questões novas, mistas e repetidas são fontes separadas; PDFs e acumulados não são acrescentados. Wilson descreve contagens, mas questões podem estar correlacionadas.',
           'Amostras pequenas, escolha de questões fáceis, duração não informada e diferenças de banca limitam as conclusões. Nenhuma relação observada é causal.','',
           '| Medida | Área | Modalidade | Intervalo | Faixa inicial | Convicção inicial | Vínculo | Tentativas | Sessões | Tema/dias | Valor | Wilson 95% | Observação |','|---|---|---|---:|---|---|---|---:|---:|---:|---:|---|---|']
    for r in rows:
        value=r.get('value'); interval=f"{r['wilson_low_pct']:.1f}–{r['wilson_high_pct']:.1f}%" if 'wilson_low_pct' in r else 'Não aplicável'
        lag=f"{r['lag_min_days']}–{r['lag_max_days']} dias" if 'lag_min_days' in r else r.get('lag_days','')
        cells=[r['measurement'],r.get('area',''),r.get('mode',''),lag,r.get('initial_band',''),r.get('confidence_band',''),r.get('linkage',''),r.get('n_attempts',''),r.get('n_sessions',''),r.get('n_topicdays',''),f'{value:.2f}' if value is not None else 'Sem dados',interval,r.get('warning','')]
        lines.append('| '+' | '.join(str(c).replace('|','\\|').replace('\n',' ') for c in cells)+' |')
    return {'rows':rows,'waived_days':sorted(waived),'repeat_pair_counts':{'included':repeat_pairs,'matched':len(pairs)},
            'markdown':'\n'.join(lines)+'\n'}


def write_report(db_path,output_dir,as_of):
    as_of=_date(as_of).isoformat()
    db_path=Path(db_path).resolve(); output=Path(output_dir).resolve()
    if not db_path.is_file(): raise FileNotFoundError(db_path)
    if output.is_relative_to(db_path.parent): raise ValueError('Salve o relatório fora da pasta do banco ativo.')
    md=output/f'analise-calibracao-{as_of}.md'; target=output/f'analise-calibracao-{as_of}.csv'
    if md.exists() or target.exists(): raise FileExistsError('Os relatórios já existem. Escolha outra pasta para preservar a versão anterior.')
    result=analyze_database(db_path,as_of); output.mkdir(parents=True,exist_ok=True)
    fields=['measurement','area','mode','lag_days','initial_band','confidence_band','linkage','n_attempts','n_sessions','n_topicdays','correct','value','wilson_low_pct','wilson_high_pct','numerator','denominator','warning','lag_min_days','lag_max_days']
    with target.open('x',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields); writer.writeheader()
        for row in result['rows']: writer.writerow({k:_safe_cell(row.get(k,'')) for k in fields})
    with md.open('x',encoding='utf-8') as file: file.write(result['markdown'])
    return md,target
