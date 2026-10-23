"""Prévia de corte com efeito condicional; grava somente no StudyAgenda."""
from datetime import timedelta
from copy import deepcopy
from .planning import _date
from .planner_service import today_local
from .study_models import AdaptiveProfile
from .study_triage_policy import propose_triage,apply_triage
from .study_calendar import forecast_calendar


class TriageServiceMixin:
    def preview_triage(self,days=28,frequency_factor=1.5,defer_days=0):
        if type(days) is not int or not 1<=days<=548: raise ValueError('Escolha uma janela de 1 a 548 dias.')
        current=today_local().isoformat(); token=self.agenda.token(); view=self.overview(current)
        p=AdaptiveProfile(**view['profile']); end=min(p.exam_date,(_date(current)+timedelta(days=days-1)).isoformat())
        if end<current: raise ValueError('A data da prova passou. Confira Minhas provas.')
        count=(_date(end)-_date(current)).days+1
        calendar=forecast_calendar(view['planning_states'],p,current,count,view['sessions'],self.store.days(),view['plan'],view['agenda'])
        report=propose_triage(view['planning_states'],calendar,current,end,frequency_factor=frequency_factor,max_gap=p.max_contact_gap,defer_days=defer_days)
        rows=[r for r in report['rows'] if r['action']!='manter']
        policy={'start':current,'end':end,'rows':rows}
        agenda=deepcopy(view['agenda']); agenda.setdefault('triage_policies',[]).append(policy)
        proposed=self.overview(current,_agenda_override=agenda)
        after_calendar=forecast_calendar(proposed['planning_states'],p,current,count,view['sessions'],self.store.days(),proposed['plan'],agenda)
        if token!=self.agenda.token(): raise ValueError('Os dados mudaram. Recalcule a prévia.')
        return {'created_day':current,'token':token,'days':days,'frequency_factor':frequency_factor,'defer_days':defer_days,
                'before':{'demand_questions':report['demand_questions'],'capacity_questions':report['capacity_questions'],'deficit_questions':report['deficit_questions']},
                'after':{'demand_questions':report['after_demand_questions'],'capacity_questions':report['capacity_questions'],'deficit_questions':report['after_deficit_questions']},
                'projected_questions_before':sum(d['questions'] for d in calendar),'projected_questions_after':sum(d['questions'] for d in after_calendar),
                'rows':report['rows'],'policy':policy}

    def apply_triage(self,preview):
        if preview['token']!=self.agenda.token() or preview['created_day']!=today_local().isoformat(): raise ValueError('Os dados mudaram. Refaça a prévia.')
        fresh=self.preview_triage(preview['days'],preview['frequency_factor'],preview['defer_days'])
        if fresh!=preview or not fresh['policy']['rows']: raise ValueError('Nenhuma redução segura disponível ou prévia alterada.')
        return self.agenda.append({**fresh,'kind':'reschedule.apply','scope':'triage','selected':[],'rows':[],
                                  'cutoff':max((e['id'] for e in self.store.events()),default=0)},fresh['token'])
