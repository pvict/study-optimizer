from streamlit.testing.v1 import AppTest
from osler.adaptive_service import AdaptiveService


def test_strategy_ui_requires_preview_and_can_show_saved_changes(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    repo,*_=setup_assessment(tmp_path,sample_pdf)
    s=AdaptiveService(repo); monkeypatch.setenv('BALANCED_UI_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.review_strategy_ui import render_review_strategy
render_review_strategy(AdaptiveService(Repository(os.environ['BALANCED_UI_ROOT'])))
''',default_timeout=60).run()
    assert not app.exception
    app.radio[0].set_value('balanced_v2').run()
    assert s.store.profile()['configured_profile']['review_strategy']=='legacy_v1'
    app.button(key='review_strategy_preview').click().run()
    assert not app.exception and app.dataframe
    app.button(key='review_strategy_apply').click().run()
    assert not app.exception
    assert s.store.profile()['configured_profile']['review_strategy']=='balanced_v2'
    assert len(s.review_strategy_history())==1


def test_balanced_feedback_explains_combined_total_without_confidence_goal():
    from test_balanced_reviews import block,state,profile
    e=block(); t=state([e]); view={'states':[t],'sessions':[e],'date':'2026-10-09',
        'profile':profile().to_dict(),'review_queue':t['pending_reviews']}
    app=AppTest.from_string('from osler.study_activity_ui import render_result_feedback\nrender_result_feedback('+repr(view)+','+repr(e['session_id'])+')').run()
    assert not app.exception
    assert any('mesmo bloco' in m.value for m in app.info)
    assert not any('Convicção abaixo da meta' in m.value for m in app.warning)


def test_calendar_today_exposes_linked_lot_and_complement_actions(tmp_path,sample_pdf,monkeypatch):
    from test_assessments import setup_assessment
    from osler.study_models import AdaptiveProfile,StudyEntry
    repo,*_,topic=setup_assessment(tmp_path,sample_pdf); s=AdaptiveService(repo)
    s.store.save_profile(AdaptiveProfile(review_strategy='balanced_v2',target_accuracy=95),0)
    s.save_entry(StudyEntry(topic.qbank.path,'2026-10-08',19,17,confident_correct=15),'origin')
    monkeypatch.setenv('BALANCED_UI_ROOT',str(tmp_path))
    app=AppTest.from_string('''
import os
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.study_calendar_ui import render_calendar
render_calendar(AdaptiveService(Repository(os.environ['BALANCED_UI_ROOT'])),lambda *args:None,lambda *args:None)
''',default_timeout=90).run()
    assert not app.exception
    assert any(b.label=='Registrar lote de 4 respostas' for b in app.button)
    assert any('Registrar complemento de' in b.label for b in app.button)
