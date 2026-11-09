from dataclasses import replace
from osler.adaptive_planning import topic_states,allocate_day
from osler.study_models import AdaptiveProfile
from osler.study_allocation import category_allocation
from test_adaptive_planning import topic


def test_sparse_planner_must_not_reduce_recommended_new_practice_to_one_question():
    p=AdaptiveProfile(max_questions=40,max_topics=2,new_share=.5,min_block=10,review_strategy='balanced_v2',return_mode='theme')
    rows=topic_states([topic('HighNew',total=1),topic('Review',answered=40)],[],[],{},'2026-10-15',p)
    for t in rows:t.update(recommended_questions=20,theme_recommended_questions=20)
    result=allocate_day(rows,p,None,'normal',[],'2026-10-15',question_target=40)
    new=next(t for t in result['items'] if t['topic_id']=='HighNew')
    assert new['questions']==20 and new['total']==1
    assert new['new_questions']==1 and new['external_bank_questions']==19 and new['repeat_questions']==0
    from osler.study_registration_ui import first_block_action
    assert first_block_action(new,'2026-10-15','balanced_v2')['mode']=='novas'
    reservation={**new,'date':'2026-10-15','original_due':'2026-10-15','remaining':20,'daily_proposal':True}
    preserved=allocate_day(rows,p,None,'normal',[],'2026-10-15',question_target=40,reservations=[reservation])
    assert next(t for t in preserved['items'] if t['topic_id']=='HighNew')['questions']==20


def test_feasible_protected_new_floor_is_not_traded_for_more_review_questions():
    p=AdaptiveProfile(max_questions=60,max_topics=2,new_share=.5,minimum_new_share=.2,workload_mode='adaptive',review_strategy='balanced_v2')
    rows=topic_states([topic('New1'),topic('New2'),topic('Review',answered=40)],[],[],{},'2026-10-15',p)
    for t in rows:
        new=t['topic_id']!='Review'
        t.update(recommended_questions=10 if new else 40,allocation_capacity=100,intake_protected=new)
    _,counts,distribution=category_allocation(rows,rows,p,60,60,[])
    assert distribution['planned_new']>=12
