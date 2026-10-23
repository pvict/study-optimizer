"""Revisão opcional de semanas alinhadas; sugestões nunca mudam a rotina."""
from collections import defaultdict
from datetime import timedelta
import json
from .models import normalize_path
from .planning import _date
from .planner_service import today_local
from .storage import utc_now
from .study_read_model import read_events,latest_active,waived_days


def validate_weekly(week_key,payload):
    day=_date(week_key)
    if day.weekday()!=0 or day>today_local(): raise ValueError('Escolha a segunda-feira da semana atual ou de uma semana anterior.')
    answers=payload['answers']
    for name in ('blocked','load_change'):
        if not isinstance(answers.get(name,''),str) or len(answers.get(name,''))>1000: raise ValueError('Resuma cada resposta em até 1000 caracteres.')
    if type(answers.get('needs_rest',False)) is not bool: raise ValueError('Informe se precisa de descanso.')
    if set(answers)-{'blocked','load_change','needs_rest'}: raise ValueError('Resposta de revisão semanal não reconhecida.')


class WeeklyReviewStore:
    def __init__(self,repo):
        self.repository=repo
        from .study_storage import StudyStore
        StudyStore(repo)

    def events(self): return [{**r,'review':r['data']} for r in read_events(self.repository,'weekly_reviews')]

    def active(self,week_key=None):
        rows=latest_active(self.events(),'week_key')
        return [r for r in rows if week_key is None or r['week_key']==week_key]

    def save(self,week_key,answers,*,expected_version=0,summary=None):
        payload={'answers':answers,'summary':summary or {}}
        validate_weekly(week_key,payload)
        return self._append(week_key,payload,expected_version,'save')

    def void(self,week_key,expected_version): return self._append(week_key,None,expected_version,'void')

    def _append(self,week_key,payload,expected_version,action):
        if type(expected_version) is not int or expected_version<0: raise ValueError('Versão inválida.')
        with self.repository._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM weekly_reviews WHERE week_key=? ORDER BY version DESC LIMIT 1',(week_key,)).fetchone()
            if (old['version'] if old else 0)!=expected_version or action=='void' and (not old or old['action']!='save'):
                raise ValueError('A revisão mudou em outra tela. Atualize antes de salvar.')
            encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False) if action=='save' else old['payload']
            event_id=db.execute('INSERT INTO weekly_reviews(week_key,version,action,payload,created_at) VALUES(?,?,?,?,?)',
                                (week_key,expected_version+1,action,encoded,utc_now())).lastrowid
        return next(r for r in self.events() if r['id']==event_id)


def weekly_summary(service,as_of):
    day=_date(as_of); monday=day-timedelta(days=day.weekday()); before=monday-timedelta(days=7)
    entries=latest_active(read_events(service.repository,'study_events'),'session_id')
    mocks=latest_active(read_events(service.repository,'mock_exams'),'exam_key')
    errors=latest_active(read_events(service.repository,'study_errors'),'error_key')
    plans=read_events(service.repository,'study_plan_runs'); waived=waived_days(plans,as_of)
    stats={}; series=defaultdict(dict)
    for name,start,end in [('current',monday,day),('previous',before,day-timedelta(days=7))]:
        first,last=start.isoformat(),end.isoformat()
        values=defaultdict(lambda:[0,0]); done=defaultdict(int)
        for row in entries:
            e=row['data']
            if not first<=e['day']<=last or e['kind']!='bloco': continue
            done[(e['day'],tuple(normalize_path(e['path'])))]+=e['questions']
            if e.get('correct') is not None and not row['session_id'].startswith('mock-'):
                v=values[(e['path'][0],'bloco_'+e['mode'],'')]; v[0]+=e['questions']; v[1]+=e['correct']
        week_mocks=[r for r in mocks if first<=r['data']['day']<=last]
        for row in week_mocks:
            mock=row['data']; context=(mock.get('institution') or 'Banca não informada')+' · '+mock['conditions']
            for area in mock.get('areas',[]):
                v=values[(area['area'],'simulado',context)]; v[0]+=area['questions']; v[1]+=area['correct']
        for key,(n,s) in values.items(): series[key][name]={'questions':n,'correct':s,'accuracy':s/n if n else None}
        saved={r['data']['plan']['date']:r['data']['plan'] for r in plans if r['data'].get('kind')=='daily_schedule'}
        expected=[(d,i) for d,p in saved.items() if first<=d<=last and d not in waived for i in p['items']]
        done_count=sum(done[(d,tuple(normalize_path(i['path'])))]>=i['questions'] for d,i in expected)
        stats[name]={'start':first,'end':last,'adhesion':{'planned_blocks':len(expected),'done_blocks':done_count,'rate':done_count/len(expected) if expected else None},
                     'open_errors':len([e for e in errors if e['day']<=as_of]) if name=='current' else None,
                     'mocks':len(week_mocks),'late_blocks':len(expected)-done_count}
    accuracy=[]
    for (area,source,context),values in sorted(series.items()):
        current=values.get('current',{'questions':0,'correct':0,'accuracy':None}); previous=values.get('previous',{'questions':0,'correct':0,'accuracy':None})
        change=100*(current['accuracy']-previous['accuracy']) if current['accuracy'] is not None and previous['accuracy'] is not None else None
        accuracy.append({'area':area,'source':source,'context':context,'current':current,'previous':previous,'change_pp':change})
    previous_errors=None
    for r in latest_active(read_events(service.repository,'weekly_reviews'),'week_key'):
        old=r['data'].get('summary',{}).get('current',{})
        if old.get('end')==stats['previous']['end']: previous_errors=old.get('open_errors')
    stats['previous']['open_errors']=previous_errors
    p=service.store.profile()['profile']; adherence=stats['current']['adhesion']
    suggestion=min(p['max_questions'],max(p['min_block'],round(p['max_questions']*.85))) if adherence['planned_blocks']>=5 and adherence['rate']<.6 else None
    if suggestion==p['max_questions']: suggestion=None
    return {**stats,'accuracy':accuracy,'changes':{'open_errors':stats['current']['open_errors']-previous_errors if previous_errors is not None else None,
            'late_blocks':stats['current']['late_blocks']-stats['previous']['late_blocks'],'mocks':stats['current']['mocks']-stats['previous']['mocks']},
            'suggested_questions':suggestion,'week_key':monday.isoformat()}


def absence_notice(service,as_of):
    days=[r['data']['day'] for r in latest_active(read_events(service.repository,'study_events'),'session_id') if r['data']['kind']!='acumulado' and r['data']['day']<=as_of]
    days+=[r['data']['day'] for r in latest_active(read_events(service.repository,'mock_exams'),'exam_key') if r['data']['day']<=as_of]
    if not days: return None
    age=(_date(as_of)-_date(max(days))).days
    return {'days':age,'last_record':max(days)} if age>=3 else None
