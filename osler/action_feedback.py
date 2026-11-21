"""Confirmação explícita na UI; serviços mantêm validação e concorrência."""
from datetime import date,datetime
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import time

import streamlit as st
import os
from .cloud_boundary import cloud_boundary

PREFIX='_action_'


def preserve_drafts(*keys, prefixes=()):
    """Desvincula valores de widgets antes da limpeza das abas recolhidas.

    Somente chaves de campos editáveis: botões e uploads não aceitam atribuição.
    Reatribuir antes de criar o widget conserva o rascunho na sessão.
    """
    for key in list(st.session_state):
        if key in keys or key.startswith(prefixes):
            value=st.session_state[key]
            # data_editor é somente leitura; seu DataFrame usa chave separada.
            if isinstance(value,dict) and {'edited_rows','added_rows','deleted_rows'}<=value.keys():continue
            st.session_state[key]=st.session_state[key]


def preserve_editor_draft(key,active):
    """Consolida as alterações do editor ao sair da aba, antes da limpeza nativa."""
    baseline=st.session_state.get(PREFIX+'editor_'+key)
    changes=st.session_state.get(key)
    if active or baseline is None or not changes:return
    frame=baseline.copy()
    for index,values in changes.get('edited_rows',{}).items():
        for column,value in values.items():frame.loc[int(index),column]=value
    frame=frame.drop(index=changes.get('deleted_rows',[]),errors='ignore')
    import pandas as pd
    additions=changes.get('added_rows',[])
    if additions:frame=pd.concat([frame,pd.DataFrame(additions)],ignore_index=True)
    st.session_state[PREFIX+'editor_'+key]=frame.reset_index(drop=True)
    st.session_state.pop(key,None)


def draft_editor(data,*,key,**options):
    baseline=st.session_state.setdefault(PREFIX+'editor_'+key,data)
    return st.data_editor(baseline,key=key,**options)


def append_editor_draft(key,row):
    preserve_editor_draft(key,False)
    baseline=st.session_state.get(PREFIX+'editor_'+key)
    if baseline is not None:
        import pandas as pd
        st.session_state[PREFIX+'editor_'+key]=pd.concat([baseline,pd.DataFrame([row])],ignore_index=True)


def bind_actions(repo):
    st.session_state[PREFIX+'database']=str(repo.db_path)
    flush_toast()


def _guard():
    path=st.session_state.get(PREFIX+'database')
    if not path:return None
    from .study_agenda import planning_token
    try:
        with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)) as db:
            try:token=planning_token(db)
            except sqlite3.OperationalError:
                # Ferramentas legadas podem abrir antes do módulo adaptativo.
                tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                token=repr([(t,db.execute('SELECT COUNT(*),MAX(rowid) FROM "'+t.replace('"','""')+'"').fetchone()) for t in sorted(tables)])
    except (sqlite3.Error,OSError):
        # A confirmação da recuperação deve continuar acessível com base inválida.
        try:
            info=Path(path).stat();token=('unavailable',info.st_size,info.st_mtime_ns)
        except OSError:token=('unavailable','missing')
    return path,token


def _fields():
    buttons=st.session_state.get(PREFIX+'buttons',[])
    return [k for k in st.session_state if not k.startswith((PREFIX,'FormSubmitter:')) and k not in buttons
            and k not in {'action_cancel','action_confirm'} and not k.endswith(('_notice','_toast','_error','_pause_until'))]


