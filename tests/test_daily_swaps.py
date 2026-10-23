from copy import deepcopy
import pytest

from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from osler.study_models import AdaptiveProfile,StudyEntry
from test_adaptive_planning import topic


def service_fixture(tmp_path,monkeypatch):
    service=AdaptiveService(Repository(tmp_path))
    topics=[{**topic(name),'is_leaf':True} for name in ['A','B','C','D']]
    topics.append({**topic('Review',answered=40),'is_leaf':True})
    monkeypatch.setattr(service,'catalog',lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None}))
    service.store.save_profile(AdaptiveProfile(max_questions=20,max_topics=1,new_share=1),0)
    return service,topics


def test_suggestion_keeps_type_and_prefers_equal_priority():
    from osler.study_swaps import replacement_candidates
    original={'topic_id':'A','questions':20,'is_new_for_day':True,'status':'sem_registro','priority':'alta','score':.2}
    def candidate(name,new=True,priority='alta',score=.2,total=100):
        return {**original,'topic_id':name,'path':['Area',name],'total':total,'is_leaf':True,
                'is_new_for_day':new,'priority':priority,'score':score}
    states=[candidate('wrong-type',False),candidate('wrong-priority',priority='normal'),
            candidate('best',score=.19),candidate('tiny',total=5),candidate('already')]
    before=deepcopy(states)
    result=replacement_candidates(original,states,{'already'},'2026-10-15')
    assert result['recommended']['topic_id']=='best'
    assert 'wrong-type' in {s['topic_id'] for s in result['manual']}
    assert not {'tiny','already'} & {s['topic_id'] for s in result['manual']}
    assert states==before


