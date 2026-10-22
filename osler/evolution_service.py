"""Projeção read-only apoiada no mesmo calendário usado pelo plano."""
from dataclasses import replace
from datetime import timedelta
from .planner_service import today_local
from .study_models import AdaptiveProfile
from .planning import _date
from .study_calendar import forecast_calendar
from .study_evolution import evolution_snapshot
from .evolution_performance import performance_history


class EvolutionServiceMixin:
    def evolution_context(self,questions=None):
        as_of=today_local().isoformat(); token=self.agenda.token()
        view=self.overview(as_of); profile=AdaptiveProfile(**view['profile'])
        settings=self.store.days()
        if questions is not None:
            profile=replace(profile,max_questions=questions).validate()
            settings={d:{**s,'questions':questions} for d,s in settings.items()}
        end=max(as_of,min(profile.exam_date,(_date(as_of)+timedelta(days=547)).isoformat()))
        calendar=forecast_calendar(view['planning_states'],profile,as_of,(_date(end)-_date(as_of)).days+1,
                                   view['sessions'],settings,agenda=view['agenda']) if profile.exam_date>=as_of else []
        result={'as_of':as_of,'end':end,'exam_date':profile.exam_date,'start_date':profile.start_date,
                'exam_in_horizon':profile.exam_date<=end,'scenario_questions':questions,'profile':profile.to_dict(),
                'snapshot':evolution_snapshot(view['states'],view['sessions'],calendar,as_of,profile.max_contact_gap),
                'performance':performance_history(view['sessions'],as_of),'token':token,
                'incidence_warnings':view['incidence']['warnings'],
                'incidence_coverage':view['incidence']['coverage']}
        if token!=self.agenda.token(): raise ValueError('Seu plano mudou. Atualize a Evolução para recalcular.')
        return result
