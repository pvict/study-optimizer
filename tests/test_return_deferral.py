from copy import deepcopy

import pytest

from osler.adaptive_service import AdaptiveService
from osler.review_queue import review_queue
from osler.storage import Repository
from osler.study_calendar import forecast_calendar
from osler.study_models import AdaptiveProfile, StudyEntry
from test_adaptive_planning import topic


DAY='2026-10-15'
TOMORROW='2026-10-16'


def configured(tmp_path,monkeypatch,strategy='balanced_v2',workload_mode='fixed'):
    service=AdaptiveService(Repository(tmp_path))
    topics=[{**topic(name,answered=40),'is_leaf':True} for name in ['A','B','C']]
    monkeypatch.setattr(service,'catalog',lambda *args,**kwargs:(topics,{'qbank':None,'flashcards':None}))
    service.store.save_profile(AdaptiveProfile(max_questions=20,max_topics=1,new_share=0,min_block=5,review_strategy=strategy,workload_mode=workload_mode),0)
    service.save_entry(StudyEntry(topics[0]['path'],'2026-10-08',20,12,confident_correct=10),'source')
    assert service.overview(DAY)['plan']['items'][0]['topic_id']=='A'
    return service


@pytest.mark.parametrize('strategy',['balanced_v2','legacy_v1'])
@pytest.mark.parametrize('workload_mode',['fixed','adaptive'])
def test_deferral_replaces_topic_preserves_results_and_can_be_undone(tmp_path,monkeypatch,strategy,workload_mode):
    service=configured(tmp_path,monkeypatch,strategy,workload_mode)
    if strategy=='legacy_v1' and workload_mode=='adaptive':
        # Outra revisão já devida cabe hoje; não exige admitir estudo novo em
        # uma agenda cujo cenário legado prevê repetições a cada três dias.
        service.save_entry(StudyEntry(['Área','B'],'2026-10-08',20,12,confident_correct=10),'pending-B')
    before=service.overview(DAY)
    service.remember_day(before)
    events=deepcopy(service.store.events())
    preview=service.preview_return_deferral(DAY,'A')
    assert preview['available_from']==TOMORROW
    assert preview['replacements'] and all(i['topic_id']!='A' for i in preview['replacements'])
    assert service.store.events()==events
    assert not service.agenda.active(before['sessions'],DAY)['rows']
    applied=service.defer_return(DAY,'A',preview['token'])
    changed=service.overview(DAY)
    assert 'A' not in {i['topic_id'] for i in changed['plan']['items']}
    assert changed['plan']['items']==preview['plan']['items']
    assert changed['plan']['questions']<=changed['plan']['target_questions']==20
    deferred=next(q for q in changed['review_queue'] if q['session_id']=='source')
    assert deferred['due_date']==TOMORROW
    assert deferred['original_due_date']==DAY
    assert review_queue(changed['sessions'])==review_queue(before['sessions'])
    for name in ['performance','confidence','spacing','last_contact','recorded_attempts']:
        assert next(t for t in before['states'] if t['topic_id']=='A')[name]==next(t for t in changed['states'] if t['topic_id']=='A')[name]
    assert service.store.events()==events
    assert all(i['topic_id']!='A' for r in service.agenda.daily_plans() for i in r['plan']['items'])
    assert any(i['topic_id']=='A' for r in service.agenda.records() if r.get('kind')=='daily_schedule' for i in r['plan']['items'])
    calendar=forecast_calendar(changed['planning_states'],AdaptiveProfile(**changed['profile']),DAY,3,changed['sessions'],service.store.days(),agenda=changed['agenda'])
    assert 'A' not in {i['topic_id'] for i in calendar[0]['items']}
    assert 'A' in {i['topic_id'] for i in calendar[1]['items']}
    service.undo_return_deferral(DAY,applied,service.agenda.token())
    restored=service.overview(DAY)
    assert restored['plan']['items'][0]['topic_id']=='A'
    assert restored['review_queue']==before['review_queue']
    assert service.store.events()==events


