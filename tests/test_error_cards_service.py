from datetime import timedelta
import pytest
from osler.error_cards_service import ErrorCardsService
from osler.storage import Repository
from osler.models import stable_topic_id
from osler.planner_service import today_local
from test_error_cards import node


def setup(tmp_path):
    s=ErrorCardsService(Repository(tmp_path)); day=today_local().isoformat()
    html=('<div>'+node('Área',200,branch='down')+node('A',100,20)+node('B',100,20)+'</div>').encode()
    return s,day,html


def test_inventory_is_not_a_backlog_and_does_not_auto_start(tmp_path):
    s,day,html=setup(tmp_path); sid=s.import_html(html,'cards.html',day,'inventory',s.token())
    assert s.overview(day,question_view={'states':[],'plan':{'items':[]}})['items']==[]
    assert s.latest_snapshot()['id']==sid and s.latest_snapshot()['scope']=='inventory'
    assert s.import_html(html,'cards.html',day,'inventory',s.token())==sid


def test_first_pass_repeats_undo_and_stale_writes(tmp_path):
    s,day,html=setup(tmp_path); s.import_html(html,'cards.html',day,'pending',s.token())
    topic=stable_topic_id(['Área','A']); token=s.token()
    event=s.record(topic,day,20,5,15,'one',token)
    v=s.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert v['remaining']==180 and v['done_today']==25 and v['covered']==20
    assert s.record(topic,day,20,5,15,'one',token)==event
    with pytest.raises(ValueError):s.record(topic,day,10,0,9,'two',token)
    with pytest.raises(ValueError):s.record(topic,day,81,0,None,'too-much',s.token())
    s.undo(event,s.token()); assert s.overview(day,question_view={'states':[],'plan':{'items':[]}})['remaining']==200
    assert len(s.history())==1 and s.history()[0]['voided']


def test_new_snapshot_replaces_counts_without_double_subtracting(tmp_path):
    s,day,html=setup(tmp_path); s.import_html(html,'cards.html',day,'pending',s.token())
    s.record(stable_topic_id(['Área','A']),day,20,0,None,'one',s.token())
    fresh=('<div>'+node('Área',180,branch='down')+node('A',80,20)+node('B',100,20)+'</div>').encode()
    s.import_html(fresh,'fresh.html',day,'pending',s.token())
    v=s.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert v['remaining']==180 and v['done_today']==20 and v['covered']==0
    assert len(s.history())==1


def test_day_capacity_respects_routine_and_explicit_override(tmp_path):
    s,day,html=setup(tmp_path); s.import_html(html,'cards.html',day,'pending',s.token())
    q={'states':[],'plan':{'items':[],'kind':'descanso','routine_override':{'mode':'mock_reserved'}}}
    assert s.overview(day,question_view=q)['budget']==0
    s.configure(200,{day:120},s.token())
    v=s.overview(day,question_view=q)
    assert v['budget']==120 and sum(i['planned'] for i in v['items'])==100


def test_screenshot_expansion_keeps_snapshot_total_progress_and_original_nodes(tmp_path):
    s,day,_=setup(tmp_path)
    html=('<div>'+node('Área',30,branch='down')+node('A',10,20)+node('Grupo',20,20,'right')+'</div>').encode()
    sid=s.import_html(html,'cards.html',day,'pending',s.token())
    s.record(stable_topic_id(['Área','A']),day,5,0,None,'before-expansion',s.token())
    evidence=b'\x89PNG\r\n\x1a\nuser-supplied-evidence'
    event=s.expand_groups([{'parent_path':['Área','Grupo'],'children':[{'name':'B','count':8},{'name':'C','count':12}]}],evidence,'print.png',s.token())
    v=s.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert v['snapshot']['id']==sid and v['snapshot']['tree']['total']==30
    assert v['unallocated']==0 and v['remaining']==25 and v['covered']==5
    assert v['done_today']==5 and len(v['snapshot']['tree']['topics'])==3
    assert s.expand_groups([{'parent_path':['Área','Grupo'],'children':[{'name':'B','count':8},{'name':'C','count':12}]}],evidence,'print.png',s.token())==event
    assert len(s.history())==1


