"""Importação inicial explícita; recusa sobrescrever histórico online existente."""
import argparse
from pathlib import Path
import sys
import tempfile
import tomllib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from osler.backups import inspect_backup,restore_backup
from osler.cloud_postgres import SupabasePostgres
from osler.cloud_store import CloudWorkspace


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--backup',type=Path,required=True)
    parser.add_argument('--secrets-file',type=Path,required=True)
    args=parser.parse_args()
    payload=args.backup.read_bytes()
    details=inspect_backup(payload)
    config=tomllib.loads(args.secrets_file.read_text())['cloud']
    remote=SupabasePostgres(config['host'],config['user'],config['password'])
    with tempfile.TemporaryDirectory(prefix='osler-cloud-seed-') as temp:
        workspace=CloudWorkspace(Path(temp)/'data',remote)
        with workspace.cycle():
            if workspace.initialized or workspace.revision!=0:
                raise SystemExit('O histórico online já existe. Nada foi importado; use a restauração com prévia no app.')
            restore_backup(payload,workspace.root)
        print('Importação confirmada na nuvem. Revisão:',workspace.revision,'Arquivos:',details['file_count'])


if __name__=='__main__':main()