def _values(fields=None):
    import pandas as pd
    def freeze(value):
        if isinstance(value,(date,datetime)):return value.isoformat()
        if isinstance(value,(str,int,float,bool,type(None))):return value
        if isinstance(value,(bytes,bytearray)):return hashlib.sha256(value).hexdigest()
        if isinstance(value,io.BytesIO):return hashlib.sha256(value.getvalue()).hexdigest()
        if isinstance(value,pd.DataFrame):return value.to_json(date_format='iso')
        if isinstance(value,dict):return {str(k):freeze(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [freeze(v) for v in value]
        return type(value).__name__
    data={k:freeze(st.session_state[k]) if k in st.session_state else {'missing':True} for k in (_fields() if fields is None else fields)}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def flush_toast():
    if os.environ.get('OSLER_CLOUD') == '1':
        from .cloud_store import has_pending_save
        if has_pending_save():
            return
    message=st.session_state.pop(PREFIX+'toast',None)
    if message:st.toast(message,icon=':material/check_circle:')


def notify_success(result,message='Alterações salvas.'):
    """Avaliado somente após a chamada de gravação retornar, nunca no clique."""
    if os.environ.get('OSLER_CLOUD') == '1':
        from .cloud_store import persist_before_success
        persist_before_success()
    st.session_state[PREFIX+'toast']=message
    return result


def _cancel():
    st.session_state.pop(PREFIX+'pending',None)
    st.session_state.pop(PREFIX+'approved',None)


def _confirm_label(label):
    lower=label.lower()
    if lower.startswith('salvar resultado'):return 'Salvar resultado'
    if lower.startswith('criar backup'):return 'Criar backup'
    if lower.startswith('abrir pasta'):return 'Abrir pasta'
    if lower.startswith('encerrar tema'):return 'Encerrar tema'
    if lower.startswith('marcar como resolvido'):return 'Resolver'
    for verb in ('Salvar','Registrar','Importar','Aplicar','Desfazer','Desconsiderar','Restaurar','Retirar','Remover','Atualizar','Aprovar'):
        if lower.startswith(verb.lower()):return verb
    return 'Confirmar'


def _request(key,label,details,callback,args,kwargs):
    from .planner_service import today_local
    fields=_fields()
    st.session_state[PREFIX+'pending']={'key':key,'label':label,'details':details,
        'danger':any(w in label.lower() for w in ('desconsider','exclu','remov','retir','restaur','suspend','desfazer','desativ')),
        'guard':_guard(),'values':_values(fields),'fields':fields,'created':time.monotonic(),
        'day':today_local().isoformat(),'callback':callback,'args':args,'kwargs':kwargs}


@st.dialog('Confirmar ação',width='small',on_dismiss=_cancel)
@cloud_boundary
def _dialog():
    pending=st.session_state.get(PREFIX+'pending')
    if not pending:return
    st.subheader(pending['label'])
    st.write(pending['details'] or 'Confira os dados informados antes de continuar. Esta ação será registrada no aplicativo.')
    if pending['danger']:st.warning('Esta ação pode alterar seus dados ou o planejamento. Confira o que será afetado.')
    with st.container(key='confirmation_danger' if pending['danger'] else 'confirmation_regular'):
        cancel,confirm=st.columns(2)
        if cancel.button('Cancelar',key='action_cancel',width='stretch'):
            _cancel();st.rerun()
        if confirm.button(_confirm_label(pending['label']),key='action_confirm',type='primary',width='stretch'):
            from .planner_service import today_local
            if time.monotonic()-pending['created']>600 or pending['day']!=today_local().isoformat() or pending['guard']!=_guard() or pending['values']!=_values(pending['fields']):
                _cancel();st.error('Os dados foram atualizados ou o formulário mudou. Feche esta janela e revise a ação antes de confirmar novamente.');return
            st.session_state.pop(PREFIX+'pending',None)
            if pending['callback']:
                pending['callback'](*pending['args'],**pending['kwargs'])
            else:st.session_state[PREFIX+'approved']=pending
            st.rerun()


def _button(widget,label,*,action_key,details=None,**options):
    flush_toast()
    validate=options.pop('validate',None)
    callback=options.pop('on_click',None)
    args=options.pop('args',()) or ();kwargs=options.pop('kwargs',{}) or {}
    action_key=action_key+'::'+str(options.get('key',label))
    keys=st.session_state.setdefault(PREFIX+'buttons',[])
    if options.get('key') and options['key'] not in keys:keys.append(options['key'])
    # Não executar callback de gravação no clique que apenas abre a janela.
    # O callback nativo captura os argumentos da tela originalmente exibida,
    # preservando versões/tokens mesmo que os dados mudem antes do clique.
    if callback:
        options['on_click']=_request
        options['args']=(action_key,label,details,callback,args,kwargs)
    pressed=widget(label,**options)
    approved=st.session_state.get(PREFIX+'approved')
    if approved and approved['key']==action_key:
        st.session_state.pop(PREFIX+'approved',None)
        if not options.get('disabled',False) and approved['label']==label and approved['details']==details and approved['guard']==_guard() and approved['values']==_values(approved['fields']):return True
        st.error('A ação mudou. Revise os dados e confirme novamente.');return False
    if pressed and not callback:
        try:
            if validate and validate() is False:return False
        except ValueError as exc:
            st.error(str(exc));return False
        _request(action_key,label,details,None,args,kwargs)
    if st.session_state.get(PREFIX+'pending',{}).get('key')==action_key:_dialog()
    return False


def confirm_button(label,*,action_key,details=None,container=None,**options):
    return _button((container or st).button,label,action_key=action_key,details=details,**options)


def confirm_submit(label,*,action_key,details=None,container=None,**options):
    return _button((container or st).form_submit_button,label,action_key=action_key,details=details,**options)
