"""Configura o projeto do próprio usuário; credenciais ficam fora do repositório.

Uso: python scripts/configure_cloud.py --project-ref REF --host HOST
     --private-dir C:/Users/Paulo/.osler-private
O arquivo privado supabase-credentials.toml contém [supabase] database_password.
Não imprime segredos nem exporta dados pessoais.
"""
import argparse
from pathlib import Path
import secrets
import sys
import tomllib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from osler.cloud_access import password_hash
from osler.cloud_postgres import SupabasePostgres


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-ref',required=True)
    parser.add_argument('--host',required=True)
    parser.add_argument('--private-dir',required=True,type=Path)
    args=parser.parse_args()
    private=args.private_dir.resolve()
    repo=Path(__file__).resolve().parents[1]
    if private.is_relative_to(repo) or not private.is_dir():
        raise SystemExit('Use uma pasta privada existente fora do repositório.')
    import psycopg
    from psycopg import sql
    credentials=tomllib.loads((private/'supabase-credentials.toml').read_text())
    config_file=private/'cloud-secrets.toml'
    if config_file.exists():
        settings=tomllib.loads(config_file.read_text())['cloud']
        if settings['host'] != args.host or settings['user'] != 'osler_cloud.'+args.project_ref:
            raise SystemExit('A pasta já contém configuração de outro projeto; nada foi alterado.')
        app_password=settings['password']
    else:
        app_password=secrets.token_urlsafe(36)
    # Valida destino antes de transmitir a credencial administrativa.
    SupabasePostgres(args.host,'osler_cloud.'+args.project_ref,app_password)
    with psycopg.connect(host=args.host,port=5432,dbname='postgres',user='postgres.'+args.project_ref,
                         password=credentials['supabase']['database_password'],connect_timeout=20,
                         sslmode='verify-full',sslrootcert=str(repo/'cloud/supabase-ca.crt')) as db:
        db.execute((repo/'cloud/schema.sql').read_text(encoding='utf-8'))
        exists=db.execute("select 1 from pg_roles where rolname='osler_cloud'").fetchone()
        if not exists:
            db.execute(sql.SQL('create role osler_cloud login password {}').format(sql.Literal(app_password)))
        elif not config_file.exists():
            raise SystemExit('O papel já existe, mas a configuração privada não está disponível. Nenhuma senha foi alterada.')
        db.execute('grant usage on schema public to osler_cloud')
        for signature in ('acquire(uuid)','release(uuid)','put(uuid,text,text)','get(text)','commit(uuid,bigint,jsonb)'):
            db.execute('grant execute on function public.osler_'+signature+' to osler_cloud')
    if not config_file.exists():
        login=secrets.token_urlsafe(18)
        import json
        settings={'auth_mode':'password','host':args.host,'user':'osler_cloud.'+args.project_ref,
                  'password':app_password,'password_hash':password_hash(login)}
        config_file.write_text('[cloud]\n'+'\n'.join(k+' = '+json.dumps(v) for k,v in settings.items())+'\n',encoding='utf-8')
        (private/'app-access.txt').write_text('Senha de acesso ao aplicativo online:\n'+login+'\n',encoding='utf-8')
    print('Esquema privado e papel restrito configurados. Secrets e senha do app salvos somente na pasta privada.')


if __name__=='__main__':
    main()
