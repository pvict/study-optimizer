"""Cria árvore de deploy com índice isolado, sem checkout/reset da árvore local."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


def git(*args, data=None, env=None):
    return subprocess.run(['git',*args],input=data,capture_output=True,check=True,env=env).stdout


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--branch',default='codex/cloud-mobile-20261109')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'codex/[a-zA-Z0-9/_-]+',args.branch) or '..' in args.branch:
        raise SystemExit('Use um nome de branch codex/ seguro.')
    root=Path(git('rev-parse','--show-toplevel').decode().strip())
    os.chdir(root)
    if git('branch','--show-current').decode().strip()==args.branch:
        raise SystemExit('Não gere o deploy sobre o checkout ativo.')
    with tempfile.TemporaryDirectory(prefix='osler-cloud-index-') as folder:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
        git('read-tree','HEAD',env=env)
        git('add','-A','--','.',env=env)
        config=(root/'.streamlit/config.toml').read_text(encoding='utf-8')
        if 'address = "127.0.0.1"' not in config:
            raise SystemExit('Configuração local mudou; confira o bind antes de gerar deploy.')
        config=config.replace('address = "127.0.0.1"','address = "0.0.0.0"')
        config=re.sub(r'^serverAddress\s*=.*\n','',config,flags=re.M)
        for name,content in {'.streamlit/config.toml':config.encode(),
                             'requirements.txt':(root/'cloud/requirements.txt').read_bytes()}.items():
            blob=git('hash-object','-w','--stdin',data=content).decode().strip()
            git('update-index','--add','--cacheinfo',f'100644,{blob},{name}',env=env)
        files=git('ls-files','-z',env=env).decode().split('\0')
        forbidden=[name for name in files if name and (
            name.startswith(('data/','evidencias/','.osler-runtime/'))
            or name.endswith(('.sqlite3','.zip','.pdf','.db'))
            or name.endswith('secrets.toml') or name.startswith('.env') and name!='.env.example')]
        if forbidden:
            raise SystemExit('Arquivos privados encontrados no deploy: '+', '.join(forbidden))
        tree=git('write-tree',env=env).decode().strip()
        if args.dry_run:
            print('Árvore de deploy validada:',tree)
            return
        ref='refs/heads/'+args.branch
        try:parent=git('rev-parse','--verify',ref).decode().strip()
        except subprocess.CalledProcessError:parent=git('rev-parse','HEAD').decode().strip()
        commit=git('commit-tree',tree,'-p',parent,data=b'feat: private cloud access with durable study history\n').decode().strip()
        git('update-ref',ref,commit)
        print('Branch preparado:',args.branch,commit)


if __name__=='__main__':main()
