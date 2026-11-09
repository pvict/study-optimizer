import copy
from contextlib import closing
import sqlite3
from pathlib import Path

import pytest

from osler.cloud_store import CloudError, CloudWorkspace, pack, unpack


class MemoryRemote:
    def __init__(self):
        self.revision = 0
        self.manifest = {}
        self.objects = {}
        self.owner = None
        self.fail = False
        self.ambiguous = False

    def acquire(self, owner, known):
        if self.owner not in (None, owner):
            raise CloudError('Outro servidor está usando os dados.')
        self.owner = owner
        return {'revision': self.revision, 'manifest': copy.deepcopy(self.manifest)}

    def release(self, owner):
        if self.owner == owner:
            self.owner = None

    def put(self, owner, digest, payload):
        if self.fail:
            raise CloudError('Sem conexão.')
        self.objects.setdefault(digest, payload)

    def get(self, digest):
        return self.objects[digest]

    def commit(self, owner, revision, manifest):
        if self.fail or revision != self.revision or owner != self.owner:
            raise CloudError('Gravação recusada.')
        self.manifest = copy.deepcopy(manifest)
        self.revision += 1
        if self.ambiguous:
            self.ambiguous = False
            raise CloudError('Resposta perdida depois de salvar.')
        return self.revision


def seed(root):
    root.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(root/'osler.sqlite3')) as db, db:
        db.execute('create table if not exists activity (value integer)')
        db.execute('insert into activity values (12)')
    (root/'originals').mkdir(exist_ok=True)
    (root/'exports').mkdir(exist_ok=True)
    (root/'exports'/'planner.html').write_text('histórico ç', encoding='utf-8')


def total(root):
    with closing(sqlite3.connect(root/'osler.sqlite3')) as db, db:
        return db.execute('select sum(value) from activity').fetchone()[0]


def test_restart_restores_database_and_original_exports(tmp_path):
    remote = MemoryRemote()
    first = CloudWorkspace(tmp_path/'first', remote)
    with first.cycle():
        assert not first.initialized
        seed(first.root)
    second = CloudWorkspace(tmp_path/'second', remote)
    with second.cycle():
        assert second.initialized
        assert total(second.root) == 12
        assert (second.root/'exports'/'planner.html').read_text(encoding='utf-8') == 'histórico ç'
    assert remote.revision == 1  # a read does not create another snapshot


def test_competing_server_cannot_overwrite(tmp_path):
    remote = MemoryRemote()
    first = CloudWorkspace(tmp_path/'a', remote)
    second = CloudWorkspace(tmp_path/'b', remote)
    with first.cycle():
        seed(first.root)
        with pytest.raises(CloudError):
            with second.cycle():
                pytest.fail('second server acquired occupied lease')
    with second.cycle():
        with closing(sqlite3.connect(second.root/'osler.sqlite3')) as db, db:
            db.execute('insert into activity values (7)')
    with first.cycle():
        assert total(first.root) == 19


def test_failed_save_preserves_pending_data_and_retries_without_repeating(tmp_path):
    remote = MemoryRemote()
    first = CloudWorkspace(tmp_path/'a', remote)
    with first.cycle():
        seed(first.root)
    remote.fail = True
    with pytest.raises(CloudError):
        with first.cycle():
            with closing(sqlite3.connect(first.root/'osler.sqlite3')) as db, db:
                db.execute('insert into activity values (5)')
    assert first.pending and total(first.root) == 17
    remote.fail = False
    with first.cycle():
        assert not first.pending
        assert total(first.root) == 17
    assert remote.revision == 2


def test_ambiguous_commit_recognizes_saved_snapshot(tmp_path):
    remote = MemoryRemote()
    first = CloudWorkspace(tmp_path/'a', remote)
    remote.ambiguous = True
    with pytest.raises(CloudError):
        with first.cycle():
            seed(first.root)
    assert first.pending
    with first.cycle():
        assert not first.pending
        assert total(first.root) == 12
    assert remote.revision == 1


def test_remote_change_never_discards_unsaved_local_data(tmp_path):
    remote = MemoryRemote()
    first = CloudWorkspace(tmp_path/'a', remote)
    with first.cycle():
        seed(first.root)
    remote.fail = True
    with pytest.raises(CloudError):
        with first.cycle():
            (first.root/'exports'/'new.txt').write_text('pending')
    remote.fail = False
    other = CloudWorkspace(tmp_path/'b', remote)
    with other.cycle():
        (other.root/'exports'/'other.txt').write_text('newer')
    with pytest.raises(CloudError, match='conflito'):
        with first.cycle():
            pass
    assert (first.root/'exports'/'new.txt').read_text() == 'pending'
    assert first.pending


def test_corrupt_object_or_unsafe_path_never_installs_database(tmp_path):
    remote = MemoryRemote()
    remote.revision = 1
    digest, payload = pack(b'not a database')
    remote.objects[digest] = payload
    remote.manifest = {'../escape':digest, 'osler.sqlite3':digest}
    with pytest.raises(CloudError):
        with CloudWorkspace(tmp_path/'a',remote).cycle():
            pass
    assert not (tmp_path/'escape').exists()
    assert not (tmp_path/'a'/'osler.sqlite3').exists()
    with pytest.raises(CloudError):
        unpack(digest, payload[:-3]+'abc')


def test_rerun_base_exception_still_persists_and_releases(tmp_path):
    class Rerun(BaseException):
        pass
    remote = MemoryRemote()
    first = CloudWorkspace(tmp_path/'a',remote)
    with pytest.raises(Rerun):
        with first.cycle():
            seed(first.root)
            raise Rerun()
    assert remote.revision == 1 and remote.owner is None


def test_nested_cycle_only_acquires_once(tmp_path):
    remote = MemoryRemote()
    first = CloudWorkspace(tmp_path/'a',remote)
    with first.cycle():
        with first.cycle():
            seed(first.root)
    assert remote.revision == 1


def test_snapshot_failure_is_pending_and_cannot_be_overwritten(monkeypatch,tmp_path):
    import osler.cloud_store as module
    remote=MemoryRemote()
    first=CloudWorkspace(tmp_path/'a',remote)
    with first.cycle():seed(first.root)
    snapshot=module._snapshot
    def unavailable(root):
        raise OSError('disk unavailable')
    with pytest.raises(CloudError):
        with first.cycle():
            with closing(sqlite3.connect(first.root/'osler.sqlite3')) as db,db:
                db.execute('insert into activity values (5)')
            monkeypatch.setattr(module,'_snapshot',unavailable)
    assert first.pending
    monkeypatch.setattr(module,'_snapshot',snapshot)
    second=CloudWorkspace(tmp_path/'b',remote)
    with second.cycle():
        (second.root/'exports'/'new.txt').write_text('remote')
    with pytest.raises(CloudError,match='conflito'):
        with first.cycle():pass
    assert total(first.root)==17


def test_cold_start_downloads_objects_in_one_batch_when_supported(tmp_path):
    remote=MemoryRemote()
    with CloudWorkspace(tmp_path/'a',remote).cycle() as ws:seed(ws.root)
    calls=[]
    def batch(digests):
        calls.append(set(digests))
        return {d:remote.objects[d] for d in digests}
    def slow(digest):pytest.fail('individual request on batch-capable backend')
    remote.get_many=batch
    remote.get=slow
    with CloudWorkspace(tmp_path/'b',remote).cycle() as ws:
        assert total(ws.root)==12
    assert len(calls)==1
