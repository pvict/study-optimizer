from dataclasses import replace
import pytest
from streamlit.testing.v1 import AppTest
from osler.study_models import StudyEntry
from osler.study_registration_ui import entry_validation,first_block_action
from osler.adaptive_service import AdaptiveService
from test_assessments import setup_assessment


def item(**changes):
    return {'topic_id':'topic','questions':10,'new_questions':7,'repeat_questions':3,
            'pending_reviews':[],'review_kind':'theme',**changes}


def test_next_action_preserves_allocated_lot_budget_and_mode():
    lot={'session_id':'original','questions':18,'path':['Área','Tema'],'due_date':'2026-10-15'}
    action=first_block_action(item(review_kind='combined',pending_reviews=[lot]),'2026-10-15','balanced_v2')
    assert action['kind']=='lot' and action['entry']['questions']==10
    assert action['entry']['session_id']=='original'
    assert first_block_action(item(),'2026-10-15','balanced_v2')=={
        'kind':'record','topic_id':'topic','questions':10,'mode':'mistas'}
    assert first_block_action(item(new_questions=0,repeat_questions=10),'2026-10-15','balanced_v2')['mode']=='repetidas'
    assert first_block_action(item(new_questions=10,repeat_questions=0),'2026-10-15','balanced_v2')['mode']=='novas'


def test_field_validation_uses_domain_rules_and_preserves_unknown_conviction():
    entry=StudyEntry(['Área','Tema'],'2026-10-15',20,correct=21)
    assert entry_validation(entry)=={'correct':'Acertos não podem passar de 20.'}
    assert entry_validation(replace(entry,correct=17,confident_correct=18))=={'confident':'Convicção não pode passar dos 17 acertos.'}
    assert entry_validation(replace(entry,correct=17))=={}
    assert 'general' in entry_validation(replace(entry,correct=None,confident_correct=0))


def test_registration_visible_kind_inline_error_and_next_action_are_idempotent(tmp_path,monkeypatch,project_root,sample_pdf):
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(project_root/'app.py'),default_timeout=60).run()
    next(b for b in app.button if b.label=='Registrar este bloco').click().run()
    assert any(g.key=='study_kind' for g in app.get('button_group'))
    app.number_input(key='study_n').set_value(20)
    app.number_input(key='study_correct').set_value(21)
    next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run()
    assert not app.exception and any('Acertos não podem passar de 20' in e.value for e in app.error)
    assert app.number_input(key='study_correct').value==21
    assert not AdaptiveService(repo).store.events()
    app.number_input(key='study_correct').set_value(17)
    next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run()
    assert not app.exception and any('Salvo. Hoje: 20 de 60.' in h.value for h in app.get('html'))
    app.run();assert len(AdaptiveService(repo).store.events())==1
    view=AdaptiveService(repo).overview('2026-10-15')
    if view['plan']['items']:
        expected=first_block_action(view['plan']['items'][0],view['date'],view['profile']['review_strategy'])
        app.button(key='study_next_block').click().run()
        assert not app.exception and not app.session_state.get('study_saved')
        if expected['kind']=='lot':assert app.session_state['study_review_of']==expected['entry']['session_id']
        else:assert app.session_state['adaptive_topic']==expected['topic_id']
        assert len(AdaptiveService(repo).store.events())==1
