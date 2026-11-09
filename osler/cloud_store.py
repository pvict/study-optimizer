"""Persistência privada de SQLite e arquivos, sem alterar os modelos de estudo.

Um workspace gerenciado por processo; o lease remoto também protege contra
dois processos. Nunca aceitar uma base vazia como substituta de dados remotos.
"""
import base64
from contextlib import closing, contextmanager, nullcontext
from contextvars import ContextVar
import hashlib
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import uuid
import zlib

from .backups import _safe_name, MAX_TOTAL_BYTES, MAX_ENTRIES

MAX_OBJECT = 64 * 1024 * 1024
_active = ContextVar('osler_cloud_workspace', default=None)


class CloudError(RuntimeError):
    """Erro operacional seguro para mostrar ao usuário, sem corpo HTTP/segredos."""


def pack(data):
    if len(data) > MAX_OBJECT:
        raise CloudError('Um arquivo excede 64 MB. Preserve o backup e reduza a importação.')
    return hashlib.sha256(data).hexdigest(), base64.b64encode(zlib.compress(data, 6)).decode('ascii')


def unpack(digest, payload):
    try:
        if not re.fullmatch('[0-9a-f]{64}', digest) or len(payload) > MAX_OBJECT*2:
            raise ValueError()
        decoder = zlib.decompressobj()
        data = decoder.decompress(base64.b64decode(payload, validate=True), MAX_OBJECT+1)
        if len(data) > MAX_OBJECT or not decoder.eof or decoder.unused_data:
            raise ValueError()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError()
        return data
    except (ValueError, TypeError, zlib.error):
        raise CloudError('Arquivo na nuvem falhou na verificação de integridade. Nenhum dado foi substituído.') from None


def _validate_manifest(manifest):
    try:
        if not isinstance(manifest, dict) or not 1 <= len(manifest) <= MAX_ENTRIES:
            raise ValueError()
        if 'osler.sqlite3' not in manifest:
            raise ValueError()
        folded = set()
        for name, digest in manifest.items():
            _safe_name(name)
            if name == 'manifest.json' or name.casefold() in folded or not re.fullmatch('[0-9a-f]{64}', digest):
                raise ValueError()
            folded.add(name.casefold())
    except (ValueError, TypeError, AttributeError):
        raise CloudError('Manifesto de dados inválido. Os dados existentes foram preservados.') from None


