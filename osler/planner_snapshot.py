"""Retratos acumulados confirmados: contexto, sem fabricar tentativas independentes."""
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from .models import normalize_path
from .planning import _date,_number

SEMANTICS={'questions':'unique','accuracy':'latest_confident_including_reviews','contact':'any_question_including_reviews'}


def planner_supply(topic,required,completed=0,as_of=None):
    """Cobertura por quantidade; não limita a dose nem identifica questões realizadas."""
    snapshot=topic.get('planner_snapshot')
    if not snapshot or as_of and snapshot['observed_date']>as_of: return None
    total=snapshot['available_questions']
    for value,name in ((total,'Questões no Planner'),(required,'Questões recomendadas'),(completed,'Questões registradas')):
        _number(value,name,integer=True)
    covered=min(required,total)
    remaining=max(0,required-completed)
    planner_remaining=max(0,covered-completed)
    external=max(0,required-covered)
    return {'recommended':required,'planner_total':total,'planner_part':covered,'external_part':external,
            'completed':completed,'remaining':remaining,'planner_remaining':planner_remaining,
            'external_remaining':max(0,remaining-planner_remaining),
            'external_only':bool(external and remaining and completed>=covered),
            'observed_date':snapshot['observed_date']}


def load_planner_contexts(repo,datasets,report_id,as_of):
    result,warnings={},[]
    for ds in sorted(datasets,key=lambda d:(d['observed_date'],d['id'])):
        if (ds.get('source_kind')!='manual_osler_planner_export' or ds.get('planner_semantics')!=SEMANTICS or
                ds.get('qbank_report_id')!=report_id or ds['observed_date']>as_of): continue
        try:
            observed=_date(ds['observed_date'])
            folder=(repo.root/ds['source_path']).resolve()
            name=ds['planner_snapshot']
            if name!='snapshot.json' or not folder.is_relative_to(repo.exports.resolve()): raise ValueError('Caminho inválido.')
            path=(folder/name).resolve()
            if not path.is_relative_to(repo.exports.resolve()) or path.stat().st_size>20*1024*1024: raise ValueError('Arquivo inválido.')
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=ds['snapshot_sha256']: raise ValueError('Hash divergente.')
            snapshot=json.loads(raw)
            if snapshot['observed_date']!=ds['observed_date'] or snapshot['source_sha256']!=ds['source_sha256']: raise ValueError('Origem divergente.')
            current={}
            for row in snapshot['rows']:
                parts=row['path']
                if not isinstance(parts,list) or not parts or any(not isinstance(p,str) or not p.strip() for p in parts): raise ValueError('Tema inválido.')
                key=tuple(normalize_path(parts))
                if key in current: raise ValueError('Tema duplicado.')
                n,total=row['questions_done_snapshot'],row['questions_available_snapshot']
                _number(total,'Questões disponíveis',integer=True)
                _number(n,'Questões distintas',integer=True,maximum=total)
                rate=row['confident_accuracy_pct']
                if rate is not None:
                    _number(rate,'Segurança acumulada',maximum=100)
                    if not n: raise ValueError('Percentual sem questões distintas.')
                age=row['days_since_contact']
                if age is not None: _number(age,'Dias sem contato',integer=True,maximum=3652058)
                pending=row['pending_reviews']
                if pending is not None: _number(pending,'Pendências',integer=True)
                current[key]={'dataset_id':ds['id'],'observed_date':ds['observed_date'],'unique_questions':n,
                              'available_questions':total,'confident_accuracy_pct':rate,'pending_reviews':pending,
                              'last_contact':(observed-timedelta(days=age)).isoformat() if age is not None else None}
            # Cada retrato substitui apenas os seus caminhos, nunca soma acumulados.
            result.update(current)
        except (ValueError,TypeError,KeyError,OSError,OverflowError) as exc:
            warnings.append(f"Retrato Osler {ds['id']} não utilizado: arquivo ou metadados incompatíveis. Confira a importação.")
    return result,warnings
