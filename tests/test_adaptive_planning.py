import pytest

from osler.adaptive_planning import posterior, incidence_weights, topic_states, allocate_day
from osler.study_models import AdaptiveProfile


def topic(name='Tema', total=100, answered=0):
    return {'topic_id':name,'path':['Área',name],'total':total,'answered_pdf':answered,
            'pdf_accuracy':{'value':90 if answered else None,'operator':'=','raw':'90%' if answered else '-'},'report_date':'2026-10-14','studied_cards':0}


def session(name='Tema', kind='bloco', mode='novas', day='2026-10-15', n=10, correct=9):
    return {'entry':{'path':['Área',name],'day':day,'kind':kind,'mode':mode,'questions':n,'correct':correct,'percent':None,'minutes':None,'last_contact':None}}


def test_beta_estimate_and_uncertainty_respect_sample_size():
    a, b = posterior(9,10), posterior(90,100)
    assert a['mean'] == pytest.approx(10/12)
    assert a['interval'][0] < .9 < a['interval'][1]
    assert a['sd'] > b['sd']
    assert posterior(0,0)['observed'] is None


def test_parent_incidence_mass_is_split_not_multiplied_and_missing_not_zero():
    topics = [topic('Um'),topic('Dois')]
    data = [{'id':1,'institutions':['A'],'unit':'questoes','observed_date':'2026-10-15','rows':[{'path':['Área'],'value':100,'band':'alta'}]}]
    result = incidence_weights(topics,data,{},'2026-10-15')
    assert result['weights']['Um'] == pytest.approx(.5)
    assert result['weights']['Dois'] == pytest.approx(.5)
    absent = incidence_weights(topics,[],{},'2026-10-15')
    assert absent['weights']['Um'] > 0 and absent['warnings']


def test_pooled_incidence_is_not_added_again_to_individual_tables():
    topics=[topic('Um'),topic('Dois')]
    def ds(i,institutions,values):
        return {'id':i,'institutions':institutions,'unit':'questoes','observed_date':'2026-10-15','rows':[{'path':t['path'],'value':v,'band':'alta'} for t,v in zip(topics,values)]}
    data=[ds(1,['A'],[90,10]),ds(2,['B'],[10,90]),ds(3,['A','B'],[50,50])]
    result=incidence_weights(topics,data,{'A':3,'B':1},'2026-10-15')
    assert result['weights']['Um'] == pytest.approx(.7)
    assert result['weights']['Dois'] == pytest.approx(.3)


