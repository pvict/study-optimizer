from dataclasses import replace
import json
import pytest
from osler.study_models import AdaptiveProfile
from osler.exam_goals import ExamGoals,ExamTarget
from osler.adaptive_service import AdaptiveService
from osler.guide import GuideSettings


def configured(tmp_path,sample_pdf,individual=False):
    from test_assessments import setup_assessment
    repo,*_,topic=setup_assessment(tmp_path,sample_pdf)
    service=AdaptiveService(repo)
    service.guide.store.save_settings(GuideSettings(institutions=['Banca A','Banca B']),0)
    target=ExamGoals(repo).save(ExamTarget('Banca A','2027-11-30',70,100,'Fonte'))
    base={'observed_date':'2026-10-15','unit':'questoes','rows':[{'path':topic.qbank.path,'value':100,'band':'alta'}]}
    service.guide.store.save_dataset({**base,'institutions':['Banca A','Banca B']})
    if individual:
        for institution in ['Banca A','Banca B']: service.guide.store.save_dataset({**base,'institutions':[institution]})
    return service,target,topic


def test_joint_table_cannot_enable_exam_weights_or_direct_profile_write(tmp_path,sample_pdf):
    service,target,_=configured(tmp_path,sample_pdf)
    record=service.store.profile(); p=AdaptiveProfile(**record['configured_profile'])
    with pytest.raises(ValueError,match='individual'):
        service.store.save_profile(replace(p,exam_weights={target['target_id']:1.5}),record['id'])
    assert service.store.profile()['id']==record['id']
    with pytest.raises(ValueError,match='individual'):
        service.store.save_profile(replace(p,institution_weights={'Banca A':1.5,'Banca B':1}),record['id'])


def test_individual_data_required_for_every_institution_and_names_are_retained(tmp_path,sample_pdf):
    service,target,topic=configured(tmp_path,sample_pdf)
    base={'observed_date':'2026-10-15','unit':'questoes','rows':[{'path':topic.qbank.path,'value':100,'band':'alta'}]}
    service.guide.store.save_dataset({**base,'institutions':['Banca A']})
    context=service.exam_weight_eligibility({target['target_id']:1.5})
    assert not context['allowed'] and context['missing']==['Banca B']
    service.guide.store.save_dataset({**base,'institutions':['Banca B']})
    context=service.exam_weight_eligibility({target['target_id']:1.5})
    assert context['allowed'] and context['effective_weights']=={'Banca A':1.5,'Banca B':1}


@pytest.mark.parametrize('day,value',[('2026-10-16',10),('2026-10-15',0)])
def test_future_or_zero_individual_tables_do_not_enable_weights(tmp_path,sample_pdf,day,value):
    service,target,topic=configured(tmp_path,sample_pdf)
    for institution in ['Banca A','Banca B']:
        service.guide.store.save_dataset({'observed_date':day,'unit':'questoes','institutions':[institution],
            'rows':[{'path':topic.qbank.path,'value':value,'band':'alta'}]})
    assert not service.exam_weight_eligibility({target['target_id']:1.5})['allowed']


def test_legacy_unsupported_weight_uses_original_group_with_visible_reason(tmp_path,sample_pdf):
    service,target,_=configured(tmp_path,sample_pdf)
    p=replace(AdaptiveProfile(),exam_weights={target['target_id']:1.5})
    with service.repository._connection() as db:
        db.execute('INSERT INTO study_profiles(payload,created_at) VALUES(?,?)',(json.dumps(p.to_dict()),'2026-10-15'))
    record=service.store.profile()
    assert not record['weight_policy']['allowed']
    view=service.overview('2026-10-15')
    assert view['profile']['institution_weights']=={'Banca A':1,'Banca B':1}
    assert view['incidence']['contexts'][0]['institutions']==['Banca A','Banca B']


def test_preview_has_no_writes_apply_checks_token_and_preserves_group_and_study(tmp_path,sample_pdf):
    service,target,_=configured(tmp_path,sample_pdf,True)
    before=service.store.profile(); events=service.store.events()
    preview=service.preview_exam_weights({target['target_id']:1.5},14)
    assert service.store.profile()['id']==before['id']
    assert preview['after']['weights']=={'Banca A':1.5,'Banca B':1}
    assert preview['before']['weights']=={'Banca A':1,'Banca B':1}
    assert preview['after']['max_questions']==preview['before']['max_questions']
    service.apply_exam_weights(preview)
    assert service.store.profile()['profile']['institution_weights']=={'Banca A':1.5,'Banca B':1}
    assert service.store.events()==events
    with pytest.raises(ValueError): service.apply_exam_weights(preview)