def test_swap_is_persistent_counts_remaining_and_does_not_create_study(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    before=service.overview('2026-10-15')
    original=before['plan']['items'][0]
    options=service.swap_options('2026-10-15',original['topic_id'])
    target=options['recommended']['topic_id']
    slot=service.swap_topic('2026-10-15',original['topic_id'],target,options['token'],'recommended')
    changed=service.overview('2026-10-15')
    assert [(i['topic_id'],i['questions']) for i in changed['plan']['items']]==[(target,20)]
    assert changed['plan']['target_questions']==before['plan']['target_questions']==20
    assert not service.store.active('2026-10-15')
    for old,new in zip(before['states'],changed['states']):
        for field in ['performance','confidence','spacing','last_contact','recorded_attempts']:
            assert old[field]==new[field]
    selected=next(t for t in topics if t['topic_id']==target)
    service.save_entry(StudyEntry(selected['path'],'2026-10-15',10,9),'partial')
    partial=service.overview('2026-10-15')
    assert [(i['topic_id'],i['questions']) for i in partial['plan']['items']]==[(target,10)]
    assert partial['plan']['done_questions']==10
    assert partial['plan']['items'][0]['day_swap_id']==slot


def test_manual_can_change_type_and_undo_preserves_study_and_history(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    options=service.swap_options('2026-10-15','A')
    slot=service.swap_topic('2026-10-15','A','Review',options['token'],'manual')
    view=service.overview('2026-10-15')
    assert view['plan']['items'][0]['topic_id']=='Review'
    assert view['plan']['distribution']['planned_reviews']==20
    assert view['plan']['distribution']['planned_new']==0
    service.undo_swap('2026-10-15',slot,service.agenda.token())
    assert service.overview('2026-10-15')['plan']['items'][0]['topic_id']=='A'
    assert not service.store.active('2026-10-15')
    assert sum(r.get('kind','').startswith('day.swap') for r in service.agenda.records())==2


def test_stale_swap_and_invalid_target_cannot_mutate_schedule(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    options=service.swap_options('2026-10-15','A')
    service.configure_day('2026-10-15',30,'normal',0)
    with pytest.raises(ValueError): service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    fresh=service.swap_options('2026-10-15','A')
    with pytest.raises(ValueError): service.swap_topic('2026-10-15','A','missing',fresh['token'],'manual')
    assert not any(r.get('kind')=='day.swap' for r in service.agenda.records())


def test_calendar_uses_swap_only_on_its_day_and_keeps_removed_topic_eligible(tmp_path,monkeypatch):
    from osler.study_calendar import forecast_calendar
    service,_=service_fixture(tmp_path,monkeypatch)
    options=service.swap_options('2026-10-15','A')
    service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    view=service.overview('2026-10-15')
    plans=forecast_calendar(view['planning_states'],AdaptiveProfile(**view['profile']),'2026-10-15',3,
                            view['sessions'],service.store.days(),agenda=view['agenda'])
    assert plans[0]['items'][0]['topic_id']=='B'
    assert any(i['topic_id']=='A' for day in plans[1:] for i in day['items'])


def test_removed_topic_gets_reserved_date_that_skips_rest_and_undo_removes_it(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    service.configure_day('2026-10-16',20,'descanso',0)
    options=service.swap_options('2026-10-15','A')
    assert options['return_plan']['date']=='2026-10-17'
    slot=service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    view=service.overview('2026-10-15')
    row=next(r for r in view['agenda']['rows'] if r['topic_id']=='A')
    assert row['date']=='2026-10-17' and row['remaining']==20
    assert next(t for t in view['states'] if t['topic_id']=='A')['last_contact'] is None
    service.undo_swap('2026-10-15',slot,service.agenda.token())
    assert not service.overview('2026-10-15')['agenda']['rows']


def test_chain_preserves_return_reservations_for_both_removed_topics(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    options=service.swap_options('2026-10-15','A')
    slot=service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    options=service.swap_options('2026-10-15','B')
    assert service.swap_topic('2026-10-15','B','C',options['token'],'manual')==slot
    view=service.overview('2026-10-15')
    assert {r['topic_id'] for r in view['agenda']['rows']}=={'A','B'}
    assert view['plan']['items'][0]['topic_id']=='C'
    assert len({r['date'] for r in view['agenda']['rows']})==2
    service.undo_swap('2026-10-15',slot,service.agenda.token())
    view=service.overview('2026-10-15')
    assert view['plan']['items'][0]['topic_id']=='B'
    assert {r['topic_id'] for r in view['agenda']['rows']}=={'A'}


def test_chain_keeps_credit_for_removed_topic_studied_between_swaps(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    options=service.swap_options('2026-10-15','A')
    service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    service.save_entry(StudyEntry(topics[0]['path'],'2026-10-15',10,9),'advance-original')
    options=service.swap_options('2026-10-15','B')
    service.swap_topic('2026-10-15','B','C',options['token'],'manual')
    row=next(r for r in service.overview('2026-10-15')['agenda']['rows'] if r['topic_id']=='A')
    assert row['remaining']==10


def test_newer_rescheduling_is_not_overwritten_by_existing_swap_or_chain(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    options=service.swap_options('2026-10-15','A')
    service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    service.agenda.append({'kind':'reschedule.apply','selected':['A'],'created_day':'2026-10-15','cutoff':0,
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':'2026-10-20','original_due':'2026-10-15',
                 'questions':20,'new_topic':True}],'overrides':{}},service.agenda.token())
    view=service.overview('2026-10-15')
    assert next(r for r in view['agenda']['rows'] if r['topic_id']=='A')['date']=='2026-10-20'
    options=service.swap_options('2026-10-15','B')
    service.swap_topic('2026-10-15','B','C',options['token'],'manual')
    view=service.overview('2026-10-15')
    assert next(r for r in view['agenda']['rows'] if r['topic_id']=='A')['date']=='2026-10-20'


def test_swapping_extra_block_keeps_normal_block_and_daily_goal(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    service.add_topic('2026-10-15','D',10,0)
    options=service.swap_options('2026-10-15','D')
    service.swap_topic('2026-10-15','D','B',options['token'],'manual')
    plan=service.overview('2026-10-15')['plan']
    assert {(i['topic_id'],i['questions']) for i in plan['items']}=={('A',20),('B',10)}
    assert plan['target_questions']==30
    target=next(t for t in service.catalog('2026-10-15')[0] if t['topic_id']=='B')
    original=next(t for t in service.catalog('2026-10-15')[0] if t['topic_id']=='A')
    service.save_entry(StudyEntry(target['path'],'2026-10-15',10,9),'done-extra')
    service.save_entry(StudyEntry(original['path'],'2026-10-15',20,18),'done-base')
    plan=service.overview('2026-10-15')['plan']
    assert plan['target_questions']==30 and plan['done_questions']==30 and not plan['items']


def test_swap_preserves_recovery_balance_larger_than_todays_block(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    service.agenda.append({'kind':'reschedule.apply','selected':['A'],'created_day':'2026-10-15','cutoff':0,
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':'2026-10-15','original_due':'2026-10-15',
                 'questions':40,'new_topic':True}],'overrides':{}},service.agenda.token())
    options=service.swap_options('2026-10-15','A')
    service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    row=next(r for r in service.overview('2026-10-15')['agenda']['rows'] if r['topic_id']=='A')
    assert row['remaining']==40


def test_manual_change_of_type_keeps_the_other_planned_block(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    topics.append({**topic('Review2',answered=40),'is_leaf':True})
    service.store.save_profile(AdaptiveProfile(max_questions=40,max_topics=2,new_share=.5),1)
    before=service.overview('2026-10-15')['plan']
    assert {i['topic_id'] for i in before['items']}=={'A','Review'}
    options=service.swap_options('2026-10-15','A')
    service.swap_topic('2026-10-15','A','Review2',options['token'],'manual')
    plan=service.overview('2026-10-15')['plan']
    assert {i['topic_id'] for i in plan['items']}=={'Review','Review2'}
    assert plan['distribution']['planned_reviews']==40 and plan['distribution']['planned_new']==0
    chosen=next(t for t in topics if t['topic_id']=='Review2')
    service.save_entry(StudyEntry(chosen['path'],'2026-10-15',20,18),'completed-swap')
    plan=service.overview('2026-10-15')['plan']
    assert [(i['topic_id'],i['questions']) for i in plan['items']]==[('Review',20)]
    assert plan['distribution']['done_reviews']==20 and plan['distribution']['done_new']==0


def test_no_date_before_exam_blocks_swap_without_mutating_history(tmp_path,monkeypatch):
    service,_=service_fixture(tmp_path,monkeypatch)
    service.store.save_profile(AdaptiveProfile(max_questions=20,max_topics=1,new_share=1,exam_date='2026-10-15'),1)
    options=service.swap_options('2026-10-15','A')
    assert options['return_plan'] is None
    with pytest.raises(ValueError): service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    assert not any(r.get('kind')=='day.swap' for r in service.agenda.records())


def test_swapping_review_keeps_original_error_lot_and_conviction(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    topics.append({**topic('Review2',answered=40),'is_leaf':True})
    service.store.save_profile(AdaptiveProfile(max_questions=20,max_topics=1,new_share=0),1)
    original=next(t for t in topics if t['topic_id']=='Review')
    service.save_entry(StudyEntry(original['path'],'2026-10-08',20,10,confident_correct=5),'weak')
    before=service.overview('2026-10-15')
    options=service.swap_options('2026-10-15','Review')
    service.swap_topic('2026-10-15','Review','Review2',options['token'],'manual')
    after=service.overview('2026-10-15')
    assert after['review_queue']==before['review_queue']
    assert next(t for t in after['states'] if t['topic_id']=='Review')['confidence']==next(t for t in before['states'] if t['topic_id']=='Review')['confidence']


def test_combined_extra_can_be_moved_in_smaller_future_blocks_without_growing_goal(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    service.add_topic('2026-10-15','A',10,0)
    options=service.swap_options('2026-10-15','A')
    assert options['return_plan']['questions']==30
    assert options['return_plan']['first_block_questions']==20
    service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    service.save_entry(StudyEntry(topics[1]['path'],'2026-10-15',30,27),'done-combined')
    plan=service.overview('2026-10-15')['plan']
    assert plan['target_questions']==30 and not plan['items']


def test_swapping_overdue_recovery_preserves_original_due_date(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    service.agenda.append({'kind':'reschedule.apply','selected':['A'],'created_day':'2026-10-15','cutoff':0,
        'rows':[{'topic_id':'A','path':topics[0]['path'],'date':'2026-10-15','original_due':'2026-10-10',
                 'questions':20,'new_topic':True}],'overrides':{}},service.agenda.token())
    options=service.swap_options('2026-10-15','A')
    assert options['return_plan']['original_due']=='2026-10-10'


def test_undo_one_of_two_independent_swaps_restores_only_its_original(tmp_path,monkeypatch):
    service,topics=service_fixture(tmp_path,monkeypatch)
    topics.append({**topic('Review2',answered=40),'is_leaf':True})
    service.store.save_profile(AdaptiveProfile(max_questions=40,max_topics=2,new_share=.5),1)
    options=service.swap_options('2026-10-15','A')
    first=service.swap_topic('2026-10-15','A','B',options['token'],'manual')
    options=service.swap_options('2026-10-15','Review')
    service.swap_topic('2026-10-15','Review','Review2',options['token'],'manual')
    service.undo_swap('2026-10-15',first,service.agenda.token())
    plan=service.overview('2026-10-15')['plan']
    assert {i['topic_id'] for i in plan['items']}=={'A','Review2'}
