"""Recuperação local em nova pasta, preservando sempre a anterior."""
from .action_feedback import confirm_button,confirm_submit,notify_success

from datetime import datetime
from pathlib import Path
import os
import sqlite3
import uuid

import streamlit as st

from .backups import create_backup, inspect_backup, restore_backup
from .workspace import activate_data_dir


def render_backups(repo, project_root):
    st.subheader("Backup e restauração")
    st.write("O backup inclui o banco consistente, os PDFs originais e as exportações. Os arquivos permanecem nesta máquina.")
    st.caption(f"Pasta de dados em uso: {repo.root}")
    if "restore_notice" in st.session_state:
        st.success(st.session_state.pop("restore_notice"))
        st.toast('Pasta de dados atualizada. A pasta anterior foi preservada.',icon=':material/check_circle:')
    if confirm_button("Criar backup local verificado", type="primary",action_key='backups_ui_20'):
        try:
            with st.spinner("Preservando e verificando os arquivos…"):
                created = notify_success(create_backup(repo),'Cópia de segurança criada.')
            st.session_state["backup_latest"] = str(created)
            st.success("Backup local criado e verificado.")
        except (ValueError, OSError, sqlite3.Error) as exc:
            st.error(str(exc))
    backups = sorted((repo.root/"backups").glob("*.zip"), reverse=True)
    if backups:
        chosen = st.selectbox("Backup local para baixar", backups, format_func=lambda p: p.name)
        if chosen.resolve().is_relative_to(repo.root) and not chosen.is_symlink():
            st.download_button("Baixar arquivo de backup", chosen.read_bytes(), chosen.name, "application/zip")
    st.divider()
    st.write("**Restaurar sem substituir os dados atuais**")
    st.caption("O conteúdo será verificado e aberto em uma nova pasta do projeto. A pasta anterior continuará disponível para voltar a ela.")
    uploaded = st.file_uploader("Arquivo ZIP de backup deste aplicativo", type=["zip"], key="restore_zip")
    verified = None
    if uploaded is not None:
        try:
            verified = inspect_backup(uploaded.getvalue())
            st.success(f"Backup válido: {verified['reports']} originais, {verified['file_count']} arquivos; versão de dados {verified['schema_version']}.")
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    if confirm_button("Restaurar em nova pasta e abrir", disabled=verified is None,action_key='backups_ui_44',details=f"Backup: {uploaded.name if uploaded else 'não selecionado'}. Será aberto em uma nova pasta. Seus dados atuais em {repo.root} serão preservados."):
        try:
            destination = Path(project_root)/f"data-restaurada-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
            restored = restore_backup(uploaded.getvalue(), destination)
            activate_data_dir(project_root, restored)
            st.session_state.clear()
            st.session_state["active_data_dir"] = str(restored)
            st.session_state["restore_notice"] = f"Dados restaurados e abertos. A pasta anterior permanece intacta: {repo.root}"
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    folders = [p for p in [Path(project_root)/"data", *sorted(Path(project_root).glob("data-restaurada-*"))] if (p/"osler.sqlite3").is_file() and p.resolve() != repo.root]
    if folders:
        with st.expander("Voltar para outra pasta local preservada"):
            target = st.selectbox("Pasta preservada", folders, format_func=lambda p: p.name)
            if confirm_button("Abrir pasta preservada",action_key='backups_ui_59',details=f"O aplicativo passará a usar {target}. Os dados atuais em {repo.root} serão preservados."):
                try:
                    activate_data_dir(project_root, target)
                    st.session_state.clear()
                    st.session_state["active_data_dir"] = str(target.resolve())
                    st.session_state["restore_notice"] = "Pasta local alterada; ambas permanecem preservadas."
                    st.rerun()
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
    if os.environ.get("OSLER_DATA_DIR"):
        st.caption("Há uma pasta definida por OSLER_DATA_DIR. Trocas feitas aqui valem nesta sessão; ao reiniciar, essa configuração explícita tem prioridade.")
