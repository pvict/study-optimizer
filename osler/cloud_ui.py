"""Entrada online autenticada; o modo local não importa este módulo."""
from collections import deque
import hashlib
import os
from pathlib import Path
import tempfile
import threading
import time

import streamlit as st

from .backups import create_backup, inspect_backup, restore_backup
from .cloud_access import session_valid, verify_password
from .cloud_store import CloudError, CloudWorkspace, _active
from .cloud_postgres import SupabasePostgres

_attempts, _attempt_lock = deque(), threading.Lock()


def _settings():
    try:
        config = dict(st.secrets['cloud'])
        mode=config.get('auth_mode','password')
        if mode not in ('password','streamlit_private'):
            raise ValueError()
        if not all(config.get(k) for k in ('host','user','password')) or (mode=='password' and not config.get('password_hash')):
            raise ValueError()
        return config
    except (KeyError, FileNotFoundError, ValueError):
        st.error('Acesso online ainda não configurado. Preencha os secrets conforme cloud/secrets.example.toml.')
        st.stop()


def _authenticate(config):
    if config.get('auth_mode')=='streamlit_private':
        # Opt-in administrativo somente depois de confirmar Sharing=private.
        # A autenticação ocorre no proxy nativo do Community Cloud.
        return
    now = time.time()
    if session_valid(st.session_state.get('_cloud_login'),config['password_hash'],now):
        return
    st.title('Seu estudo, de onde estiver')
    with st.form('cloud_login'):
        password = st.text_input('Senha do aplicativo',type='password',key='_cloud_password')
        submitted = st.form_submit_button('Entrar',type='primary')
    if submitted:
        with _attempt_lock:
            while _attempts and now-_attempts[0] > 60:
                _attempts.popleft()
            allowed = len(_attempts) < 5
            if allowed:
                _attempts.append(now)
        if not allowed:
            st.error('Aguarde um minuto antes de tentar novamente.')
        elif verify_password(password,config['password_hash']):
            st.session_state['_cloud_login'] = (hashlib.sha256(config['password_hash'].encode()).hexdigest(),now)
            st.rerun()
        else:
            st.error('Senha incorreta.')
    st.stop()


@st.cache_resource(show_spinner=False)
def _workspace(host,user,password):
    directory = Path(tempfile.gettempdir())/'osler-online'/hashlib.sha256((host+user).encode()).hexdigest()[:16]
    # Um processo novo não reutiliza uma cópia local não confirmada de outro.
    directory = directory/str(os.getpid())/'data'
    return CloudWorkspace(directory, SupabasePostgres(host,user,password))


def _initialize(workspace):
    st.title('Trazer seu histórico')
    st.write('Envie o backup ZIP verificado do app local. O calendário e os registros serão preservados.')
    upload = st.file_uploader('Backup do Osler Study Optimizer',type=['zip'],key='cloud_initial_backup')
    verified = None
    if upload:
        try:
            verified = inspect_backup(upload.getvalue())
            st.write(f"{verified['reports']} relatórios · {verified['file_count']} arquivos")
        except (ValueError,OSError) as exc:
            st.error(str(exc))
    from .action_feedback import confirm_button, notify_success
    if confirm_button('Importar meu histórico',key='cloud_initialize',action_key='cloud_initialize',
                      disabled=verified is None,details='O backup será enviado ao seu projeto Supabase. O app local continuará preservado.'):
        restore_backup(upload.getvalue(),workspace.root)
        notify_success(True,'Histórico importado e salvo na nuvem.')
        st.rerun()


def _recovery(workspace):
    if workspace.pending and workspace.initialized:
        st.warning('Existe uma alteração que ainda não foi confirmada na nuvem. Não registre o mesmo bloco novamente. Tente atualizar ou baixe uma cópia de recuperação.')
        from .storage import Repository
        try:
            backup = create_backup(Repository(workspace.root))
            st.download_button('Baixar cópia de recuperação',backup.read_bytes(),backup.name,'application/zip',key='cloud_pending_backup')
        except (OSError,ValueError):
            st.error('Não foi possível preparar a cópia. Mantenha esta sessão aberta.')


def protected_run(function):
    # Dentro da mesma execução, a autenticação e o lease já foram verificados.
    if _active.get() is not None:
        return function()
    config = _settings()
    st.session_state['_cloud_auth_mode']=config.get('auth_mode','password')
    _authenticate(config)
    workspace = _workspace(config['host'],config['user'],config['password'])
    try:
        with workspace.cycle():
            os.environ['OSLER_DATA_DIR'] = str(workspace.root)
            st.session_state['active_data_dir'] = str(workspace.root)
            if not workspace.initialized:
                _initialize(workspace)
            else:
                return function()
    except CloudError as exc:
        st.error(str(exc))
        _recovery(workspace)
        st.stop()


def render_cloud_backups(repo):
    st.subheader('Backup e restauração')
    from .action_feedback import confirm_button
    if st.button('Preparar backup para baixar',key='cloud_prepare_backup'):
        backup = create_backup(repo)
        st.session_state['_cloud_backup_download'] = (backup.name,backup.read_bytes())
    available = st.session_state.get('_cloud_backup_download')
    if available:
        st.download_button('Baixar backup verificado',available[1],available[0],'application/zip',key='cloud_download_backup')
    with st.expander('Restaurar outro backup'):
        st.write('Baixe uma cópia atual antes de restaurar. O backup escolhido passará a valer em todos os seus dispositivos.')
        uploaded = st.file_uploader('Backup ZIP',type=['zip'],key='cloud_restore_upload')
        verified = None
        if uploaded:
            try:
                verified = inspect_backup(uploaded.getvalue())
                st.write(f"Backup verificado · {verified['file_count']} arquivos")
            except (ValueError,OSError) as exc:
                st.error(str(exc))
        if confirm_button('Restaurar histórico online',key='cloud_restore',action_key='cloud_restore',
                          disabled=verified is None,details='O histórico deste backup substituirá a versão online para todos os dispositivos. Preserve um backup atual antes de confirmar.'):
            current = _active.get()
            with tempfile.TemporaryDirectory(prefix='osler-cloud-restore-',dir=repo.root.parent) as folder:
                stage = Path(folder)/'incoming'
                restore_backup(uploaded.getvalue(),stage)
                repo.root.rename(Path(folder)/'previous')
                stage.rename(repo.root)
                current.checkpoint()
            # Rascunhos e tokens antigos não devem operar na base restaurada.
            login = st.session_state.get('_cloud_login')
            st.session_state.clear()
            st.session_state['_cloud_login'] = login
            st.session_state['_action_toast'] = 'Histórico restaurado e salvo na nuvem.'
            st.rerun()
