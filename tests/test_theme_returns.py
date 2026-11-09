from dataclasses import replace
from copy import deepcopy
import pytest
from test_return_deferral import configured,DAY
from osler.study_models import AdaptiveProfile
from osler.review_queue import review_queue


def test_theme_mode_preserves_queue_and_results_without_scheduling_lots(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch)
    before=s.overview(DAY);events=deepcopy(s.store.events())
    p=s.store.profile()
    s.store.save_profile(replace(AdaptiveProfile(**p['configured_profile']),return_mode='theme'),p['id'])
    after=s.overview(DAY)
    assert after['review_queue']==[]
    assert after['reference_review_queue']==before['review_queue']
    assert all(not t['pending_reviews'] and t['review_kind']=='theme' for t in after['planning_states'])
    assert s.store.events()==events
    assert review_queue(after['sessions'])==review_queue(before['sessions'])
    from osler.study_calendar import forecast_calendar
    plans=forecast_calendar(after['planning_states'],AdaptiveProfile(**after['profile']),DAY,14,after['sessions'],s.store.days(),agenda=after['agenda'])
    assert all(not t.get('pending_reviews') and t.get('review_kind')=='theme' for day in plans for t in day['items'])
    for t in after['states']:
        old=next(o for o in before['states'] if o['topic_id']==t['topic_id'])
        assert t['performance']==old['performance'] and t['confidence']==old['confidence']
    s.store.save_profile(AdaptiveProfile(**p['configured_profile']),s.store.profile()['id'])
    assert s.overview(DAY)['review_queue']==before['review_queue']


def test_return_mode_change_uses_existing_read_only_preview_and_audited_apply(tmp_path,monkeypatch):
    s=configured(tmp_path,monkeypatch);token=s.agenda.token()
    preview=s.preview_review_strategy('balanced_v2',return_mode='theme')
    assert s.agenda.token()==token
    s.apply_review_strategy(preview)
    assert s.store.profile()['profile']['return_mode']=='theme'
    assert s.review_strategy_history()[-1]['preview']==preview


def test_invalid_return_mode_is_rejected():
    with pytest.raises(ValueError):replace(AdaptiveProfile(),return_mode='unknown').validate()


def test_theme_mode_keeps_objective_linked_failures_as_evidence():
    from test_balanced_reviews import block,state,profile
    a=block('2026-10-01',n=40,correct=40,confident=30)
    b=block('2026-10-08',n=40,correct=40,confident=40)
    failed=block('2026-10-09',n=10,correct=0,confident=0,mode='repetidas',review_of=a['session_id'])
    t=state([a,b,failed],'2026-10-09',replace(profile(),return_mode='theme'))
    assert t['linked_adverse'] and t['learning_state']!='dominado'
    assert t['dose_kind']=='reinforcement' and not t['pending_reviews']
    assert t['performance']['exact_n']==80 and t['performance']['exact_correct']==80


def test_special_card_days_keep_decks_whole_and_honor_explicit_ceiling():
    from osler.error_cards import plan_error_cards
    topics=[{'topic_id':'large','path':['Área','Grande'],'count':153},
            {'topic_id':'small','path':['Área','Pequeno'],'count':10}]
    normal=plan_error_cards(topics,{},[],DAY,100)
    assert next(t for t in normal if t['topic_id']=='large')['planned']==0
    special=plan_error_cards(topics,{},[],DAY,153,max_total=153)
    assert sum(t['planned'] for t in special)<=153
    assert all(t['planned'] in {0,t['remaining']} for t in special)
    assert next(t for t in special if t['topic_id']=='large')['planned']==153


def test_later_representative_success_can_resolve_theme_alert_without_closing_old_lot():
    from test_balanced_reviews import block,state,profile
    a=block('2026-10-01',n=40,correct=40,confident=30)
    failed=block('2026-10-08',n=10,correct=0,confident=0,mode='repetidas',review_of=a['session_id'])
    good=block('2026-10-15',n=40,correct=38,confident=25,mode='mistas')
    entries=[a,failed,good];raw=deepcopy(review_queue(entries))
    t=state(entries,'2026-10-15',replace(profile(),return_mode='theme'))
    assert not t['linked_adverse']
    assert review_queue(entries)==raw
