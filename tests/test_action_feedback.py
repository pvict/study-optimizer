from streamlit.testing.v1 import AppTest

APP='''
import streamlit as st
from osler.action_feedback import confirm_submit,notify_success
with st.form('sample'):
 value=st.number_input('Questões',1,100,20,key='count')
 save=confirm_submit('Salvar resultado',action_key='sample-save',key='sample-save',details=f'{value} questões')
if save:
 if value==13:st.error('Registro inválido')
 else:
  st.session_state['writes']=st.session_state.get('writes',0)+1
  notify_success(value,'Resultado salvo.')
  st.rerun()
st.write('Gravações: '+str(st.session_state.get('writes',0)))
'''


def test_cancel_confirm_once_and_success():
 app=AppTest.from_string(APP).run()
 app.button(key='sample-save').click().run()
 assert 'Gravações: 0' in str([m.value for m in app.markdown])
 app.button(key='action_cancel').click().run()
 assert not app.exception and app.session_state.get('writes',0)==0
 app.button(key='sample-save').click().run()
 app.button(key='action_confirm').click().run()
 assert not app.exception and app.session_state['writes']==1
 app.run();assert app.session_state['writes']==1
 assert len(app.toast)==0  # consumido uma única vez na execução anterior


def test_error_does_not_produce_success_toast():
 app=AppTest.from_string(APP).run()
 app.number_input(key='count').set_value(13)
 app.button(key='sample-save').click().run()
 app.button(key='action_confirm').click().run()
 assert app.error and not app.toast


def test_changed_values_invalidate_confirmation():
 app=AppTest.from_string(APP).run()
 app.session_state['preview']={'questions':20}
 app.button(key='sample-save').click().run()
 app.session_state['preview']={'questions':30}
 app.button(key='action_confirm').click().run()
 assert app.error and not app.toast and app.session_state.get('writes',0)==0


def test_callback_executes_once_only_after_confirmation():
 app=AppTest.from_string('''
import streamlit as st
from osler.action_feedback import confirm_button,notify_success
def commit():
 st.session_state['writes']=st.session_state.get('writes',0)+1
 notify_success(None,'Concluído.')
confirm_button('Desfazer registro',action_key='undo',key='undo',on_click=commit)
''').run()
 app.button(key='undo').click().run()
 assert app.session_state.get('writes',0)==0
 app.button(key='action_confirm').click().run()
 assert not app.exception and app.session_state['writes']==1 and app.toast
 app.run();assert app.session_state['writes']==1


def test_database_change_invalidates_pending_action(tmp_path,sample_pdf,monkeypatch):
 from test_mock_schedule import configured
 service,_=configured(tmp_path,sample_pdf)
 monkeypatch.setenv('CONFIRM_ROOT',str(service.repository.root))
 header='''
import os
from osler.storage import Repository
from osler.action_feedback import bind_actions
bind_actions(Repository(os.environ['CONFIRM_ROOT']))
'''
 app=AppTest.from_string(header+APP).run()
 app.button(key='sample-save').click().run()
 service.configure_day('2026-10-16',30,'normal',0)
 app.button(key='action_confirm').click().run()
 assert app.error and not app.toast and app.session_state.get('writes',0)==0


def test_failed_folder_activation_does_not_show_success(tmp_path,monkeypatch):
 from osler.storage import Repository
 import osler.backups_ui as backups_ui
 Repository(tmp_path/'data')
 Repository(tmp_path/'data-restaurada-active')
 monkeypatch.setenv('CONFIRM_PROJECT',str(tmp_path))
 def reject(*args):raise OSError('Não foi possível ativar a pasta')
 monkeypatch.setattr(backups_ui,'activate_data_dir',reject)
 app=AppTest.from_string('''
import os
from pathlib import Path
from osler.storage import Repository
from osler.action_feedback import bind_actions,flush_toast
from osler.backups_ui import render_backups
root=Path(os.environ['CONFIRM_PROJECT'])
repo=Repository(root/'data-restaurada-active')
bind_actions(repo)
render_backups(repo,root)
flush_toast()
''').run()
 next(b for b in app.button if b.label=='Abrir pasta preservada').click().run()
 assert not app.toast
 app.button(key='action_confirm').click().run()
 assert not app.exception and app.error and not app.toast
 assert 'restore_notice' not in app.session_state
