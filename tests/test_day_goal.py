from copy import deepcopy
from dataclasses import replace
import pytest

from osler.adaptive_service import AdaptiveService
from osler.storage import Repository
from osler.study_models import AdaptiveProfile, StudyDay, StudyEntry
from osler.study_replanning import effective_routine
from osler.recovery import RecoveryService
from test_adaptive_planning import topic

DAY='2026-10-15'


def configured(tmp_path,monkeypatch,area=0):
    s=AdaptiveService(Repository(tmp_path))
    topics=[{**topic(name),'is_leaf':True} for name in ['A','B','C','D','E','F']]
    monkeypatch.setattr(s,'catalog',lambda *args,**kwargs:(deepcopy(topics),{'qbank':None,'flashcards':None}))
    s.store.save_profile(AdaptiveProfile(max_questions=120,max_topics=6,workload_mode='adaptive',review_strategy='balanced_v2'),0)
    if area:
        s.agenda.append({'kind':'reschedule.apply','scope':'area_practice','created_day':DAY,
            'cutoff':0,'selected':[],'rows':[],'request':{'end':'2026-11-30'},
            'occurrences':[{'id':'area-one','date':DAY,'original_date':DAY,'questions':area,
                            'institution':'UNESP','area':'Clínica Médica'}]},s.agenda.token())
    RecoveryService(s.repository).save(200,30,80,50,70,DAY,s.agenda.token())
    return s


def test_explicit_total_changes_effective_budget_without_changing_legacy_defaults():
    p=AdaptiveProfile()
    over={'recovery_limit':80,'recovery_reserved':30,'area_reserved':20}
    assert effective_routine(p,StudyDay(questions=100).to_dict(),over)[1]==30
    config=StudyDay(questions=100,effective_goal=True).to_dict()
    assert effective_routine(p,config,over)[1]==50
    with pytest.raises(ValueError):replace(StudyDay(),effective_goal=1).validate()


def test_preview_is_read_only_and_applied_goal_changes_only_one_date(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch,area=20)
    before=(s.agenda.token(),s.store.days(),s.store.profile(),s.store.events())
    preview=s.preview_day_goal(DAY,100)
    assert preview['before']['total']==80
    assert preview['after']['total']==100
    assert preview['after']['themes']==50
    assert preview['after']['area']==20 and preview['after']['external']==30
    assert (s.agenda.token(),s.store.days(),s.store.profile(),s.store.events())==before
    s.apply_day_goal(preview)
    v=s.overview(DAY)
    assert v['plan']['base_questions']==50
    assert v['plan']['routine_override']['recovery_limit']==100
    assert v['plan']['routine_override']['area_reserved']==20
    assert s.overview('2026-10-16')['plan']['routine_override']['recovery_limit']==80
    assert s.store.profile()==before[2] and s.store.events()==before[3]
    assert any(r.get('kind')=='day_goal.change' for r in s.agenda.records())
    with pytest.raises(ValueError,match='mud|prévia'):s.apply_day_goal(preview)


def test_preview_cannot_be_applied_after_another_setting_or_payload_changes(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch)
    preview=s.preview_day_goal(DAY,100)
    damaged=deepcopy(preview);damaged['after']['total']=120
    with pytest.raises(ValueError,match='prévia'):s.apply_day_goal(damaged)
    s.configure_day(DAY,110,'normal',0)
    with pytest.raises(ValueError,match='mud|prévia'):s.apply_day_goal(preview)


def test_goal_cannot_hide_reserved_training_or_recorded_external_work(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch,area=20)
    r=RecoveryService(s.repository);r.record(DAY,30,s.agenda.token())
    with pytest.raises(ValueError,match='50'):s.preview_day_goal(DAY,40)
    with pytest.raises(ValueError,match='treino'):s.preview_day_goal(DAY,80,kind='descanso')


def test_exclusive_day_explains_the_owner_of_the_schedule(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch)
    s.agenda.append({'kind':'reschedule.apply','scope':'mock_day','created_day':DAY,'cutoff':0,
        'rows':[],'selected':[],'overrides':{DAY:{'mode':'mock_reserved','questions':0}}},s.agenda.token())
    with pytest.raises(ValueError,match='Simulados'):s.preview_day_goal(DAY,100)


def test_effective_total_includes_existing_extras_and_new_extras_still_add_capacity(tmp_path,monkeypatch):
    s=AdaptiveService(Repository(tmp_path))
    topics=[{**topic(n),'is_leaf':True} for n in ['A','B','C']]
    monkeypatch.setattr(s,'catalog',lambda *a,**kw:(deepcopy(topics),{'qbank':None,'flashcards':None}))
    s.add_topic(DAY,'A',10,0)
    p=s.preview_day_goal(DAY,50)
    assert p['after']['total']==50 and p['after']['themes']==50
    s.apply_day_goal(p)
    assert s.overview(DAY)['plan']['target_questions']==50
    s.add_topic(DAY,'B',5,2)
    assert s.overview(DAY)['plan']['target_questions']==55
    s.remove_added_topic(DAY,'B',3)
    assert s.overview(DAY)['plan']['target_questions']==50


