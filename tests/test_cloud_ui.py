import hashlib
from pathlib import Path

import pytest

from osler.cloud_access import password_hash, verify_password, session_valid
from osler.cloud_store import CloudError
from osler.cloud_postgres import SupabasePostgres


def test_password_hash_and_expiring_session():
    stored = password_hash('a-long-private-password')
    assert verify_password('a-long-private-password',stored)
    assert not verify_password('wrong',stored)
    assert not verify_password('a-long-private-password','malformed')
    fingerprint = hashlib.sha256(stored.encode()).hexdigest()
    assert session_valid((fingerprint,100),stored,200)
    assert not session_valid((fingerprint,100),stored,100+12*3600+1)
    assert not session_valid((fingerprint,100),password_hash('a-different-password'),200)


def test_no_credentials_sent_to_untrusted_host():
    for host in ['http://example.supabase.co','aws-1-us-west-2.pooler.supabase.com.evil.org','127.0.0.1','aws-1-us-west-2.pooler.supabase.com/api']:
        with pytest.raises(CloudError):
            SupabasePostgres(host,'osler_cloud.abcdefghijklmnopqrst','secret')


def test_local_import_does_not_load_network_or_cloud_runtime():
    import subprocess,sys
    result = subprocess.run([sys.executable,'-c',
        'import osler.ui; import sys; assert "osler.cloud_store" not in sys.modules; assert "osler.cloud_ui" not in sys.modules'],
        capture_output=True,text=True)
    assert result.returncode == 0,result.stderr


def test_all_mutating_fragments_have_a_cloud_boundary():
    root = Path(__file__).resolve().parents[1]/'osler'
    for name in ['action_feedback.py','error_cards_ui.py','exam_practice_ui.py','mock_exams_ui.py','mock_result_followup_ui.py']:
        source = (root/name).read_text(encoding='utf-8')
        lines = source.splitlines()
        for i,line in enumerate(lines):
            if line.startswith('@st.fragment') or line.startswith('@st.dialog'):
                assert lines[i+1] == '@cloud_boundary', (name,line)


def test_failed_save_finalizes_receipt_before_retry(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    from osler import cloud_ui
    from osler.cloud_store import CloudWorkspace
    from test_cloud_store import MemoryRemote, seed, total
    remote=MemoryRemote()
    workspace=CloudWorkspace(tmp_path/'cloud',remote)
    with workspace.cycle():seed(workspace.root)
    monkeypatch.setenv('OSLER_CLOUD','1')
    monkeypatch.setenv('OSLER_DATA_DIR',str(tmp_path/'placeholder'))
    monkeypatch.setattr(cloud_ui,'_settings',lambda:{'host':'h','user':'u','password':'p'})
    monkeypatch.setattr(cloud_ui,'_authenticate',lambda config:None)
    monkeypatch.setattr(cloud_ui,'_workspace',lambda *args:workspace)
    # Recuperação usa backup do esquema real; aqui testamos só a barreira de UI.
    monkeypatch.setattr(cloud_ui,'_recovery',lambda ws:None)
    source='''
import streamlit as st
import sqlite3, os
from contextlib import closing
from osler.action_feedback import notify_success,flush_toast
from osler.cloud_ui import protected_run
def body():
 if 'receipt' not in st.session_state and st.button('Salvar',key='save'):
  with closing(sqlite3.connect(os.path.join(os.environ['OSLER_DATA_DIR'],'osler.sqlite3'))) as db,db:
   db.execute('insert into activity values (5)')
  saved=notify_success('receipt-1','Salvo.')
  st.session_state['receipt']=saved
  st.rerun()
 flush_toast()
protected_run(body)
'''
    app=AppTest.from_string(source).run()
    remote.fail=True
    app.button(key='save').click().run()
    assert app.session_state['receipt']=='receipt-1'
    assert workspace.pending and app.error and not app.toast
    remote.fail=False
    app.run()
    assert not app.exception and not workspace.pending
    assert total(workspace.root)==17
    assert app.session_state['receipt']=='receipt-1'