def test_unavailable_day_is_never_counted_as_missed_work(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    service.remember_day(service.overview(DAY))
    service.defer_return(DAY,'A',service.agenda.token())
    assert not any(r['topic_id']=='A' for r in service.replanning(TOMORROW)['backlog'])
    row=next(r for r in service.replanning('2026-10-17')['backlog'] if r['topic_id']=='A')
    assert row['original_due']==TOMORROW and row['days_late']==1


def test_stale_deferral_and_non_return_are_rejected(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    preview=service.preview_return_deferral(DAY,'A')
    service.configure_day(DAY,30,'normal',0)
    with pytest.raises(ValueError,match='mudou'):
        service.defer_return(DAY,'A',preview['token'])
    with pytest.raises(ValueError):service.preview_return_deferral(DAY,'B')
    with pytest.raises(ValueError):service.preview_return_deferral(TOMORROW,'A')
    assert not service.overview(DAY)['agenda']['rows']


def test_tomorrow_rest_is_protected_and_reservation_carries_forward(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    service.configure_day(TOMORROW,20,'descanso',0)
    preview=service.preview_return_deferral(DAY,'A')
    service.defer_return(DAY,'A',preview['token'])
    view=service.overview(DAY)
    calendar=forecast_calendar(view['planning_states'],AdaptiveProfile(**view['profile']),DAY,3,view['sessions'],service.store.days(),agenda=view['agenda'])
    assert not calendar[1]['items']
    assert 'A' in {i['topic_id'] for i in calendar[2]['items']}


def test_extra_cannot_reinsert_unavailable_topic_or_inflate_target(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    service.add_topic(DAY,'A',5,0)
    preview=service.preview_return_deferral(DAY,'A')
    service.defer_return(DAY,'A',preview['token'])
    changed=service.overview(DAY)
    assert 'A' not in {i['topic_id'] for i in changed['plan']['items']}
    assert changed['plan']['target_questions']==20
    assert changed['plan']['extra_questions']==0


def test_manually_swapped_return_is_replaced_even_when_peer_list_was_empty(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    service.save_entry(StudyEntry(['Área','B'],'2026-10-08',20,12,confident_correct=10),'second-source')
    source=service.overview(DAY)['plan']['items'][0]['topic_id']
    target='B' if source=='A' else 'A'
    options=service.swap_options(DAY,source)
    service.swap_topic(DAY,source,target,options['token'])
    assert service.overview(DAY)['plan']['items'][0]['topic_id']==target
    preview=service.preview_return_deferral(DAY,target)
    assert [i['topic_id'] for i in preview['plan']['items']]==['C']
    applied=service.defer_return(DAY,target,preview['token'])
    view=service.overview(DAY)
    assert [i['topic_id'] for i in view['plan']['items']]==['C']
    assert len(view['agenda']['swaps'])==1
    service.undo_return_deferral(DAY,applied,service.agenda.token())
    assert service.overview(DAY)['plan']['items'][0]['topic_id']==target


def test_deferral_does_not_erase_existing_larger_reservation(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    service.agenda.append({'kind':'reschedule.apply','created_day':DAY,'selected':['A'],'cutoff':0,
        'rows':[{'topic_id':'A','path':['Área','A'],'date':DAY,'original_due':'2026-10-14','questions':45}],
        'overrides':{}},service.agenda.token())
    before=next(r for r in service.overview(DAY)['agenda']['rows'] if r['topic_id']=='A')['remaining']
    preview=service.preview_return_deferral(DAY,'A')
    service.defer_return(DAY,'A',preview['token'])
    row=next(r for r in service.overview(DAY)['agenda']['rows'] if r['topic_id']=='A')
    assert row['remaining']==before and row['date']==TOMORROW


def test_future_lots_stay_on_original_dates_and_reread_is_persistent(tmp_path,monkeypatch):
    service=configured(tmp_path,monkeypatch)
    service.save_entry(StudyEntry(['Área','A'],'2026-10-12',10,8,confident_correct=7),'future-source')
    preview=service.preview_return_deferral(DAY,'A')
    service.defer_return(DAY,'A',preview['token'])
    reopened=AdaptiveService(Repository(tmp_path))
    monkeypatch.setattr(reopened,'catalog',service.catalog)
    queue={q['session_id']:q for q in reopened.overview(DAY)['review_queue']}
    assert queue['source']['due_date']==TOMORROW
    assert queue['future-source']['due_date']=='2026-10-19'
    assert 'original_due_date' not in queue['future-source']


def test_can_defer_again_tomorrow_without_losing_count_or_origin(tmp_path,monkeypatch):
    from datetime import date
    import osler.planner_service,osler.adaptive_service,osler.swap_service
    service=configured(tmp_path,monkeypatch)
    service.defer_return(DAY,'A',service.agenda.token())
    for mod in [osler.planner_service,osler.adaptive_service,osler.swap_service]:
        monkeypatch.setattr(mod,'today_local',lambda:date(2026,10,16))
    again=service.preview_return_deferral(TOMORROW,'A')
    assert again['available_from']=='2026-10-17'
    applied=service.defer_return(TOMORROW,'A',again['token'])
    view=service.overview(TOMORROW)
    assert not any(i['topic_id']=='A' for i in view['plan']['items'])
    assert view['review_queue'][0]['due_date']=='2026-10-17'
    assert view['review_queue'][0]['original_due_date']==DAY
    assert view['review_queue'][0]['questions']==10
    service.undo_return_deferral(TOMORROW,applied,service.agenda.token())
    assert service.overview(TOMORROW)['review_queue'][0]['due_date']==TOMORROW
