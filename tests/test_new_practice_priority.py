from dataclasses import replace
from osler.adaptive_planning import topic_states,allocate_day
from osler.study_models import AdaptiveProfile
from osler.study_allocation import category_allocation
from test_adaptive_planning import topic


def test_sparse_planner_keeps_recommended_new_practice_outside_automatic_slots():
    p=AdaptiveProfile(max_questions=40,max_topics=2,new_share=.5,min_block=10,review_strategy='balanced_v2',return_mode='theme')
    rows=topic_states([topic('HighNew',total=1),topic('New'),topic('Review',answered=40)],[],[],{},'2026-10-15',p)
    for t in rows:t.update(recommended_questions=20,theme_recommended_questions=20)
    result=allocate_day(rows,p,None,'normal',[],'2026-10-15',question_target=40)
    small=next(t for t in rows if t['topic_id']=='HighNew')
    assert small['recommended_questions']==20 and small['total']==1
    assert small['complement_per_block']>=p.min_block-1
    assert {t['topic_id'] for t in result['items']}=={'New','Review'}
    reservation={**small,'date':'2026-10-15','original_due':'2026-10-15','remaining':20,'daily_proposal':True}
    preserved=allocate_day(rows,p,None,'normal',[],'2026-10-15',question_target=40,reservations=[reservation])
    assert {t['topic_id'] for t in preserved['items']}=={'New','Review'}


def test_feasible_protected_new_floor_is_not_traded_for_more_review_questions():
    p=AdaptiveProfile(max_questions=60,max_topics=2,new_share=.5,minimum_new_share=.2,workload_mode='adaptive',review_strategy='balanced_v2')
    rows=topic_states([topic('New1'),topic('New2'),topic('Review',answered=40)],[],[],{},'2026-10-15',p)
    for t in rows:
        new=t['topic_id']!='Review'
        t.update(recommended_questions=10 if new else 40,allocation_capacity=100,intake_protected=new)
    _,counts,distribution=category_allocation(rows,rows,p,60,60,[])
    assert distribution['planned_new']>=12
