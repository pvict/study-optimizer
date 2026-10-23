"""Prévia de importância por prova, sem retirar instituições silenciosamente."""
from dataclasses import replace
from datetime import timedelta
from .study_models import AdaptiveProfile
from .planner_service import today_local
from .planning import _date
from .exam_weight_policy import policy_inputs,exam_weight_policy
from .study_calendar import forecast_calendar
from .mock_schedule import calendar_changes


def _proposed_profile(record,weights,approach_days=None):
    original=AdaptiveProfile(**record['configured_profile'])
    return replace(original,institution_weights={name:1 for name in original.institution_weights},
                   exam_weights=dict(weights),exam_weight_basis='',
                   approach_days=original.approach_days if approach_days is None else approach_days).validate()


class ExamWeightServiceMixin:
    def exam_weight_eligibility(self,weights):
        p=_proposed_profile(self.store.profile(),weights)
        with self.repository._connection() as db: inputs=policy_inputs(db)
        return exam_weight_policy(p,inputs,today_local().isoformat())

    def preview_exam_weights(self,weights,approach_days):
        current=today_local().isoformat(); token=self.agenda.token(); record=self.store.profile()
        proposed=_proposed_profile(record,weights,approach_days)
        with self.repository._connection() as db: inputs=policy_inputs(db)
        policy=exam_weight_policy(proposed,inputs,current)
        if not policy['allowed']: raise ValueError(policy['reason'])
        effective=replace(AdaptiveProfile(**record['profile']),exam_weights=dict(weights),approach_days=approach_days,
                          institution_weights=policy['effective_weights'],exam_weight_basis=policy['basis'])
        before=self.overview(current); after=self.overview(current,_profile_override=effective.to_dict())
        count=max(1,min(28,(_date(effective.exam_date)-_date(current)).days+1))
        def forecast(view):
            return forecast_calendar(view['planning_states'],AdaptiveProfile(**view['profile']),current,count,
                                     view['sessions'],self.store.days(),view['plan'],view['agenda'],next_contact_only=True)
        calendar_before,calendar_after=forecast(before),forecast(after)
        def summary(view):
            return {'weights':view['profile']['institution_weights'],'coverage':view['incidence']['coverage'],
                    'contexts':view['incidence']['contexts'],'warnings':view['incidence']['warnings'],
                    'max_questions':view['profile']['max_questions'],'max_topics':view['profile']['max_topics'],
                    'approach_days':view['profile']['approach_days'],'exam_date':view['profile']['exam_date'],
                    'today':[{'topic_id':t['topic_id'],'path':t['path'],'questions':t['questions']} for t in view['plan']['items']]}
        by_id={t['topic_id']:t for t in before['states']}; ranks=[]
        for t in after['states']:
            old=by_id.get(t['topic_id'])
            if old and any(old.get(k)!=t.get(k) for k in ['priority','learning_state','importance']):
                ranks.append({'path':t['path'],'before_priority':old['priority'],'after_priority':t['priority'],
                              'before_importance':old['importance'],'after_importance':t['importance'],
                              'before_state':old['learning_state'],'after_state':t['learning_state']})
        if token!=self.agenda.token(): raise ValueError('Os dados mudaram. Recalcule a prévia.')
        return {'weights':dict(weights),'approach_days':approach_days,'profile_id':record['id'],'created_day':current,'token':token,
                'basis':policy['basis'],
                'legacy_weights_before':record['configured_profile']['institution_weights'],
                'legacy_weights_after':proposed.institution_weights,
                'before':summary(before),'after':summary(after),'sources':policy['sources'],'rank_changes':ranks,
                'topic_changes':calendar_changes(calendar_before,calendar_after,include_quantities=True,include_additions=True),
                'window_end':calendar_after[-1]['date']}

    def apply_exam_weights(self,preview):
        if preview['token']!=self.agenda.token() or preview['created_day']!=today_local().isoformat(): raise ValueError('Os dados mudaram. Recalcule a prévia.')
        fresh=self.preview_exam_weights(preview['weights'],preview['approach_days'])
        if fresh!=preview: raise ValueError('A prévia mudou. Recalcule antes de aplicar.')
        record=self.store.profile()
        # Save_profile revalida as fontes e a versão dentro da transação.
        return self.store.save_profile(replace(_proposed_profile(record,preview['weights'],preview['approach_days']),
             exam_weight_basis=preview['basis']),preview['profile_id'],expected_planning_token=preview['token'])
