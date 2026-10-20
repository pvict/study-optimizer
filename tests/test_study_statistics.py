import pytest

from osler.study_statistics import period_bounds, topic_statistics
from test_adaptive_planning import session


def state():
    return {'topic_id':'Tema','path':['Área','Tema'],'priority':'alta','status':'revisao','importance':.1,
            'answered_pdf':100,'pdf_accuracy':{'raw':'95%'},'last_contact':'2026-10-15'}


def test_calendar_periods_cross_month_and_year_without_rolling_30_day_shortcut():
    assert period_bounds('Dia','2026-10-15')==('2026-10-15','2026-10-15')
    assert period_bounds('Semana','2026-01-01')==('2025-12-29','2026-01-01')
    assert period_bounds('Mês','2026-03-31')==('2026-03-01','2026-03-31')
    assert period_bounds('Todo o período','2026-10-15')==(None,'2026-10-15')
    with pytest.raises(ValueError): period_bounds('Ano','2026-10-15')


def test_period_table_uses_weighted_exact_accuracy_and_separate_approximate_pdf():
    a=session(n=10,correct=9)
    b=session(n=2,correct=1)
    approx=session(n=20,correct=None,mode='mistas')
    approx['entry']['percent']=80
    events=[a,b,approx,session(kind='acumulado',n=100,correct=95),session(day='2026-10-14',n=50,correct=40),session(day='2026-10-16',n=50,correct=40)]
    row=topic_statistics([state()],events,'Dia','2026-10-15')[0]
    assert row['Questões']==32
    assert row['Acerto (%)']==pytest.approx(100*10/12)
    assert row['Acerto aproximado (%)']==80
    assert row['Questões aproximadas']==20
    assert row['Respondidas no PDF']==100
    assert row['Novas']==12 and row['Mistas']==20


def test_mode_filter_and_empty_period_do_not_fabricate_accuracy():
    events=[session(mode='repetidas',n=10,correct=2)]
    row=topic_statistics([state()],events,'Dia','2026-10-15','Novas')[0]
    assert row['Questões']==0 and row['Acerto (%)'] is None
    repeated=topic_statistics([state()],events,'Dia','2026-10-15','Repetidas')[0]
    assert repeated['Acerto (%)']==20


def test_recorded_topic_outside_current_catalog_keeps_its_real_statistics():
    rows=topic_statistics([],[session(n=10,correct=8)],'Dia','2026-10-15')
    assert len(rows)==1
    assert rows[0]['Questões']==10 and rows[0]['Acerto (%)']==80
    assert rows[0]['Respondidas no PDF'] is None
    assert not rows[0]['catalog_available']
