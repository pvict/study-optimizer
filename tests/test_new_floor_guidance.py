from copy import deepcopy
from dataclasses import replace
import unittest
from osler.adaptive_planning import allocate_day,topic_states
from osler.study_models import AdaptiveProfile


def scenario(*,questions=60,slots=2,share=.5,minimum=.2,block=10,include_new=True,competing_review=False):
    p=AdaptiveProfile(max_questions=questions,max_topics=slots,new_share=share,
                      minimum_new_share=minimum,min_block=block,workload_mode='adaptive')
    topics=[{'topic_id':n,'path':['Area',n],'total':100,'answered_pdf':40 if n.startswith('R') else 0,
             'pdf_accuracy':{'value':80 if n.startswith('R') else None,'operator':'=','raw':'-'},
             'report_date':'2026-11-15','studied_cards':0} for n in ['R1','R2']+(['R3'] if competing_review else [])+(['N'] if include_new else [])]
    states=topic_states(topics,[],[],{},'2026-11-16',p)
    reservations=[{'topic_id':n,'path':['Area',n],'date':'2026-11-16','original_due':'2026-11-01',
                   'remaining':20,'questions':20,'manual_date':True} for n in ['R1','R2']]
    return states,p,dict(minutes=None,kind='normal',sessions=[],as_of='2026-11-16',
                         question_target=questions,reservations=reservations)


class NewFloorGuidance(unittest.TestCase):
    def test_real_new_questions_are_not_replaced_by_allocation_credit(self):
        states,p,args=scenario()
        args['sessions']=[{'id':1,'session_id':'x','entry':{'path':['Area','N'],'day':'2026-11-16',
            'kind':'bloco','mode':'novas','questions':15,'correct':12,'minutes':None}}]
        plan=allocate_day(states,p,**args,allocation_credits={'x':5})
        self.assertEqual(plan['capacity']['new_floor']['done'],15)
        self.assertEqual(plan['capacity']['new_floor']['missing'],0)

    def test_dispensed_new_block_is_removed_before_counts_and_options(self):
        from osler.planner_completion import apply_completions
        states,p,args=scenario(slots=3)
        agenda={'rows':[],'planner_completions':[{'id':1,'day':'2026-11-16','topic_id':'N',
                    'manual_partial':True,'skipped_questions':20}]}
        def finalize(plan):apply_completions(plan,agenda,'2026-11-16')
        plan=allocate_day(states,p,**args,diagnose_new_floor=True,finalize_plan=finalize)
        info=plan['capacity']['new_floor']
        self.assertEqual(info['planned'],0)
        self.assertEqual(info['missing'],12)
        self.assertEqual(info['options'],[])

    def test_manual_extras_are_counted_in_protected_work_without_double_counting(self):
        states,p,args=scenario(questions=40,competing_review=True)
        extra=next(t for t in states if t['topic_id']=='R3')
        args['extra_topics']=[{**extra,'extra_id':'extra','requested':8,'after_event_id':0}]
        info=allocate_day(states,p,**args,diagnose_new_floor=True)['capacity']['new_floor']
        self.assertEqual(info['protected_questions'],48)
        self.assertEqual(info['protected_topics'],3)
        self.assertEqual(info['remaining_questions'],0)

    def test_small_inventory_is_not_explained_as_reserved_work(self):
        states,p,args=scenario()
        states=[{**t,'total':2,'available_new':2,'recommended_questions':2} for t in states if t['topic_id']=='N']
        args['reservations']=[]
        info=allocate_day(states,p,**args,diagnose_new_floor=True)['capacity']['new_floor']
        self.assertEqual(info['missing'],10)
        self.assertEqual(info['new_capacity'],2)
        self.assertEqual(info['reason'],'limited_candidates')

    def test_notice_reports_missing_questions_from_the_final_plan(self):
        states,p,args=scenario()
        plan=allocate_day(states,p,**args)
        info=plan['capacity'].get('new_floor',{})
        self.assertEqual(info.get('required'),12)
        self.assertEqual(info.get('done'),0)
        self.assertEqual(info.get('planned'),0)
        self.assertEqual(info.get('missing'),12)

    def test_one_more_topic_fits_the_minimum_without_adding_questions_or_moving_reservations(self):
        states,p,args=scenario();before=deepcopy((states,args))
        plan=allocate_day(states,p,**args,diagnose_new_floor=True)
        info=plan['capacity']['new_floor']
        option=next(r for r in info['options'] if r['max_topics']==3 and r['new_share']==.5)
        self.assertGreaterEqual(option['planned_new'],12)
        self.assertEqual(option['target_questions'],60)
        trial=allocate_day(states,replace(p,max_topics=option['max_topics'],new_share=option['new_share']),**args)
        reserved={r['topic_id']:r['questions'] for r in trial['items'] if r.get('rescheduled')}
        self.assertEqual(reserved,{'R1':20,'R2':20})
        self.assertEqual((states,args),before)

    def test_no_candidates_is_not_solved_by_fabricating_questions(self):
        states,p,args=scenario(include_new=False)
        info=allocate_day(states,p,**args,diagnose_new_floor=True)['capacity']['new_floor']
        self.assertEqual(info['missing'],12)
        self.assertEqual(info['options'],[])
        self.assertEqual(info['reason'],'no_candidates')

    def test_percentage_adjustment_is_verified_with_the_same_quantity(self):
        states,p,args=scenario(slots=3,share=.05,competing_review=True)
        info=allocate_day(states,p,**args,diagnose_new_floor=True)['capacity']['new_floor']
        option=next(r for r in info['options'] if r['new_share']==.2)
        self.assertEqual(option['max_topics'],3)
        self.assertEqual(option['target_questions'],60)
        self.assertEqual(option['planned_new'],20)

    def test_both_controls_are_reported_when_neither_alone_fits(self):
        states,p,args=scenario(slots=1,share=.05,competing_review=True)
        info=allocate_day(states,p,**args,diagnose_new_floor=True)['capacity']['new_floor']
        self.assertEqual([(r['max_topics'],r['new_share']) for r in info['options']],[(3,.2)])

    def test_effective_share_is_translated_to_the_setting_the_user_edits(self):
        states,p,args=scenario(slots=3,share=.05,competing_review=True)
        info=allocate_day(states,p,**args,diagnose_new_floor=True,new_floor_control_share=.1)['capacity']['new_floor']
        option=info['options'][0]
        self.assertEqual(option['control_new_share'],.35)
        self.assertEqual(option['new_share'],.175)

    def test_no_spare_budget_does_not_suggest_only_more_topics(self):
        states,p,args=scenario(questions=40)
        info=allocate_day(states,p,**args,diagnose_new_floor=True)['capacity']['new_floor']
        self.assertEqual(info['missing'],10)
        self.assertEqual(info['options'],[])

    def test_new_questions_already_reserved_count_toward_the_minimum(self):
        states,p,args=scenario()
        args['reservations']=[{'topic_id':'N','path':['Area','N'],'date':'2026-11-16',
                               'original_due':'2026-11-01','remaining':20,'questions':20,'manual_date':True}]
        plan=allocate_day(states,p,**args)
        self.assertEqual(plan['capacity'].get('new_floor',{}).get('missing'),0)
        self.assertFalse(plan['capacity']['new_floor_shortfall'])


if __name__=='__main__':unittest.main()
