"""Rendimento em novas: observação, referência estacionária e tendência testada."""
from collections import defaultdict
from datetime import timedelta
from math import exp,log,sqrt
from .classification import wilson_interval
from .planning import _date
from .models import normalize_path


def _interval(k,n): return [v/100 for v in wilson_interval(100*k/n,n)] if n else None


def _fit(weeks):
    xs=[(_date(w['date'])-_date(weeks[0]['date'])).days for w in weeks]
    ys=[log((w['correct']+1)/(w['questions']-w['correct']+1)) for w in weeks]
    weights=[w['questions'] for w in weeks]
    total=sum(weights); xbar=sum(x*w for x,w in zip(xs,weights))/total; ybar=sum(y*w for y,w in zip(ys,weights))/total
    den=sum(w*(x-xbar)**2 for x,w in zip(xs,weights))
    slope=sum(w*(x-xbar)*(y-ybar) for x,y,w in zip(xs,ys,weights))/den if den else 0
    return {'intercept':ybar-slope*xbar,'slope':slope,'origin':weeks[0]['date'],'last':weeks[-1]['date']}


def _predict(fit,day):
    elapsed=(_date(day)-_date(fit['origin'])).days
    observed=(_date(fit['last'])-_date(fit['origin'])).days
    damped=observed+28*(1-exp(-max(0,elapsed-observed)/28)) if elapsed>observed else elapsed
    z=max(-12,min(12,fit['intercept']+fit['slope']*damped))
    return 1/(1+exp(-z))


def performance_history(sessions,as_of):
    entries=[s['entry'] for s in sessions if s['entry']['kind']=='bloco' and s['entry']['mode']=='novas' and
             not s['entry'].get('review_of') and s['entry']['correct'] is not None and s['entry']['day']<=as_of]
    weekly=defaultdict(lambda:{'questions':0,'correct':0,'confident_n':0,'confident':0})
    paths=set()
    for e in entries:
        paths.add(tuple(normalize_path(e['path']))); day=_date(e['day']); key=(day-timedelta(days=day.weekday())).isoformat()
        w=weekly[key]; w['questions']+=e['questions']; w['correct']+=e['correct']
        if e.get('confident_correct') is not None: w['confident_n']+=e['questions']; w['confident']+=e['confident_correct']
    weeks=[{'date':d,**w,'accuracy':w['correct']/w['questions'],'conviction':w['confident']/w['confident_n'] if w['confident_n'] else None} for d,w in sorted(weekly.items())]
    n=sum(w['questions'] for w in weeks); correct=sum(w['correct'] for w in weeks)
    cn=sum(w['confident_n'] for w in weeks); cc=sum(w['confident'] for w in weeks)
    days=sorted(e['day'] for e in entries)
    span=(_date(days[-1])-_date(days[0])).days if days else 0
    recent_entries=[e for e in entries if (_date(as_of)-_date(e['day'])).days<=55]
    baseline=[e for e in entries if (_date(as_of)-_date(e['day'])).days<=27]
    recent_days=sorted(e['day'] for e in recent_entries)
    recent_span=(_date(recent_days[-1])-_date(recent_days[0])).days if recent_days else 0
    recent_counts=defaultdict(lambda:[0,0])
    for e in recent_entries:
        d=_date(e['day']); key=(d-timedelta(days=d.weekday())).isoformat()
        recent_counts[key][0]+=e['questions']; recent_counts[key][1]+=e['correct']
    recent=[{'date':d,'questions':v[0],'correct':v[1],'accuracy':v[1]/v[0]} for d,v in sorted(recent_counts.items())]
    model={'as_of':as_of,'weekly':weeks,'questions':n,'accuracy':correct/n if n else None,'interval':_interval(correct,n),
           'conviction':cc/cn if cn else None,'conviction_questions':cn,'topics':len(paths),'span':span,'fit':None,'trend_selected':False,
           'last_measurement':days[-1] if days else None,'recent_span':recent_span,
           'recent_questions':sum(e['questions'] for e in baseline),'recent_correct':sum(e['correct'] for e in baseline),
           'recent_topics':len({tuple(normalize_path(e['path'])) for e in baseline})}
    recent_n=sum(e['questions'] for e in recent_entries)
    recent_paths={tuple(normalize_path(e['path'])) for e in recent_entries}
    if len(recent)>=8 and recent_n>=300 and len(recent_paths)>=3 and recent_span>=49:
        errors=[]; reference=[]
        for stop in range(4,len(recent)):
            training=recent[:stop]; validation=recent[stop]
            prediction=_predict(_fit(training),validation['date'])
            stationary=sum(w['correct'] for w in training[-4:])/sum(w['questions'] for w in training[-4:])
            errors.append(abs(prediction-validation['accuracy'])); reference.append(abs(stationary-validation['accuracy']))
        if sum(errors)<.9*sum(reference): model.update(fit=_fit(recent),trend_selected=True)
        model['validation']={'trend_mae':sum(errors)/len(errors),'stationary_mae':sum(reference)/len(reference),'folds':len(errors)}
    return model


def performance_outlook(model,at):
    h=(_date(at)-_date(model['as_of'])).days
    result={'estimate':None,'lower':None,'upper':None,'method':'Sem base suficiente',
            'reason':'Registre questões novas, com acertos exatos, em dias e temas diferentes.'}
    if h<0: raise ValueError('Escolha hoje ou uma data futura.')
    if model['recent_questions']<30 or model['recent_topics']<2 or model['recent_span']<7: return result
    last=model['last_measurement']
    if (_date(model['as_of'])-_date(last)).days>21: return {**result,'reason':'A medição mais recente está antiga. Registre novos blocos para atualizar o cenário.'}
    if h>min(56,model['recent_span']): return {**result,'reason':'Esta data está além do horizonte sustentado pelo histórico. Volume e cobertura continuam disponíveis.'}
    n=model['recent_questions']; correct=model['recent_correct']
    estimate=_predict(model['fit'],at) if model['trend_selected'] else correct/n
    lo,hi=_interval(correct,n)
    spread=max(.05,(hi-lo)/2)*sqrt(1+h/max(7,model['recent_span']))
    return {'estimate':estimate,'lower':max(0,estimate-spread),'upper':min(1,estimate+spread),
            'method':'Tendência exploratória' if model['trend_selected'] else 'Mantendo o rendimento recente',
            'reason':'Faixa de cenários; não é intervalo de predição calibrado nem estimativa de nota na prova.'}
