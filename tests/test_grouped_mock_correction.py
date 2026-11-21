"""Erros individuais continuam válidos quando a agenda usa grupos de subtemas."""
from copy import deepcopy
from dataclasses import replace

import pytest

from osler.adaptive_service import AdaptiveService
from osler.mock_exams import MockExams, MockExam
from osler.planner_service import today_local
from osler.storage import Repository
from osler.study_models import AdaptiveProfile
from osler.exam_practice import validate_errors,correction_doses
from test_topic_grouping import fixture


def setup_grouped(tmp_path,monkeypatch,mode):
    service=AdaptiveService(Repository(tmp_path))
    topics,datasets,profile=fixture();day=today_local().isoformat()
    for topic in topics:
        topic['path']=['Clínica Médica','Gastroenterologia','Pâncreas']+topic['path'][3:]
        topic.update(answered_pdf=0,pdf_accuracy={'value':None,'operator':None,'raw':'-'},report_date=day,
                     studied_cards=None,planner_snapshot=None)
    for row in datasets[0]['rows']:
        row['path']=['Clínica Médica','Gastroenterologia','Pâncreas']+row['path'][3:]
    datasets[0]['observed_date']=day
    monkeypatch.setattr(service,'catalog',lambda as_of,include_parents=False:(topics if include_parents else topics[1:],{}))
    service.guide.store.save_dataset({k:v for k,v in datasets[0].items() if k!='id'})
    service.store.save_profile(replace(profile,grouping_mode=mode,grouping_paths=[topics[0]['path']] if mode=='custom' else [],
                                       start_date=day,review_strategy='balanced_v2',max_questions=60,max_topics=4),0)
    return service,topics,day


@pytest.mark.parametrize('mode',['balanced','custom'])
@pytest.mark.parametrize('area_train',[False,True])
def test_specific_error_is_scheduled_even_when_hidden_inside_a_group(tmp_path,monkeypatch,mode,area_train):
    service,topics,day=setup_grouped(tmp_path,monkeypatch,mode)
    if area_train:
        service.apply_area_schedule(service.preview_area_schedule(day,'2026-10-30',1,20,['USP']))
        exam=service.register_area_result('area-'+day,day,20,16,token=service.agenda.token())
    else:exam=MockExams(service.repository).save(MockExam(day,20,16,institution='USP'))
    service.save_mock_errors(exam['exam_key'],exam['version'],[{'path':topics[1]['path'],'errors':3}],0,service.agenda.token())
    view=service.overview(day)
    assert any(t['topic_id']=='parent' and 'A' in t['group_members'] for t in view['planning_states'])
    assert not any(t['topic_id']=='A' for t in view['planning_states'])
    errors=deepcopy(service.mock_errors(exam['exam_key']))
    events=service.store.events();profile=service.store.profile()
    preview=service.preview_mock_correction(exam['exam_key'],'2026-10-16',30)
    assert preview['rows'] and not preview['unassigned']
    assert preview['selected']==['A'] and preview['rows'][0]['path']==topics[1]['path']
    assert service.store.events()==events and service.mock_errors(exam['exam_key'])==errors
    assert service.store.profile()==profile
    service.apply_mock_correction(preview)
    next_day=service.overview(preview['rows'][0]['date'])
    assert any(i['topic_id']=='A' and i.get('source_exam_key')==exam['exam_key'] for i in next_day['plan']['items'])
    assert not any(i.get('group_members') and 'A' in i['group_members'] for i in next_day['plan']['items'])
    assert next_day['plan']['questions']<=next_day['plan']['target_questions']


def test_missing_catalog_topic_names_the_path_and_explains_how_to_fix():
    with pytest.raises(ValueError) as caught:
        validate_errors([{'path':['Clínica Cirúrgica','Pâncreas','Neoplasias Císticas'],'errors':2}],[],4)
    message=str(caught.value)
    assert 'Neoplasias Císticas' in message and 'Clínica Cirúrgica' in message
    assert 'Adicionar um tema errado' in message and 'salvos' in message


def test_missing_individual_evidence_is_not_misreported_as_a_deleted_topic():
    with pytest.raises(ValueError) as caught:
        correction_doses([{'topic_id':'gone','path':['Área','Tema específico'],'errors':2}],[],10)
    message=str(caught.value)
    assert 'Tema específico' in message and 'dados individuais' in message
    assert 'Atualize a prévia' in message and 'salvos' in message
    assert 'saiu do catálogo' not in message


@pytest.mark.parametrize('institution',['USP','Outra instituição'])
def test_grouping_keeps_individual_incidence_and_dose_equal_to_separate_mode(tmp_path,monkeypatch,institution):
    service,topics,day=setup_grouped(tmp_path,monkeypatch,'balanced')
    exam=MockExams(service.repository).save(MockExam(day,20,16,institution=institution))
    service.save_mock_errors(exam['exam_key'],exam['version'],[
        {'path':topics[1]['path'],'errors':3},{'path':topics[2]['path'],'errors':1}],0,service.agenda.token())
    grouped=service.preview_mock_correction(exam['exam_key'],'2026-10-16',60)
    profile=service.store.profile()
    service.store.save_profile(replace(AdaptiveProfile(**profile['configured_profile']),grouping_mode='osler'),profile['id'])
    separate=service.preview_mock_correction(exam['exam_key'],'2026-10-16',60)
    values=lambda preview:[(r['topic_id'],r['weight'],r['questions']) for r in preview['rows']]
    assert values(grouped)==values(separate)
