"""Pooler Supabase com papel restrito às cinco funções do workspace."""
from contextlib import contextmanager
import re
from pathlib import Path

from .cloud_store import CloudError


def _failure(exc):
    if exc.sqlstate == '40001':
        return CloudError('A nuvem está sendo usada por outra sessão ou a versão mudou. Atualize a página; não repita o registro.')
    if exc.sqlstate in ('28P01','42501'):
        return CloudError('O armazenamento recusou a credencial. Confira os secrets e o papel osler_cloud.')
    if exc.sqlstate == '42883':
        return CloudError('Armazenamento não configurado. Aplique cloud/schema.sql no projeto Supabase.')
    return CloudError('Sem resposta do armazenamento. Confira se o projeto Supabase está ativo e tente atualizar sem repetir o registro.')


class SupabasePostgres:
    def __init__(self, host, user, password):
        if not re.fullmatch(r'aws-\d+-[a-z0-9-]+\.pooler\.supabase\.com',str(host)):
            raise CloudError('Host de armazenamento inválido. Use o pooler do seu projeto Supabase.')
        if not re.fullmatch(r'osler_cloud\.[a-z0-9]{20}',str(user)) or not password:
            raise CloudError('Configure o usuário restrito e a senha do armazenamento nos secrets.')
        self.host, self.user, self.password = host,user,password
        self._db = None

    @contextmanager
    def session(self):
        """Reutiliza TLS durante uma execução; cada RPC confirma sua transação.

        O lock do CloudWorkspace serializa o uso por sessões Streamlit.
        autocommit evita manter a linha do lease bloqueada durante a renderização.
        """
        if self._db is not None:
            yield
            return
        import psycopg
        try:
            with psycopg.connect(host=self.host,port=5432,user=self.user,password=self.password,
                                 dbname='postgres',sslmode='verify-full',
                                 sslrootcert=str(Path(__file__).resolve().parents[1]/'cloud/supabase-ca.crt'),
                                 connect_timeout=15,autocommit=True,options='-c statement_timeout=45000') as db:
                self._db = db
                try:
                    yield
                finally:
                    self._db = None
        except psycopg.Error as exc:
            raise _failure(exc) from None

    def _call(self, function, *args):
        import psycopg
        try:
            with self.session():
                # O nome vem somente das funções fixas abaixo, nunca de entrada.
                placeholders=','.join(['%s']*len(args))
                return self._db.execute(f'SELECT public.osler_{function}({placeholders})',args).fetchone()[0]
        except psycopg.Error as exc:
            raise _failure(exc) from None

    def acquire(self,owner,known):
        return self._call('acquire',owner)

    def release(self,owner):
        self._call('release',owner)

    def put(self,owner,digest,payload):
        self._call('put',owner,digest,payload)

    def get(self,digest):
        return self._call('get',digest)

    def get_many(self,digests):
        """Uma consulta na abertura evita uma ida de rede para cada original."""
        import psycopg
        try:
            with self.session():
                rows=self._db.execute('select digest, public.osler_get(digest) from unnest(%s::text[]) as item(digest)',
                                      (list(digests),)).fetchall()
                return dict(rows)
        except psycopg.Error as exc:
            raise _failure(exc) from None

    def commit(self,owner,revision,manifest):
        from psycopg.types.json import Jsonb
        return self._call('commit',owner,revision,Jsonb(manifest))