def test_screenshot_expansion_rejects_counts_that_do_not_match_the_parent(tmp_path):
    s,day,_=setup(tmp_path)
    html=('<div>'+node('Área',20,branch='down')+node('Grupo',20,20,'right')+'</div>').encode()
    s.import_html(html,'cards.html',day,'pending',s.token())
    with pytest.raises(ValueError):s.expand_groups([{'parent_path':['Área','Grupo'],'children':[{'name':'B','count':21}]}],b'\x89PNG\r\n\x1a\n','print.png',s.token())


def test_expansion_uses_the_same_original_parent_path_when_aliases_exist(tmp_path):
    s,day,_=setup(tmp_path)
    html=(node('Area',10,branch='down')+node('Group',10,20,'right')+node('AREA',20,branch='down')+node('GROUP',20,20,'right')).encode()
    s.import_html(html,'aliases.html',day,'pending',s.token())
    s.expand_groups([{'parent_path':['AREA','GROUP'],'children':[{'name':'B','count':20}]}],b'\x89PNG\r\n\x1a\n','print.png',s.token())
    tree=s.latest_snapshot()['tree']
    assert tree['total']==30 and tree['schedulable']==20 and tree['unallocated']==10
    assert tree['schedulable']+tree['unallocated']==tree['total']


def test_today_and_first_forecast_day_match_question_topic_bonus(tmp_path):
    s,day,_=setup(tmp_path)
    s.import_html((node('Área',410,branch='down')+node('A',200,20)+node('B',210,20)).encode(),'cards.html',day,'pending',s.token())
    q={'states':[],'plan':{'items':[{'topic_id':stable_topic_id(['Área','A'])}]}}
    v=s.overview(day,question_view=q); forecast=s.forecast(v,2)
    assert [(t['topic_id'],t['planned']) for t in forecast['days'][0]['items']]==[(t['topic_id'],t['planned']) for t in v['items']]


def test_reaching_reference_does_not_drop_rest_of_started_deck(tmp_path):
    s,day,_=setup(tmp_path)
    s.import_html((node('Área',220,branch='down')+node('A',220,20)).encode(),'cards.html',day,'pending',s.token())
    s.record(stable_topic_id(['Área','A']),day,200,0,None,'partial',s.token())
    v=s.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert sum(t['planned'] for t in v['items'])==20
    assert s.forecast(v,2)['days'][0]['cards']==20


def test_invalid_registration_and_different_snapshot_stale_guard(tmp_path):
    s,day,html=setup(tmp_path); s.import_html(html,'cards.html',day,'pending',s.token()); token=s.token()
    with pytest.raises(ValueError):s.record('missing',day,1,0,None,'bad',token)
    with pytest.raises(ValueError):s.record(stable_topic_id(['Área','A']),day,2,0,3,'bad',token)
    with pytest.raises(ValueError):s.record(stable_topic_id(['Área','A']),(today_local()+timedelta(days=1)).isoformat(),2,0,None,'bad',token)


def test_settings_can_return_to_an_earlier_value_and_forecast_is_not_study(tmp_path):
    s,day,html=setup(tmp_path); s.import_html(html,'cards.html',day,'pending',s.token())
    s.configure(120,{},s.token()); s.configure(200,{},s.token()); s.configure(120,{},s.token())
    assert s.settings()['daily']==120
    before=s.token();v=s.overview(day,question_view={'states':[],'plan':{'items':[]}})
    forecast=s.forecast(v,10)
    assert forecast['completion'] is not None and sum(d['cards'] for d in forecast['days'])==200
    assert s.token()==before and s.history()==[]


def test_concurrent_snapshot_cannot_pair_old_view_with_new_token(tmp_path,monkeypatch):
    s,day,html=setup(tmp_path);sid=s.import_html(html,'cards.html',day,'pending',s.token())
    original=s.routine
    def concurrent():
        r=original()
        fresh=('<div>'+node('Área',180,branch='down')+node('A',80,20)+node('B',100,20)+'</div>').encode()
        s.import_html(fresh,'fresh.html',day,'pending',s.token())
        return r
    monkeypatch.setattr(s,'routine',concurrent)
    v=s.overview(day,question_view={'states':[],'plan':{'items':[]}})
    assert v['snapshot']['id']==sid
    with pytest.raises(ValueError):s.record(stable_topic_id(['Área','A']),day,5,0,None,'stale',v['token'])