def _snapshot(root):
    """Usa SQLite backup, nunca copia um banco aberto com WAL pendente."""
    if not (root/'osler.sqlite3').is_file():
        return {}, {}
    files = {}
    with tempfile.TemporaryDirectory(prefix='osler-snapshot-') as folder:
        target = Path(folder)/'osler.sqlite3'
        with closing(sqlite3.connect((root/'osler.sqlite3').as_uri()+'?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(target)) as destination:
                source.backup(destination)
        files['osler.sqlite3'] = target.read_bytes()
    for name in ('originals','exports'):
        folder = root/name
        for path in sorted(folder.rglob('*')) if folder.exists() else []:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise CloudError('Link ou arquivo fora da pasta de dados. Sincronização interrompida.')
            if path.is_file() and not path.name.startswith('.'):
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    if len(files) > MAX_ENTRIES or sum(map(len, files.values())) > MAX_TOTAL_BYTES:
        raise CloudError('Os dados excedem o limite de 512 MB. Baixe um backup antes de continuar.')
    manifest, objects = {}, {}
    for name, data in files.items():
        _safe_name(name)
        digest = hashlib.sha256(data).hexdigest()
        manifest[name] = digest
        objects[digest] = data
    return manifest, objects


class CloudWorkspace:
    def __init__(self, root, remote):
        self.root = Path(root).resolve()
        self.root.parent.mkdir(parents=True, exist_ok=True)
        self.remote, self.owner = remote, str(uuid.uuid4())
        self.revision, self.manifest = -1, {}
        self.pending = False
        self._lock = threading.RLock()
        self._leased = False

    @property
    def initialized(self):
        return (self.root/'osler.sqlite3').is_file()

    def _install(self, manifest):
        _validate_manifest(manifest)
        with tempfile.TemporaryDirectory(prefix='osler-cloud-install-', dir=self.root.parent) as folder:
            stage = Path(folder)/'incoming'
            stage.mkdir()
            size = 0
            batch = self.remote.get_many(set(manifest.values())) if hasattr(self.remote,'get_many') else None
            for name, digest in manifest.items():
                data = unpack(digest, batch.get(digest) if batch is not None else self.remote.get(digest))
                size += len(data)
                if size > MAX_TOTAL_BYTES:
                    raise CloudError('Dados remotos excedem o limite de tamanho.')
                target = stage/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            try:
                with closing(sqlite3.connect((stage/'osler.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
                    if db.execute('pragma integrity_check').fetchone()[0] != 'ok':
                        raise sqlite3.DatabaseError()
            except sqlite3.Error:
                raise CloudError('O banco remoto está inválido. Nenhum dado foi substituído.') from None
            if self.root.exists():
                self.root.rename(Path(folder)/'previous')
            stage.rename(self.root)

    def checkpoint(self):
        if not self._leased:
            raise CloudError('Esta alteração está fora da sessão protegida. Atualize a página.')
        self.pending = True
        try:
            manifest, objects = _snapshot(self.root)
        except (OSError, sqlite3.Error, ValueError):
            raise CloudError('Não foi possível preparar a gravação na nuvem. Os dados locais foram preservados; tente novamente sem repetir o registro.') from None
        if manifest == self.manifest:
            self.pending = False
            return
        if not manifest:
            raise CloudError('O banco ativo desapareceu. Nenhum dado remoto foi removido.')
        # Renova o lease antes de enviar os objetos; o CAS ainda verifica revisão.
        state = self.remote.acquire(self.owner, self.revision)
        if state['revision'] != self.revision:
            if state['manifest'] == manifest:  # commit anterior cujo ACK se perdeu
                self.revision, self.manifest = state['revision'], manifest
                self.pending = False
                return
            raise CloudError('Há conflito com uma versão mais nova na nuvem. Baixe a cópia de recuperação; nenhum dado local foi descartado.')
        known = set(self.manifest.values())
        for digest, data in objects.items():
            if digest not in known:
                _, payload = pack(data)
                self.remote.put(self.owner, digest, payload)
        revision = self.remote.commit(self.owner, self.revision, manifest)
        self.revision, self.manifest, self.pending = revision, manifest, False

    @contextmanager
    def cycle(self):
        if _active.get() is self:
            yield self
            return
        with self._lock, self.remote.session() if hasattr(self.remote,'session') else nullcontext():
            token = None
            try:
                state = self.remote.acquire(self.owner, self.revision)
                self._leased = True
                if self.pending:
                    self.checkpoint()
                elif state['revision'] != self.revision:
                    if state['manifest']:
                        self._install(state['manifest'])
                    elif self.initialized:
                        raise CloudError('A nuvem está vazia, mas há dados locais. A inicialização precisa ser explícita.')
                    self.revision, self.manifest = state['revision'], state['manifest']
                token = _active.set(self)
                try:
                    yield self
                finally:
                    if self.initialized:
                        self.checkpoint()
            finally:
                if token is not None:
                    _active.reset(token)
                if self._leased:
                    try:
                        self.remote.release(self.owner)
                    except CloudError:
                        pass  # lease expira; um commit confirmado continua confirmado
                    self._leased = False


def persist_before_success():
    current = _active.get()
    if current is not None:
        try:
            current.checkpoint()
        except CloudError:
            # A escrita SQLite já terminou. Deixe o chamador concluir receipt,
            # limpeza do formulário e chave de edição; interromper aqui poderia
            # transformar a próxima tentativa numa duplicata. A barreira final
            # insiste na gravação e apresenta recuperação em caso de falha.
            return False
    return True


def has_pending_save():
    current = _active.get()
    return current is not None and current.pending
