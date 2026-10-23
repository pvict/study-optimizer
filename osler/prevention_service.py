"""Comparação preventiva e aplicação auditável de uma política temporária."""
from copy import deepcopy
from datetime import timedelta
from .planning import _date
from .planner_service import today_local,valid_date
from .study_models import AdaptiveProfile
from .study_calendar import forecast_calendar
from .study_prevention import summarize_risk,worsened_risks,PREVENTION_MODES


class PreventiveServiceMixin:
    def prevention_context(self,start,days):
        current=today_local().isoformat()
        valid_date(start)
        if type(days) is not int or not 1<=days<=90: raise ValueError('Escolha uma janela de1 a90dias.')
        if start<current or (_date(start)-_date(current)).days>=548: raise ValueError('Planeje de hoje até18meses à frente.')
        token=self.agenda.token()
        view=self.overview(current)
        profile=AdaptiveProfile(**view['profile'])
        if start>profile.exam_date: raise ValueError('O início deve ser anterior à prova.')
        end=min(_date(start)+timedelta(days=days-1),_date(current)+timedelta(days=547),_date(profile.exam_date)).isoformat()
        calendar=forecast_calendar(view['planning_states'],profile,current,(_date(end)-_date(current)).days+1,
                                   view['sessions'],self.store.days(),view['plan'],view['agenda'])
        summary=summarize_risk(calendar,start,end)
        candidates=sorted(summary['topics'],key=lambda r:(r['first_pending'],-r['importance'],r['path']))
        if token!=self.agenda.token(): raise ValueError('Os dados mudaram. Recalcule a previsão.')
        return {'start':start,'end':end,'days':days,'view':view,'calendar':calendar,'summary':summary,'candidates':candidates,'token':token}

    def preview_prevention(self,start,days,mode,selected=None,extra_questions=20):
        if mode not in PREVENTION_MODES: raise ValueError('Escolha uma estratégia preventiva reconhecida.')
        if type(extra_questions) is not int or not 0<=extra_questions<=300: raise ValueError('Adicional deve estar entre0 e300questões.')
        context=self.prevention_context(start,days)
        selected=list(selected) if selected is not None else [r['topic_id'] for r in context['candidates']]
        allowed={r['topic_id'] for r in context['candidates']}
        if not selected or len(set(selected))!=len(selected) or set(selected)-allowed: raise ValueError('Selecione temas com pendência prevista nesse período.')
        view=context['view']
        agenda=deepcopy(view['agenda'])
        policy={'start':start,'end':context['end'],'topics':selected}
        agenda.setdefault('policies',[]).append(policy)
        overrides={}
        if mode in {'reviews','extra'}:
            day=_date(start)
            while day<=_date(context['end']):
                key=day.isoformat()
                if agenda['overrides'].get(key,{}).get('mode') not in {'final_review','final_rest','mock_day'}:
                    overrides[key]={'mode':mode,'extra_questions':extra_questions}
                day+=timedelta(days=1)
            agenda['overrides'].update(overrides)
        proposed_view=self.overview(view['date'],_agenda_override=agenda)
        after_calendar=forecast_calendar(proposed_view['planning_states'],AdaptiveProfile(**view['profile']),view['date'],len(context['calendar']),
                                         view['sessions'],self.store.days(),proposed_view['plan'],agenda)
        before=context['summary']
        after=summarize_risk(after_calendar,start,context['end'])
        after_by_id={r['topic_id']:r for r in after['topics']}
        comparisons=[]
        for row in context['candidates']:
            if row['topic_id'] not in selected: continue
            future=after_by_id.get(row['topic_id'])
            earliest=(_date(row['due_date'])-timedelta(days=2)).isoformat()
            planned=[d['date'] for d in after_calendar if start<=d['date']<=context['end'] and d['date']>=earliest and
                     any(i['topic_id']==row['topic_id'] and i.get('preventive_priority') for i in d['items'])]
            comparisons.append({'topic_id':row['topic_id'],'path':row['path'],'due_date':row['due_date'],'before_first_pending':row['first_pending'],
                                'after_first_pending':future['first_pending'] if future else None,
                                'next_planned_review':min(planned) if planned else None})
        if context['token']!=self.agenda.token(): raise ValueError('Os dados mudaram. Recalcule a comparação.')
        before_ids={r['topic_id'] for r in before['topics']}
        after_ids={r['topic_id'] for r in after['topics']}
        return {'start':start,'end':context['end'],'days':days,'mode':mode,'selected':selected,'extra_questions':extra_questions,
                'created_day':view['date'],'token':context['token'],'policy':policy,'overrides':overrides,
                'before':before,'after':after,'comparison_rows':comparisons,
                'new_risk_topics':[r for r in after['topics'] if r['topic_id'] not in before_ids],
                'worsened_risk_topics':worsened_risks(before,after),
                'resolved_topics':sorted(before_ids-after_ids),
                'selected_before':summarize_risk(context['calendar'],start,context['end'],selected),
                'selected_after':summarize_risk(after_calendar,start,context['end'],selected)}

    def apply_prevention(self,preview):
        if preview['created_day']!=today_local().isoformat() or preview['token']!=self.agenda.token():
            raise ValueError('Os dados mudaram. Atualize a comparação antes de aplicar.')
        fresh=self.preview_prevention(preview['start'],preview['days'],preview['mode'],preview['selected'],preview['extra_questions'])
        if fresh!=preview: raise ValueError('A previsão mudou. Recalcule antes de aplicar.')
        # selected vazio protege reservas reais; política cobre todas as repetições elegíveis no período.
        event={**fresh,'kind':'reschedule.apply','scope':'preventive','preventive_selected':fresh['selected'],'selected':[],'rows':[],
               'cutoff':max((e['id'] for e in self.store.events()),default=0)}
        return self.agenda.append(event,fresh['token'])
