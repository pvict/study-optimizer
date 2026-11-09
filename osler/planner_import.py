"""Atualização versionada do retrato do Planner, separada de tentativas de estudo."""
from collections import defaultdict
from datetime import timedelta
import hashlib
import json
import re

from .files import write_immutable
from .incidence import parse_html_table, prepare_incidence
from .models import normalize_path
from .planner_service import valid_date, today_local
from .planning import _date
from .planner_snapshot import SEMANTICS, load_planner_contexts


def _text(value):
    return normalize_path([value])[0].strip()


def _count(value):
    if not re.fullmatch(r'\d+|\d{1,3}(?:\.\d{3})+', value):
        raise ValueError('Quantidade inválida no Planner: '+value[:70])
    return int(value.replace('.', ''))


def parse_planner_html(data):
    if not isinstance(data, bytes) or not data or len(data)>20*1024*1024:
        raise ValueError('Envie um HTML do Planner de até 20 MB.')
    try: table=parse_html_table(data.decode('utf-8-sig'))
    except UnicodeDecodeError: raise ValueError('Salve o HTML em UTF-8 e envie novamente.') from None
    if len(table['rows'])>10000: raise ValueError('A tabela excede 10.000 temas.')
    headers=[_text(h) for h in table['headers']]
    def column(words, optional=False):
        matches=[i for i,h in enumerate(headers) if all(w in h for w in words)]
        if len(matches)==1:return matches[0]
        if optional and not matches:return None
        raise ValueError('Não identifiquei a coluna '+ ' '.join(words)+'. Copie a tabela completa do Planner, com os títulos.')
    cols={k:column(words) for k,words in {'theme':['tema'],'pending':['revis','pendent'],
          'rate':['acert','seguran'],'age':['dias','contato'],'counts':['incid','geral']}.items()}
    incidence=column(['incid','institui'],optional=True)
    result=[];seen=set()
    missing={'','-','—','–','nunca','sem contato','nao estudado'}
    for number,values in enumerate(table['rows'],1):
        path=[p.strip() for p in re.split(r'>>|→|>|»|›',values[cols['theme']]) if p.strip()]
        if not path:raise ValueError(f'Linha {number}: tema vazio.')
        key=tuple(normalize_path(path))
        if key in seen:raise ValueError(f'Linha {number}: tema repetido. Nenhum dado foi importado.')
        seen.add(key)
        counts=re.fullmatch(r'([\d.]+)\s+de\s+([\d.]+)(?:\s+(?:feitas|respondidas|questoes))*',_text(values[cols['counts']]))
        if not counts:raise ValueError(f'Linha {number}: não reconheci as questões feitas e disponíveis.')
        n,total=map(_count,counts.groups())
        if n>total:raise ValueError(f'Linha {number}: questões feitas ultrapassam o total disponível.')
        raw=_text(values[cols['rate']]);rate=None
        if raw not in missing:
            if not re.fullmatch(r'\d+(?:[.,]\d+)?\s*%',raw):raise ValueError(f'Linha {number}: segurança inválida.')
            rate=float(raw.rstrip('%').strip().replace(',','.'))
            if not 0<=rate<=100 or not n:raise ValueError(f'Linha {number}: segurança sem uma base válida de questões.')
        raw=_text(values[cols['age']]);age=None
        if raw=='hoje':age=0
        elif raw=='ontem':age=1
        elif raw not in missing:
            match=re.fullmatch(r'(\d+)\s*(?:d|dias?)',raw)
            if not match:raise ValueError(f'Linha {number}: dias sem contato não reconhecidos.')
            age=int(match[1])
        raw=_text(values[cols['pending']]);pending=None
        if raw=='em dia':pending=0
        elif raw not in missing:pending=_count(raw)
        value=None
        if incidence is not None:
            raw=_text(values[incidence])
            match=re.fullmatch(r'([\d.]+)\s*(?:questoes|questao)?',raw)
            if match:value=_count(match[1])
            elif raw not in missing:raise ValueError(f'Linha {number}: incidência das instituições inválida.')
        result.append({'path':path,'questions_done_snapshot':n,'questions_available_snapshot':total,
                       'confident_accuracy_pct':rate,'days_since_contact':age,'pending_reviews':pending,
                       'institution_incidence_questions':value,'source_order':number})
    return result


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class PlannerImportService:
    def __init__(self,repo):
        from .adaptive_service import AdaptiveService
        self.repo=repo
        self.adaptive=AdaptiveService(repo)
        self.guide=self.adaptive.guide

    def preview(self,data,filename,day,*,include_incidence=False,institutions=()):
        valid_date(day,past=True)
        rows=parse_planner_html(data)
        if type(include_incidence) is not bool:raise ValueError('Escolha se deseja atualizar a incidência.')
        if not isinstance(institutions,(list,tuple)) or any(not isinstance(s,str) or not s.strip() for s in institutions):
            raise ValueError('Informe as instituições selecionadas nesta consulta.')
        institutions=list(dict.fromkeys(s.strip() for s in institutions))
        if include_incidence and (not institutions or any(r['institution_incidence_questions'] is None for r in rows)):
            raise ValueError('Para atualizar incidência, informe as instituições e envie sua coluna completa.')
        token=self.adaptive.agenda.token()
        report=self.guide._report('qbank',today_local().isoformat())
        if report is None:raise ValueError('Importe primeiro o PDF do acervo de questões em Arquivos e ferramentas.')
        by_path=defaultdict(list)
        for record in report.records:by_path[tuple(normalize_path(record.path))].append(record)
        datasets=self.guide.datasets()
        previous,warnings=load_planner_contexts(self.repo,datasets,report.file_sha256,day)
        prior_incidence={}
        if include_incidence:
            group=set(normalize_path(institutions))
            relevant=[d for d in prepare_incidence(datasets,institutions,day) if set(normalize_path(d['institutions']))==group]
            for dataset in relevant:
                if dataset['unit']=='questoes':prior_incidence.update(dataset['_index'])
            received={tuple(normalize_path(r['path'])) for r in rows}
            if set(prior_incidence)-received:
                raise ValueError('A tabela é parcial em relação à incidência atual. Desmarque a atualização de incidência para atualizar só o progresso, ou envie a tabela completa.')
        comparison=[];matched=0;incidence_rows=[];included=set()
        positive=sorted({r['institution_incidence_questions'] for r in rows if (r['institution_incidence_questions'] or 0)>0},reverse=True)
        for row in rows:
            key=tuple(normalize_path(row['path']));matches=by_path.get(key,[])
            included.add(key)
            recognized=len(matches)==1
            if recognized:row['path']=matches[0].path;matched+=1
            old=previous.get(key,{})
            try:contact=(_date(day)-timedelta(days=row['days_since_contact'])).isoformat() if row['days_since_contact'] is not None else None
            except (ValueError,OverflowError):raise ValueError('Os dias sem contato ultrapassam uma data válida.') from None
            row['matched']=recognized
            comparison.append({'Tema':' → '.join(row['path']),'Reconhecido':recognized,
                'Questões antes':old.get('unique_questions'),'Questões novas':row['questions_done_snapshot'],
                'Convicção antes (%)':old.get('confident_accuracy_pct'),'Convicção nova (%)':row['confident_accuracy_pct'],
                'Contato antes':old.get('last_contact'),'Contato novo':contact,'Pendentes':row['pending_reviews']})
            if include_incidence:
                value=row['institution_incidence_questions'];rank=positive.index(value)/len(positive) if value>0 else 1
                comparison[-1].update({'Incidência antes (questões)':prior_incidence.get(key,{}).get('value'),
                                       'Incidência agora (questões)':value})
                incidence_rows.append({'path':row['path'] if recognized else None,'topic':' → '.join(row['path']),
                    'value':value,'band':'alta' if rank<1/3 else 'media' if rank<2/3 else 'baixa','reason':'associação exata' if recognized else 'não reconhecido'})
        if not matched:raise ValueError('Nenhum tema corresponde ao acervo atual. Confira a hierarquia ou importe o PDF atualizado.')
        source_sha=hashlib.sha256(data).hexdigest()
        identity={'source_sha256':source_sha,'observed_date':day,'qbank_report_id':report.file_sha256,
                  'incidence_included':include_incidence,'institutions':institutions if include_incidence else []}
        key=_digest(identity)
        if token!=self.adaptive.agenda.token():raise ValueError('O plano mudou. Atualize a prévia.')
        return {**identity,'import_key':key,'token':token,'filename':str(filename)[:200],
                'rows':rows,'incidence_rows':incidence_rows,'received_rows':len(rows),'matched_rows':matched,
                'preserved_topics':len(set(previous)-included),'comparison':comparison,'warnings':warnings,
                'duplicate_id':next((d['id'] for d in datasets if d.get('import_key')==key),None)}

    def apply(self,preview,data):
        fresh=self.preview(data,preview['filename'],preview['observed_date'],
                           include_incidence=preview['incidence_included'],institutions=preview['institutions'])
        if fresh['import_key']!=preview['import_key']:raise ValueError('O arquivo ou as opções mudaram. Gere outra prévia.')
        if fresh['duplicate_id']:return fresh['duplicate_id']
        if fresh['token']!=preview['token']:raise ValueError('O plano mudou. Atualize a prévia antes de importar.')
        folder=self.repo.exports/'planner'/fresh['import_key'];folder.mkdir(parents=True,exist_ok=True)
        snapshot={'observed_date':fresh['observed_date'],'source_sha256':fresh['source_sha256'],'rows':fresh['rows']}
        raw=json.dumps(snapshot,ensure_ascii=False,sort_keys=True).encode('utf-8')
        write_immutable(folder/'origem.html',data);write_immutable(folder/'snapshot.json',raw)
        payload={k:fresh[k] for k in ['import_key','source_sha256','observed_date','qbank_report_id','incidence_included','institutions','filename','received_rows','matched_rows']}
        payload.update(source_kind='manual_osler_planner_export',planner_semantics=SEMANTICS,
                       planner_snapshot='snapshot.json',snapshot_sha256=hashlib.sha256(raw).hexdigest(),
                       source_path=str(folder.relative_to(self.repo.root)),unit='questoes',rows=fresh['incidence_rows'])
        return self.guide.store.save_dataset(payload,expected_token=preview['token'])