def test_preview_invalidates_when_new_incidence_changes_inputs(tmp_path,sample_pdf):
    service,target,topic=configured(tmp_path,sample_pdf,True)
    preview=service.preview_exam_weights({target['target_id']:1.5},14)
    service.guide.store.save_dataset({'institutions':['Banca A'],'observed_date':'2026-10-15','unit':'questoes',
        'rows':[{'path':topic.qbank.path,'value':99,'band':'alta'}]})
    with pytest.raises(ValueError): service.apply_exam_weights(preview)


def test_apply_checks_planning_token_inside_the_profile_transaction(tmp_path,sample_pdf,monkeypatch):
    service,target,topic=configured(tmp_path,sample_pdf,True)
    preview=service.preview_exam_weights({target['target_id']:1.5},14)
    original=service.store.save_profile
    def concurrent(profile,expected_id,**kwargs):
        service.guide.store.save_dataset({'institutions':['Banca A'],'observed_date':'2026-10-15','unit':'questoes',
            'rows':[{'path':topic.qbank.path,'value':79,'band':'alta'}]})
        return original(profile,expected_id,**kwargs)
    monkeypatch.setattr(service.store,'save_profile',concurrent)
    with pytest.raises(ValueError): service.apply_exam_weights(preview)
    assert service.store.profile()['id']==0


def test_weight_comparison_includes_quantity_changes_and_newly_admitted_themes():
    from osler.mock_schedule import calendar_changes
    before=[{'date':'2026-10-15','items':[{'topic_id':'A','path':['Área','A'],'questions':10,'priority':'normal'}]}]
    after=[{'date':'2026-10-15','items':[{'topic_id':'A','path':['Área','A'],'questions':20,'priority':'normal'},
                                    {'topic_id':'B','path':['Área','B'],'questions':10,'priority':'alta'}]}]
    changes=calendar_changes(before,after,include_quantities=True,include_additions=True)
    assert {r['topic_id'] for r in changes}=={'A','B'}
    assert next(r for r in changes if r['topic_id']=='A')['after_questions']==20


def test_legacy_weights_do_not_reactivate_just_because_individual_files_arrive(tmp_path,sample_pdf):
    service,target,topic=configured(tmp_path,sample_pdf)
    p=replace(AdaptiveProfile(),exam_weights={target['target_id']:1.5})
    with service.repository._connection() as db:
        db.execute('INSERT INTO study_profiles(payload,created_at) VALUES(?,?)',(json.dumps(p.to_dict()),'2026-10-15'))
    for institution in ['Banca A','Banca B']:
        service.guide.store.save_dataset({'institutions':[institution],'observed_date':'2026-10-15','unit':'questoes',
            'rows':[{'path':topic.qbank.path,'value':100,'band':'alta'}]})
    assert not service.store.profile()['weight_policy']['allowed']
    assert service.store.profile()['profile']['institution_weights']=={'Banca A':1,'Banca B':1}
    preview=service.preview_exam_weights({target['target_id']:1.5},14)
    service.apply_exam_weights(preview)
    assert service.store.profile()['weight_policy']['allowed']


def test_legacy_raw_weights_can_be_cleared_by_preview_without_individual_files(tmp_path,sample_pdf):
    service,_,_=configured(tmp_path,sample_pdf)
    p=replace(AdaptiveProfile(),institution_weights={'Banca A':1.5,'Banca B':1})
    with service.repository._connection() as db:
        db.execute('INSERT INTO study_profiles(payload,created_at) VALUES(?,?)',(json.dumps(p.to_dict()),'2026-10-15'))
    assert service.exam_weight_eligibility({})['allowed']
    preview=service.preview_exam_weights({},14)
    assert preview['legacy_weights_before']=={'Banca A':1.5,'Banca B':1}
    assert preview['legacy_weights_after']=={'Banca A':1,'Banca B':1}
    assert preview['after']['weights']=={'Banca A':1,'Banca B':1}
    service.apply_exam_weights(preview)
    saved=service.store.profile()
    assert saved['configured_profile']['institution_weights']=={'Banca A':1,'Banca B':1}
    service.store.save_profile(replace(AdaptiveProfile(**saved['configured_profile']),max_questions=100),saved['id'])
