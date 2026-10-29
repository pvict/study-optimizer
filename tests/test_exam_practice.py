from itertools import product

import pytest

from osler.exam_practice import AREAS, area_rotation, validate_errors, correction_doses, next_correction_day


def test_rotation_covers_every_institution_area_without_shift_on_move():
    institutions=['UNESP','SUS-SP','HMMG','FMUSP','FMUSP-RP']
    rows=area_rotation('2026-10-19','2027-05-01',1,20,institutions)
    assert {(r['institution'],r['area']) for r in rows}==set(product(institutions,AREAS))
    assert len({r['date'] for r in rows})==len(rows)
    moved=area_rotation('2026-10-19','2027-05-01',1,20,institutions,{rows[0]['id']:'2026-10-20'})
    assert moved[0]['date']=='2026-10-20'
    assert moved[1:]==rows[1:]


def test_two_weekly_sessions_and_collision_validation():
    rows=area_rotation('2026-10-19','2026-11-01',2,20,['UNESP'])
    assert [r['date'] for r in rows]==['2026-10-19','2026-10-22','2026-10-26','2026-10-29']
    with pytest.raises(ValueError): area_rotation('2026-10-19','2026-11-01',2,20,['UNESP'],{rows[0]['id']:rows[1]['date']})
    with pytest.raises(ValueError): area_rotation('2026-10-19','2026-11-01',0,20,['UNESP'])
    assert next_correction_day('2026-10-25',2)=='2026-10-28'


def test_error_counts_are_not_accuracy_and_unknown_is_not_zero():
    catalog=[{'topic_id':'a','path':['Área','A']},{'topic_id':'b','path':['Área','B']}]
    result=validate_errors([{'path':['Área','A'],'errors':2},{'path':['Área','B'],'errors':None}],catalog,4)
    assert result[1]['errors'] is None
    assert not any('correct' in r or 'accuracy' in r for r in result)
    for rows in ([{'path':['Área','A'],'errors':5}], [{'path':['Área'],'errors':1}],
                 [{'path':['Área','A'],'errors':True}], [{'path':['Área','A'],'errors':2}]*2):
        with pytest.raises(ValueError): validate_errors(rows,catalog,3)


def test_doses_use_incidence_and_difficulty_without_inflation_or_unbounded_errors():
    states=[{'topic_id':k,'path':['Área',k],'total':100,'recommended_questions':25,
             'importance':i,'performance':{'observed':p}} for k,i,p in [('a',.9,.5),('b',.1,.9)]]
    errors=[{'topic_id':s['topic_id'],'path':s['path'],'errors':2} for s in states]
    doses=correction_doses(errors,states,10)
    assert 10<=doses[1]['questions']<doses[0]['questions']<=25
    assert doses[0]['weight']>doses[1]['weight']
    assert all(r['questions']<=25 for r in correction_doses(errors,states,10))


def test_correction_limit_is_not_total_day_capacity():
    from osler.exam_practice import schedule_corrections
    from osler.study_models import AdaptiveProfile
    p=AdaptiveProfile(max_questions=120,max_topics=5,exam_date='2026-11-01')
    existing={'topic_id':'old','path':['A','Old'],'date':'2026-10-15','remaining':60,'new_topic':True}
    doses=[{'topic_id':'a','path':['A','New'],'questions':20,'weight':1}]
    rows,left=schedule_corrections(doses,p,'2026-10-15',40,{}, {'rows':[existing],'overrides':{}},{})
    assert not left and rows[0]['date']=='2026-10-15'
    rows,left=schedule_corrections(doses,p,'2026-10-15',10,{}, {'rows':[],'overrides':{}},{})
    assert not rows and left  # Never truncate a useful dose just to fill 10.


def test_correction_spills_and_respects_protected_days_area_load_and_actuals():
    from osler.exam_practice import schedule_corrections
    from osler.study_models import AdaptiveProfile
    p=AdaptiveProfile(max_questions=40,max_topics=2,exam_date='2026-10-20')
    doses=[{'topic_id':str(i),'path':['A',str(i)],'questions':20,'weight':1} for i in range(3)]
    agenda={'rows':[],'overrides':{'2026-10-15':{'mode':'mock_reserved'},'2026-10-16':{'area_reserved':30}}}
    rows,left=schedule_corrections(doses,p,'2026-10-15',40,{},agenda,{'2026-10-17':{'total':30,'slots':1}})
    assert not left
    assert [r['date'] for r in rows]==['2026-10-18','2026-10-18','2026-10-19']