def test_explicit_goal_replaces_temporary_extra_mode_instead_of_adding_it_twice(tmp_path,monkeypatch):
    s=AdaptiveService(Repository(tmp_path))
    s.agenda.append({'kind':'reschedule.apply','created_day':DAY,'cutoff':0,'rows':[],'selected':[],
        'overrides':{DAY:{'mode':'extra','extra_questions':20}}},s.agenda.token())
    assert s.preview_day_goal(DAY,100)['after']['total']==100


def test_explicit_extras_keep_their_place_inside_recovery_and_the_total(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch)
    s.add_topic(DAY,'F',50,0)
    with pytest.raises(ValueError,match='50'):s.preview_day_goal(DAY,10)
    p=s.preview_day_goal(DAY,50)
    assert p['after']['total']==50 and p['after']['external']==0
    assert p['after']['items']==[{'topic_id':'F','path':['Área','F'],'questions':50}]
    s.apply_day_goal(p)
    assert s.overview(DAY)['plan']['target_questions']==50


def test_recovery_loads_previously_saved_extra_in_today_and_calendar(tmp_path,monkeypatch):
    from osler.study_calendar import forecast_calendar

    s=configured(tmp_path,monkeypatch,area=20)
    # Reproduz o registro escrito pela versão que ocultava extras na retomada.
    s.store.save_day(DAY,StudyDay(questions=120,extra_topics=[
        {'extra_id':'saved','topic_id':'F','questions':50,'after_event_id':0}]),0)
    view=s.overview(DAY)
    for plan in [view['plan'],forecast_calendar(view['planning_states'],AdaptiveProfile(**view['profile']),DAY,1,
                                              view['sessions'],s.store.days(),agenda=view['agenda'])[0]]:
        assert next(i['extra_pending'] for i in plan['items'] if i['topic_id']=='F')==50
        assert plan['base_questions']+plan['extra_questions']+20+plan['routine_override']['recovery_reserved']==80


def test_recovery_refuses_extra_that_would_exceed_room_after_recorded_work(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch,area=20)
    RecoveryService(s.repository).record(DAY,30,s.agenda.token())
    s.save_entry(StudyEntry(['Área','A'],DAY,25,20),'already-done')
    with pytest.raises(ValueError,match='Cabem 5 questões extras'):
        s.add_topic(DAY,'F',6,0)
    assert s.store.days()=={}
    s.add_topic(DAY,'F',5,0)
    plan=s.overview(DAY)['plan']
    assert next(i['extra_pending'] for i in plan['items'] if i['topic_id']=='F')==5
    assert plan['target_questions']+plan['routine_override']['recovery_reserved']==80


def test_free_extra_preserves_recovery_capacity_and_automatic_blocks(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch,area=20)
    before=s.overview(DAY)['plan']
    before_items={i['topic_id']:i['questions'] for i in before['items']}
    s.add_topic(DAY,'F',150,0,over_limit=True)
    added=s.overview(DAY)['plan']
    after_items={i['topic_id']:i['questions'] for i in added['items']}
    assert after_items=={**before_items,'F':before_items.get('F',0)+150}
    assert added['target_questions']==before['target_questions']+150
    assert added['routine_override']==before['routine_override']
    assert added['area_tasks']==before['area_tasks']
    assert added['manual_extra_questions']==150
    assert s.store.events()==[]
    assert s.preview_day_goal(DAY,230)['after']['total']==230

    s.save_entry(StudyEntry(['Área','F'],DAY,145,110,mode='mistas'),'extra-real')
    plan=s.overview(DAY)['plan']
    assert plan['manual_extra_done']==145 and plan['done_questions']==145
    assert next(i['manual_pending'] for i in plan['items'] if i['topic_id']=='F')==5
    assert plan['routine_override']['recovery_reserved']==30
    assert plan['base_questions']==before['base_questions']
    s.remove_added_topic(DAY,'F',1)
    assert s.store.active(DAY)[0]['entry']['questions']==145
    plan=s.overview(DAY)['plan']
    assert plan['manual_extra_done']==145 and plan['manual_extra_questions']==145
    assert plan['routine_override']['recovery_reserved']==30


def test_rest_preview_has_zero_capacity_in_every_category(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch)
    after=s.preview_day_goal(DAY,80,kind='descanso')['after']
    assert [after[k] for k in ['total','themes','area','external']]==[0,0,0,0]


def test_area_result_is_not_completion_of_a_separately_reserved_extra(tmp_path,monkeypatch):
    from osler.mock_exams import MockExams,MockExam,convert_to_entries
    s=configured(tmp_path,monkeypatch,area=20)
    s.add_topic(DAY,'A',50,0)
    result=MockExams(s.repository).save(MockExam(DAY,20,10,institution='UNESP',practice_id='area-one',
        areas=[{'area':'Clínica Médica','questions':20,'correct':10}],
        topics=[{'path':['Área','A'],'questions':20,'correct':10}],unseen_questions=True))
    convert_to_entries(s,result['exam_key'],1)
    with pytest.raises(ValueError,match='70'):s.preview_day_goal(DAY,50)
    p=s.preview_day_goal(DAY,100)
    assert p['after']['total']==100 and p['after']['external']==30
    assert next(i['questions'] for i in p['after']['items'] if i['topic_id']=='A')==50
