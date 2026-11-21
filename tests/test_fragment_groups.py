import pytest

from osler.adaptive_service import AdaptiveService
from osler.models import normalize_path, stable_topic_id
from osler.study_models import AdaptiveProfile, StudyEntry
from osler.topic_catalog import planning_frontier


DAY = '2026-10-30'
THEME = ['Clínica Cirúrgica', 'Princípios de Cirurgia', 'Nutrição Perioperatória']
OTHER_THEME = ['Clínica Cirúrgica', 'Princípios de Cirurgia', 'Outro tema']


def leaf(path, total, **rest):
    return {'path': path, 'topic_id': stable_topic_id(path), 'total': total,
            'is_leaf': True, 'answered_pdf': 0, 'studied_cards': 0, **rest}


def test_parent_documented_exposure_and_future_activity_do_not_leak_to_the_leaf():
    from osler.topic_catalog import classify_theme_context

    child = leaf(THEME+['Terapia Nutricional'], 1)
    sibling = leaf(OTHER_THEME+['Subtema'], 40)
    parent = {**leaf(THEME, 100), 'is_leaf': False, 'answered_pdf': 39}
    index = {tuple(normalize_path(THEME)): {'path': THEME}}
    topics = classify_theme_context([child, sibling, parent], [index], DAY,
        sessions=[{'entry': StudyEntry(sibling['path'], '2026-10-31', 10, correct=8).to_dict()}])
    first, second, _ = topics
    assert first['theme_path']==THEME and first['theme_started']
    assert not first['leaf_started'] and first['answered_pdf']==0
    assert second['theme_path']==OTHER_THEME and not second['theme_started']


def test_a_leafs_own_first_entry_does_not_make_it_a_continuation():
    from osler.topic_catalog import classify_theme_context

    first=leaf(THEME+['Primeiro'],20)
    second=leaf(THEME+['Segundo'],20)
    entry=StudyEntry(first['path'],DAY,10,correct=6).to_dict()
    topics=classify_theme_context([first,second],[],DAY,sessions=[{'entry':entry}])
    assert topics[0]['leaf_started'] and not topics[0]['theme_started']
    assert not topics[1]['leaf_started'] and topics[1]['theme_started']


def test_fragment_groups_are_disjoint_and_require_a_full_minimum():
    tiny = [leaf(THEME+[f'Tema {i}'], 2, theme_path=THEME) for i in range(5)]
    elsewhere = [leaf(OTHER_THEME+[f'Tema {i}'], 2, theme_path=OTHER_THEME) for i in range(4)]
    groups = planning_frontier(tiny+elsewhere, 10)
    virtual = [t for t in groups if t.get('fragment_group')]
    assert len(virtual)==1
    group = virtual[0]
    assert group['total']==10 and group['path']==THEME+['Subtemas menores']
    assert group['group_members']==[t['topic_id'] for t in tiny]
    assert {t['topic_id'] for t in groups if not t.get('fragment_group')}=={t['topic_id'] for t in elsewhere}
    assert group['group_member_paths']==[t['path'] for t in tiny]
    assert not any(t.get('fragment_group') for t in planning_frontier(tiny,10,blocked=[tiny[0]['topic_id']]))


def test_virtual_path_respects_a_physical_catalog_parent_outside_the_frontier():
    tiny=[leaf(THEME+[f'Tema {i}'],2,theme_path=THEME) for i in range(5)]
    existing=THEME+['Subtemas menores']
    frontier=planning_frontier(tiny,10,reserved_paths=[existing])
    assert {t['topic_id'] for t in frontier}=={t['topic_id'] for t in tiny}


def test_fragment_group_is_registrable_and_history_survives_membership_change(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from osler.planner_service import today_local

    repo,*_=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    actual_day=today_local().isoformat()
    report_topics=[{**leaf(THEME+[f'Tema {i}'],2),
                    'pdf_accuracy':{'value':None,'operator':'=','raw':'-'},
                    'report_date':actual_day}
                   for i in range(6)]
    catalog=report_topics[:]
    monkeypatch.setattr(service,'catalog',lambda _day,include_parents=False:(catalog,{}))
    monkeypatch.setattr(service.guide,'datasets',lambda:[])
    service.store.save_profile(AdaptiveProfile(exam_date='2027-12-31',return_mode='theme'),0)
    before=next(t for t in service.overview(actual_day)['planning_states'] if t.get('fragment_group'))
    catalog.pop()
    with pytest.raises(ValueError,match='composição'):
        service.save_entry(StudyEntry(before['path'],actual_day,10,correct=8,
                                     fragment_members=before['group_member_paths']),'stale')
    assert not service.store.events()
    group=next(t for t in service.overview(actual_day)['planning_states'] if t.get('fragment_group'))
    validate=service._validate_entry
    def validate_after_an_agenda_change(entry,**options):
        from osler.study_models import StudyDay
        checked=validate(entry,**options)
        service.store.save_day(actual_day,StudyDay(questions=60),0)
        return checked
    with monkeypatch.context() as race:
        race.setattr(service,'_validate_entry',validate_after_an_agenda_change)
        with pytest.raises(ValueError,match='plano mudou'):
            service.save_entry(StudyEntry(group['path'],actual_day,10,correct=8,
                                         fragment_members=group['group_member_paths']),'race')
    assert not service.store.events()
    saved=service.save_entry(StudyEntry(group['path'],actual_day,10,correct=8),'virtual')
    event=service.store.active(actual_day)[0]
    assert event['entry']['fragment_members']==group['group_member_paths']
    assert saved>0
    active=service.overview(actual_day)
    assert any(t['topic_id']==group['topic_id'] for t in active['planning_states'])
    from osler.study_evolution import evolution_snapshot
    coverage=evolution_snapshot(active['states'],active['sessions'],[],actual_day,planning_states=active['planning_states'])
    assert coverage['total_topics']==5 and coverage['covered_now']==0
    assert set(coverage['joint_member_ids_now'])==set(group['group_members'])
    catalog[0]=report_topics[5]
    view=service.overview(actual_day)
    assert all(t['topic_id']!=group['topic_id'] for t in view['planning_states'])
    historic=next(t for t in view['states'] if t['topic_id']==group['topic_id'])
    assert historic['historical_aggregate'] and historic['group_member_paths']==group['group_member_paths']
    with pytest.raises(ValueError,match='composição'):
        service.save_entry(StudyEntry(group['path'],actual_day,10,correct=9),'new')
    service.save_entry(StudyEntry(group['path'],actual_day,10,correct=9),'virtual',expected_version=1)
    assert service.store.active(actual_day)[0]['entry']['fragment_members']==group['group_member_paths']
