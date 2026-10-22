from osler.evolution_performance import performance_history,performance_outlook
from test_adaptive_planning import session


def measured(day,n=20,correct=16,mode='novas',confident=12):
    e=session(day=day,n=n,correct=correct,mode=mode)
    e['entry']['confident_correct']=confident
    return e


def test_performance_does_not_use_repeated_or_future_results():
    events=[measured('2026-10-01'),measured('2026-10-08'),measured('2026-10-10',mode='repetidas'),measured('2026-10-20')]
    model=performance_history(events,'2026-10-15')
    assert model['questions']==40 and model['accuracy']==.8
    assert model['conviction']==.6
    assert len(model['weekly'])==2


def test_no_data_is_not_zero_and_long_term_accuracy_is_not_invented():
    assert performance_outlook(performance_history([],'2026-10-15'),'2027-11-30')['estimate'] is None
    events=[measured('2026-10-01'),measured('2026-10-08')]
    m=performance_history(events,'2026-10-15')
    assert performance_outlook(m,'2027-11-30')['estimate'] is None
    assert 0<=m['interval'][0]<m['accuracy']<m['interval'][1]<=1


def test_validated_trend_is_bounded_and_stationary_reference_can_win():
    from datetime import date,timedelta
    events=[]
    for i in range(8):
        e=measured((date(2026,8,25)+timedelta(days=7*i)).isoformat(),100,40+5*i,confident=35+5*i)
        e['entry']['path']=['Área',str(i%3)]; events.append(e)
    model=performance_history(events,'2026-10-15')
    assert model['trend_selected'] and model['validation']['folds']>=3
    estimate=performance_outlook(model,'2026-10-29')
    assert 0<=estimate['lower']<=estimate['estimate']<=estimate['upper']<=1
    for e in events: e['entry']['correct']=60; e['entry']['confident_correct']=50
    model=performance_history(events,'2026-10-15')
    assert not model['trend_selected']
    assert performance_outlook(model,'2026-10-29')['estimate']==.6


def test_old_large_sample_does_not_unlock_projection_from_tiny_recent_sample():
    events=[measured('2026-01-01',1000,800,confident=700)]
    for i,day in enumerate(['2026-09-21','2026-09-28','2026-10-05','2026-10-12']):
        e=measured(day,5,4,confident=3); e['entry']['path']=['Área',str(i%3)]; events.append(e)
    assert performance_outlook(performance_history(events,'2026-10-15'),'2026-10-20')['estimate'] is None


def test_calendar_recency_ignores_old_measurements_and_uses_actual_elapsed_days():
    old=measured('2024-01-01',1000,900,confident=800)
    tiny=measured('2026-10-20',5,0,confident=0); tiny['entry']['path']=['Área','B']
    assert performance_outlook(performance_history([old,tiny],'2026-10-21'),'2026-11-04')['estimate'] is None
    sunday=measured('2026-10-18'); monday=measured('2026-10-19'); monday['entry']['path']=['Área','B']
    m=performance_history([sunday,monday],'2026-10-20')
    assert m['span']==1
    assert performance_outlook(m,'2026-10-27')['estimate'] is None


def test_theme_spelling_variants_do_not_manufacture_diversity():
    a=measured('2026-10-01'); a['entry']['path']=['Área','Tema']
    b=measured('2026-10-08'); b['entry']['path']=['área','tema']
    m=performance_history([a,b],'2026-10-15')
    assert m['topics']==1
    assert performance_outlook(m,'2026-10-20')['estimate'] is None
