"""Pesos individuais exigem fontes individuais para todo o conjunto ponderado."""
import json
import hashlib
from math import isfinite
from .incidence import prepare_incidence
from .models import normalize_path


def policy_inputs(db):
    latest={}
    for row in db.execute('SELECT target_id,action,payload FROM exam_targets ORDER BY id'):
        latest[row['target_id']]={'target_id':row['target_id'],'action':row['action'],'target':json.loads(row['payload'])}
    guide=db.execute('SELECT payload FROM guide_settings ORDER BY id DESC LIMIT 1').fetchone()
    return {'exams':[r for r in latest.values() if r['action']=='save'],
            'institutions':json.loads(guide['payload']).get('institutions',[]) if guide else [],
            'datasets':[{'id':r['id'],**json.loads(r['payload'])} for r in db.execute('SELECT id,payload FROM incidence_datasets ORDER BY id')]}


def exam_weight_policy(profile,inputs,as_of):
    base=dict(profile.institution_weights) or {name:1 for name in inputs['institutions']}
    names={normalize_path([name])[0]:name for name in base}
    proposed=dict(base); linked={}; unknown=[]
    exams={e['target_id']:e['target'] for e in inputs['exams']}
    for key,weight in profile.exam_weights.items():
        if key not in exams: unknown.append(key); continue
        normalized=normalize_path([exams[key]['institution']])[0]
        name=names.setdefault(normalized,exams[key]['institution'])
        linked[name]=max(linked.get(name,0),weight)
    proposed.update(linked)
    prepared=prepare_incidence(inputs['datasets'],list(proposed),as_of)
    sources={}
    for dataset in prepared:
        if len(dataset['institutions'])!=1: continue
        usable=any(isinstance(r['value'],(int,float)) and isfinite(r['value']) and r['value']>0 for r in dataset['_index'].values())
        if usable: sources[normalize_path(dataset['institutions'])[0]]=dataset
    missing=[name for name in proposed if normalize_path([name])[0] not in sources]
    requested=bool(profile.exam_weights) or any(weight!=1 for weight in profile.institution_weights.values())
    allowed=not requested or not(missing or unknown)
    reason=''
    if not allowed:
        reason='Pesos por prova exigem incidência individual aplicável para cada instituição do conjunto.'
        if missing: reason+=' Faltam: '+', '.join(missing)+'.'
        if unknown: reason+=' Há prova vinculada desconsiderada ou não encontrada.'
    safe={name:1 for name in base} if not allowed else proposed
    basis=hashlib.sha256(json.dumps({'weights':{normalize_path([n])[0]:w for n,w in proposed.items()},
                                  'exams':{key:normalize_path([exams[key]['institution']])[0] for key in profile.exam_weights if key in exams}},sort_keys=True).encode()).hexdigest() if requested else ''
    return {'allowed':allowed,'requested':requested,'missing':missing,'unknown_ids':unknown,'reason':reason,
            'base_weights':base,'effective_weights':safe,'basis':basis,
            'sources':[{'institution':name,'dataset_id':sources[normalize_path([name])[0]]['id'],
                        'observed_date':sources[normalize_path([name])[0]]['observed_date'],'unit':sources[normalize_path([name])[0]]['unit']}
                       for name in proposed if normalize_path([name])[0] in sources]}
