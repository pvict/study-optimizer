"""Mudança versionada de política com prévia reproduzível e histórico local."""
from dataclasses import replace
from .study_models import AdaptiveProfile
from .planner_service import today_local
from .planning import _date
from .study_calendar import forecast_calendar
from .mock_schedule import calendar_changes
from .balanced_reviews import STRATEGIES


class ReviewStrategyServiceMixin:
    def review_strategy_history(self):
        return [r for r in self.agenda.records() if r.get('kind')=='review_strategy.change']

    def preview_review_strategy(self,strategy):
        if strategy not in STRATEGIES: raise ValueError('Escolha uma estratégia de revisão válida.')
        day=today_local().isoformat(); token=self.agenda.token(); record=self.store.profile()
        effective=replace(AdaptiveProfile(**record['profile']),review_strategy=strategy)
        before=self.overview(day); after=self.overview(day,_profile_override=effective.to_dict())
        count=max(1,min(28,(_date(effective.exam_date)-_date(day)).days+1))
        def forecast(view):
            return forecast_calendar(view['planning_states'],AdaptiveProfile(**view['profile']),day,count,
                view['sessions'],self.store.days(),view['plan'],view['agenda'],next_contact_only=True)
        a,b=forecast(before),forecast(after)
        def summary(view):
            p=view['profile']; plan=view['plan']
            return {'strategy':p['review_strategy'],'max_questions':p['max_questions'],'max_topics':p['max_topics'],
                    'target_accuracy':p['target_accuracy'],'area_targets':p['area_targets'],'exam_date':p['exam_date'],
                    'today_questions':plan['questions'],'done_questions':plan['done_questions'],
                    'today_target':plan['target_questions'],
                    'today':[{'topic_id':t['topic_id'],'path':t['path'],'questions':t['questions']} for t in plan['items']]}
        old={t['topic_id']:t for t in before['states']}; changes=[]
        fields=['theme_recommended_questions','review_interval_days','theme_review_due','priority','learning_state']
        for t in after['states']:
            previous=old.get(t['topic_id'])
            if previous and any(previous.get(k)!=t.get(k) for k in fields):
                changes.append({'topic_id':t['topic_id'],'path':t['path'],
                    'before':{k:previous.get(k) for k in fields},'after':{k:t.get(k) for k in fields}})
        if token!=self.agenda.token(): raise ValueError('Os dados mudaram. Recalcule a prévia.')
        return {'strategy':strategy,'token':token,'created_day':day,'profile_id':record['id'],
                'before':summary(before),'after':summary(after),'state_changes':changes,
                'contacts':calendar_changes(a,b,include_quantities=True,include_additions=True),'window_end':b[-1]['date']}

    def apply_review_strategy(self,preview):
        if preview['token']!=self.agenda.token() or preview['created_day']!=today_local().isoformat():
            raise ValueError('Os dados mudaram. Recalcule a prévia.')
        if self.preview_review_strategy(preview['strategy'])!=preview: raise ValueError('A prévia mudou. Recalcule antes de aplicar.')
        record=self.store.profile()
        return self.store.save_profile(replace(AdaptiveProfile(**record['configured_profile']),review_strategy=preview['strategy']),
            preview['profile_id'],expected_planning_token=preview['token'],audit_preview=preview)
