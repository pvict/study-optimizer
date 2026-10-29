"""Resumos de apresentação a partir de registros; não planeja nem grava estudo."""
from datetime import datetime,timedelta
from math import ceil
from zoneinfo import ZoneInfo
from .planning import _date


def date_label(day):
    d=_date(day)
    weekdays=['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
    months=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
    return f'{weekdays[d.weekday()]}, {d.day} de {months[d.month-1]}'


def hero_state(view):
    p=view['plan']
    if not view['states']: return 'empty'
    if p.get('not_started'): return 'not_started'
    if p.get('routine_override',{}).get('mode') in {'mock_day','mock_reserved'}: return 'mock'
    if p['kind']=='descanso': return 'rest'
    if p['items']:return 'study'
    return 'complete' if p['target_questions'] and p['done_questions']>=p['target_questions'] else 'free'


def entry_clock(event):
    try:
        stamp=datetime.fromisoformat(event.get('created_at',''))
        return stamp.astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M') if stamp.tzinfo else None
    except (ValueError,TypeError): return None


def pause_remaining(deadline,now):
    return None if deadline is None else max(0,ceil(deadline-now))


def week_summary(view,settings,guide_days=(),exam=None,mock_days=()):
    today=_date(view['date']);start=today-timedelta(days=today.weekday())
    first=start.isoformat();last=today.isoformat();previous=(start-timedelta(days=7)).isoformat()
    events=[s['entry'] for s in view['sessions'] if s['entry']['kind']!='acumulado' and s['entry']['day']<=last]
    blocks=[e for e in events if e['kind']=='bloco']
    from .exam_practice import area_extra_volume
    extra=area_extra_volume(view.get('agenda',{}).get('area_results',[]),view['sessions'],last)
    week=[e for e in blocks if first<=e['day']<=last]
    new=[e for e in week if e['mode']=='novas' and not e.get('review_of')]
    known=[e for e in new if e.get('correct') is not None]
    n=sum(e['questions'] for e in known);correct=sum(e['correct'] for e in known)
    days=[]
    for i in range(7):
        day=(start+timedelta(days=i)).isoformat()
        actual=[e for e in events if e['day']==day]
        guides=[r for r in guide_days if r['day']==day]
        q=sum(e['questions'] for e in actual)+extra.get(day,0)
        config=settings.get(day,{})
        goal=view['plan']['target_questions'] if day==last else config.get('questions')
        rest=config.get('kind')=='descanso' or any(r['status']=='descanso' for r in guides)
        if day in mock_days:status='done'
        elif actual or extra.get(day,0) or any(r['status'] in {'feito','parcial'} for r in guides):
            status='partial' if (goal and q<goal) or any(r['status']=='parcial' for r in guides) else 'done'
        else: status='rest' if rest else 'future' if day>last else 'missing'
        days.append({'date':day,'status':status,'questions':q})
    return {'days':days,'study_days':sum(d['status'] in {'done','partial'} for d in days),
            'rest_days':sum(d['status']=='rest' for d in days),'questions':sum(e['questions'] for e in week)+sum(n for day,n in extra.items() if first<=day<=last),
            'previous_questions':sum(e['questions'] for e in blocks if previous<=e['day']<first)+sum(n for day,n in extra.items() if previous<=day<first),
            'new_n':n,'new_correct':correct,'new_accuracy':correct/n if n else None,
            'new_unknown':sum(e['questions'] for e in new if e.get('correct') is None),
            'mastered':sum(t.get('learning_state')=='dominado' and not t.get('historical_aggregate') for t in view['states']) if view['states'] else None,
            'exam_days':(_date(exam['exam_date'])-today).days if exam else None}
