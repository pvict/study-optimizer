"""Revisão final temporária: reservas explícitas, sem fabricar estudo ou dívida."""
from collections import Counter
from datetime import timedelta
from .models import normalize_path
from .planning import _date,_number
from .planner_service import today_local,valid_date
from .exam_goals import active_exams


def special_config(config,override):
    if override.get('mode') not in {'final_review','final_rest','mock_day','mock_reserved'}: return config
    return {**config,'questions':override.get('questions',config['questions']),
            'kind':'descanso' if override['mode'] in {'final_rest','mock_day','mock_reserved'} else config['kind'],
            'extra_topics':[]}


def final_reservations(override,day,sessions):
    used=Counter()
    for s in sessions:
        e=s['entry']
        if e['day']==day and e['kind']=='bloco' and s.get('first_event_id',s.get('id',0))>override.get('after_event_id',0):
            used[tuple(normalize_path(e['path']))]+=e['questions']
    return [{**r,'remaining':max(0,r['questions']-used[tuple(normalize_path(r['path']))]),
             'original_due':r['date'],'final_review':True} for r in override.get('rows',[])]


class FinalReviewServiceMixin:
    def exam_dates(self,as_of=None):
        current=as_of or today_local().isoformat()
        dates=[]
        for e in active_exams(self.repository):
            for field,label in [('exam_date','Prova'),('registration_deadline','Inscrição até')]:
                day=e['target'].get(field)
                if day: dates.append({'date':day,'kind':field,'label':label,'institution':e['target']['institution'],
                                      'target_id':e['target_id'],'days_left':(_date(day)-_date(current)).days})
        return sorted(dates,key=lambda r:(r['date'],r['kind'],r['institution']))

    def preview_final_review(self,target_id,start,questions):
        valid_date(start)
        _number(questions,'Questões por dia',integer=True,positive=True,maximum=1000)
        current=today_local().isoformat()
        token=self.agenda.token()
        exam=next((e for e in active_exams(self.repository) if e['target_id']==target_id),None)
        if not exam: raise ValueError('Escolha uma prova cadastrada ativa.')
        end=exam['target']['exam_date']
        duration=(_date(end)-_date(start)).days
        if not 2<=duration<=14 or start<current or (_date(end)-_date(current)).days>=548:
            raise ValueError('Escolha início entre 2 e 14 dias antes da prova, a partir de hoje. A véspera é descanso.')
        view=self.overview(current)
        if view['profile'].get('start_date') and start<view['profile']['start_date']:
            raise ValueError('A revisão final deve começar depois do início do cronograma.')
        from .study_errors import ErrorStore
        errors={tuple(p) for p in [r['path'] for r in ErrorStore(self.repository).active(current)]}
        candidates=sorted(view['planning_states'],key=lambda t:(tuple(normalize_path(t['path'])) not in errors,
                          -t['importance'],t['performance'].get('observed') if t['performance'].get('observed') is not None else 1,
                          -t['score'],t['path']))
        rest=(_date(end)-timedelta(days=1)).isoformat()
        settings=self.store.days()
        cutoff=max((e['id'] for e in self.store.events()),default=0)
        overrides={}; rows=[]; available=list(candidates)
        day=_date(start)
        while day<_date(end):
            key=day.isoformat()
            config=settings.get(key,{'kind':'normal','questions':view['profile']['max_questions']})
            old=view['agenda']['overrides'].get(key,{})
            if key==rest:
                if old.get('mode') in {'mock_day','mock_reserved'}: raise ValueError('Há um simulado na véspera da prova. Mova esse simulado antes de reservar o descanso final.')
                overrides[key]={'mode':'final_rest','questions':questions,'exam_id':target_id}
            elif config['kind']!='descanso' and old.get('mode') not in {'mock_day','mock_reserved','final_rest'}:
                used=sum(s['entry']['questions'] for s in view['sessions'] if s['entry']['kind']=='bloco' and s['entry']['day']==key)
                budget=max(0,questions-used)
                planned=[]
                for t in list(available):
                    if len(planned)>=view['profile']['max_topics']: break
                    q=min(t['total'],t['recommended_questions'],budget)
                    if q<min(t['total'],view['profile']['min_block']): continue
                    r={'topic_id':t['topic_id'],'path':t['path'],'date':key,'questions':q,
                       'basis':'Erro aberto' if tuple(normalize_path(t['path'])) in errors else 'Incidência e desempenho'}
                    planned.append(r); rows.append(r); budget-=q; available.remove(t)
                overrides[key]={'mode':'final_review','questions':questions,'rows':planned,'exam_id':target_id,'after_event_id':cutoff}
            day+=timedelta(days=1)
        if self.agenda.token()!=token: raise ValueError('Os dados mudaram. Recalcule a prévia.')
        return {'target_id':target_id,'start':start,'exam_date':end,'questions':questions,'rest_day':rest,
                'rows':rows,'overrides':overrides,'created_day':current,'token':token,
                'replaced_days':list(overrides),'unassigned_topics':len(available)}

    def apply_final_review(self,preview):
        if preview['created_day']!=today_local().isoformat() or preview['token']!=self.agenda.token():
            raise ValueError('O plano mudou. Recalcule a revisão final antes de aplicar.')
        fresh=self.preview_final_review(preview['target_id'],preview['start'],preview['questions'])
        if fresh!=preview: raise ValueError('A revisão mudou. Recalcule a prévia.')
        # Reservas por dia expiram, em vez de se acumularem como dívida.
        return self.agenda.append({**fresh,'kind':'reschedule.apply','scope':'final_review','selected':[],
                                  'preview_rows':fresh['rows'],'rows':[],
                                  'cutoff':max((e['id'] for e in self.store.events()),default=0)},fresh['token'])

    def preview_mock_day(self,exam_key,expected_version):
        from .mock_exams import MockExamStore
        record=next((r for r in MockExamStore(self.repository).active() if r['exam_key']==exam_key),None)
        if not record or record['version']!=expected_version: raise ValueError('O simulado mudou. Atualize a tela.')
        mock=record.get('exam',record.get('mock',record.get('data')))
        if mock.get('practice_id'): raise ValueError('Treinos por área usam apenas parte da meta; não dispensam o dia inteiro.')
        day=mock['day']
        target=self.store.day(day,self.store.profile()['profile']['max_questions'])['settings']['questions']
        return {'exam_key':exam_key,'version':expected_version,'day':day,'questions':mock['questions'],
                'replaced_questions':target,'token':self.agenda.token(),'created_day':today_local().isoformat()}

    def mark_mock_day(self,exam_key,expected_version,preview=None):
        fresh=self.preview_mock_day(exam_key,expected_version)
        if preview is None or fresh!=preview: raise ValueError('Confira a prévia atual antes de marcar o dia do simulado.')
        return self.agenda.append({'kind':'reschedule.apply','scope':'mock_day','selected':[],'rows':[],
                                  'created_day':fresh['created_day'],'cutoff':0,
                                  'overrides':{fresh['day']:{'mode':'mock_day','questions':fresh['replaced_questions'],
                                                          'exam_key':exam_key,'mock_questions':fresh['questions']}}},fresh['token'])