def test_pdf_is_context_not_a_contact_or_binomial_sample():
    state=topic_states([topic(answered=44)],[],[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['last_contact'] is None
    assert state['performance']['exact_n'] == 0
    assert state['performance']['interval'] is None
    assert state['status'] == 'diagnostico'


def test_baseline_blocks_and_repeats_are_not_blindly_added():
    entries=[session(kind='acumulado',n=100,correct=90),session(n=10,correct=5),session(mode='repetidas',n=20,correct=20)]
    state=topic_states([topic()],entries,[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['performance']['exact_n'] == 10
    assert state['performance']['exact_correct'] == 5
    assert state['repeated']['exact_n'] == 20
    assert state['last_contact'] == '2026-10-15'


def test_low_accuracy_and_elapsed_time_generate_alert_without_fake_forgetting():
    state=topic_states([topic(answered=40)],[session(day='2026-09-15',correct=3)],[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['priority'] == 'urgente'
    assert state['days_without_contact'] == 30
    assert 'memory_percent' not in state


@pytest.mark.parametrize('minutes', [15,30,60,120,240])
def test_daily_integer_allocation_fits_time_and_preserves_exploration(minutes):
    topics=[topic('Novo'),topic('Revisar',answered=50),topic('Outro',answered=50)]
    states=topic_states(topics,[session('Revisar',correct=3),session('Outro',correct=8)],[],{},'2026-10-15',AdaptiveProfile())
    result=allocate_day(states,AdaptiveProfile(),minutes,'normal',[],'2026-10-15')
    assert all(type(i['questions']) is int and i['questions']>0 for i in result['items'])
    assert sum(i['questions'] for i in result['items']) == result['questions']
    assert result['planned_minutes'] <= minutes
    assert result['questions'] <= 60
    if result['budget']>=sum(t['recommended_questions'] for t in states[:1]+[t for t in states if t['topic_id']=='Novo']):
        assert any(i['topic_id']=='Novo' for i in result['items'])
    assert all(i['questions']>=min(AdaptiveProfile().min_block,result['budget']) for i in result['items'])


def test_rest_and_completed_today_do_not_create_more_daily_debt():
    states=topic_states([topic()],[],[],{},'2026-10-15',AdaptiveProfile())
    assert allocate_day(states,AdaptiveProfile(),120,'descanso',[],'2026-10-15')['items'] == []
    done=[session(n=60,correct=50)]
    assert allocate_day(states,AdaptiveProfile(),120,'normal',done,'2026-10-15')['items'] == []


def test_recording_part_of_today_subtracts_instead_of_creating_extra_tasks():
    states=topic_states([topic()],[],[],{},'2026-10-15',AdaptiveProfile())
    initial=allocate_day(states,AdaptiveProfile(),120,'normal',[],'2026-10-15')
    remaining=allocate_day(states,AdaptiveProfile(),120,'normal',[session(n=5,correct=4)],'2026-10-15')
    assert remaining['questions'] <= initial['questions']-5


def test_maximum_topics_is_respected_with_new_topic_reservation():
    states=topic_states([topic('Novo'),topic('Visto',answered=40)],[],[],{},'2026-10-15',AdaptiveProfile())
    result=allocate_day(states,AdaptiveProfile(max_topics=1),120,'normal',[],'2026-10-15')
    assert len(result['items']) <= 1


def test_successful_contact_after_card_reduction_resets_its_due_alert():
    reduced={**topic(answered=44),'cards_reduced_day':'2026-10-01'}
    state=topic_states([reduced],[session(n=20,correct=19)],[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['priority']=='normal'
    assert 'após redução' not in state['reason']


def test_latest_guide_contact_wins_even_when_history_is_descending():
    contacts=[(['Área','Tema'],'2026-10-15'),(['Área','Tema'],'2026-09-01')]
    state=topic_states([topic(answered=44)],[],[],{},'2026-10-15',AdaptiveProfile(),contacts)[0]
    assert state['last_contact']=='2026-10-15'


@pytest.mark.parametrize('mode',['repetidas','mistas'])
def test_adverse_other_mode_raises_alert_without_pooling_samples(mode):
    entries=[session(n=1,correct=1),session(mode=mode,n=20,correct=0)]
    state=topic_states([topic(answered=100)],entries,[],{},'2026-10-15',AdaptiveProfile())[0]
    assert state['priority']=='urgente'
    assert state['performance']['exact_n']==1
    assert state['alert_signal']['mode']==mode
    assert 'erros' in state['reason'].lower()


def test_zero_exploration_does_not_replace_urgent_review_with_new_topic():
    p=AdaptiveProfile(max_topics=1,new_share=0)
    states=topic_states([topic('Novo'),topic('Urgente',answered=40)],[session('Urgente',correct=0)],[],{},'2026-10-15',p)
    result=allocate_day(states,p,120,'normal',[],'2026-10-18')
    assert [i['topic_id'] for i in result['items']]==['Urgente']


def test_undated_pdf_conservatively_subtracts_recorded_new_attempts():
    t={**topic(),'report_date':None}
    state=topic_states([t],[session(n=100,correct=90)],[],{},'2026-10-16',AdaptiveProfile())[0]
    assert state['available_new']==0
    assert state['bank_balance_uncertain']
