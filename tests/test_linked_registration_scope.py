from streamlit.testing.v1 import AppTest
from ui_actions import confirm_action
from test_assessments import setup_assessment
from osler.adaptive_service import AdaptiveService
from osler.study_models import StudyEntry


def test_can_leave_wrong_review_link_without_losing_results(tmp_path,sample_pdf,monkeypatch):
 repo,*_,topic=setup_assessment(tmp_path,sample_pdf)
 s=AdaptiveService(repo)
 s.save_entry(StudyEntry(topic.qbank.path,'2026-10-08',30,correct=22,confident_correct=10),'origin')
 monkeypatch.setenv('REVIEW_SCOPE_ROOT',str(repo.root))
 app=AppTest.from_string('''
import os,streamlit as st
from osler.storage import Repository
from osler.adaptive_service import AdaptiveService
from osler.adaptive_ui import _go_record,_go_review,_back_to_plan,_edit
from osler.study_registration_ui import render_registration
from osler.action_feedback import bind_actions,flush_toast
s=AdaptiveService(Repository(os.environ['REVIEW_SCOPE_ROOT']))
bind_actions(s.repository)
if 'scope_initialized' not in st.session_state:
 _go_review({'path':s.store.active('2026-10-15')[0]['entry']['path'],'session_id':'origin','questions':20})
 st.session_state['scope_initialized']=True
render_registration(s,_go_record,_go_review,_back_to_plan,_edit)
flush_toast()
''',default_timeout=60).run()
 assert not app.exception
 assert any('20 questões disponíveis' in i.value for i in app.info)
 app.number_input(key='study_n').set_value(27)
 app.number_input(key='study_correct').set_value(19)
 app.number_input(key='study_confident').set_value(11)
 next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run()
 assert not app.exception and any('27 questões' in e.value and '20 disponíveis' in e.value for e in app.error)
 assert len(s.store.events())==1
 app.button(key='study_detach_review').click().run()
 assert not app.exception and not app.session_state.get('study_review_of')
 assert app.number_input(key='study_n').value==27
 assert app.number_input(key='study_correct').value==19
 assert app.number_input(key='study_confident').value==11
 assert app.selectbox(key='study_mode').value=='mistas'
 confirm_action(next(b for b in app.button if b.label=='Salvar resultado e atualizar meu plano').click().run())
 assert not app.exception
 saved=[r['entry'] for r in s.store.active('2026-10-15') if r['session_id']!='origin']
 assert len(saved)==1 and saved[0]['questions']==27 and saved[0]['review_of'] is None
