"""Comparação de rotinas sem alterar dados; ativação explícita e versionada."""
from dataclasses import replace
from datetime import timedelta
from .planner_service import today_local,valid_date
from .planning import _date
from .study_models import AdaptiveProfile
from .study_calendar import forecast_calendar
from .study_prevention import summarize_risk


class CapacityServiceMixin:
    def configure_workload(self,mode,expected_id):
        record=self.store.profile()
        if record['id']!=expected_id: raise ValueError('Os ajustes mudaram. Atualize a comparação antes de aplicar.')
        return self.store.save_profile(replace(AdaptiveProfile(**record['configured_profile']),workload_mode=mode),expected_id)

    def workload_comparison(self,start,days=14):
        valid_date(start)
        if type(days) is not int or not 1<=days<=90: raise ValueError('Compare de1 a90dias.')
        current=today_local().isoformat()
        if start<current or (_date(start)-_date(current)).days>547: raise ValueError('Escolha uma janela futura disponível.')
        token=self.agenda.token()
        view=self.overview(current)
        p=AdaptiveProfile(**view['profile'])
        end=min(_date(start)+timedelta(days=days-1),_date(current)+timedelta(days=547),_date(p.exam_date)).isoformat()
        if end<start: raise ValueError('A janela começa depois da prova de referência.')
        result={}
        for mode in ('fixed','adaptive'):
            calendar=forecast_calendar(view['planning_states'],replace(p,workload_mode=mode),current,
                                       (_date(end)-_date(current)).days+1,view['sessions'],self.store.days(),agenda=view['agenda'])
            summary=summarize_risk(calendar,start,end)
            window=[d for d in calendar if start<=d['date']<=end]
            result[mode]={**summary,'new_topics':len({i['topic_id'] for d in window for i in d['items'] if i.get('is_new_for_day')}),
                          'new_questions':sum(d['distribution']['planned_new'] for d in window),
                          'adjusted_days':sum(d.get('capacity',{}).get('effective_share',p.new_share)<p.new_share for d in window),
                          'unused_questions':sum(max(0,d['target_questions']-d['questions']-d['done_questions']) for d in window),
                          'max_daily_backlog':max((d['topic_backlog'] for d in window),default=0)}
        if token!=self.agenda.token(): raise ValueError('O plano mudou. Atualize a comparação.')
        return {**result,'start':start,'end':end,'days':len(window),'token':token,'profile_id':view['profile_id'],
                'mode':p.workload_mode,'reference_share':p.new_share,'max_questions':p.max_questions}
