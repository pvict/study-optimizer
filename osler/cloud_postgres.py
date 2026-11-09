"""Pooler Supabase com papel restrito às cinco funções do workspace."""
import json
import re
from pathlib import Path

from .cloud_store import CloudError


class SupabasePostgres:
    def __init__(self, host, user, password):
        if not re.fullmatch(r'aws-\d+-[a-z0-9-]+\.pooler\.supabase\.com',str(host)):
            raise CloudError('Host de armazenamento inválido. Use o pooler do seu projeto Supabase.')
        if not re.fullmatch(r'osler_cloud\.[a-z0-9]{20}',str(user)) or not password:
            raise CloudError('Configure o usuário restrito e a senha do armazenamento nos secrets.')
        self.host, self.user, self.password = host,user,password

    def _call(self, function, *args):
        import psycopg
        try:
            with psycopg.connect(host=self.host,port=5432,user=self.user,password=self.password,
                                 dbname='postgres',sslmode='verify-full',
                                 sslrootcert=str(Path(__file__).resolve().parents[1]/'cloud/supabase-ca.crt'),
                                 connect_timeout=15,options='-c statement_timeout=45000') as db:
                # O nome vem somente das funções fixas abaixo, nunca de entrada.
                placeholders=','.join(['%s']*len(args))
                return db.execute(f'SELECT public.osler_{function}({placeholders})',args).fetchone()[0]
        except psycopg.Error as exc:
            if exc.sqlstate in ('40001',):
                message='A nuvem está sendo usada por outra sessão ou a versão mudou. Atualize a página; não repita o registro.'
            elif exc.sqlstate in ('28P01','42501'):
                message='O armazenamento recusou a credencial. Confira os secrets e o papel osler_cloud.'
            elif exc.sqlstate == '42883':
                message='Armazenamento não configurado. Aplique cloud/schema.sql no projeto Supabase.'
            else:
                message='Sem resposta do armazenamento. Confira se o projeto Supabase está ativo e tente atualizar sem repetir o registro.'
            raise CloudError(message) from None

    def acquire(self,owner,known):
        return self._call('acquire',owner)

    def release(self,owner):
        self._call('release',owner)

    def put(self,owner,digest,payload):
        self._call('put',owner,digest,payload)

    def get(self,digest):
        return self._call('get',digest)

    def commit(self,owner,revision,manifest):
        from psycopg.types.json import Jsonb
        return self._call('commit',owner,revision,Jsonb(manifest))
