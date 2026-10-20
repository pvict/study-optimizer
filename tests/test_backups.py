from io import BytesIO
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest

from osler.backups import create_backup, inspect_backup, restore_backup
from osler.service import import_bytes
from osler.storage import Repository
from osler.workspace import active_data_dir, activate_data_dir


def backup_data(tmp_path, sample_pdf):
    repo = Repository(tmp_path/"data")
    report = import_bytes(repo, sample_pdf(), "sample.pdf").report
    backup = create_backup(repo)
    return repo, report, backup


def test_backup_restore_preserves_originals_and_active_data(tmp_path, sample_pdf):
    repo, report, backup = backup_data(tmp_path, sample_pdf)
    before = repo.db_path.read_bytes()
    details = inspect_backup(backup.read_bytes())
    assert details["reports"] == 1
    assert details["schema_version"] == 2
    restored = restore_backup(backup.read_bytes(), tmp_path/"data-restaurada")
    other = Repository(restored)
    assert other.original_path(report.file_sha256).read_bytes() == sample_pdf() or other.original_path(report.file_sha256).read_bytes() == repo.original_path(report.file_sha256).read_bytes()
    assert other.get_report(report.file_sha256).to_dict() == repo.get_report(report.file_sha256).to_dict()
    assert repo.db_path.read_bytes() == before
    with sqlite3.connect(other.db_path) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with pytest.raises(ValueError):
        restore_backup(backup.read_bytes(), restored)


def repack(data, transform=None, extra=None):
    output = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as original, zipfile.ZipFile(output, "w") as changed:
        for item in original.infolist():
            payload = original.read(item.filename)
            changed.writestr(item, transform(item.filename, payload) if transform else payload)
        if extra:
            changed.writestr(*extra)
    return output.getvalue()


def test_corruption_or_wrong_hash_is_refused_before_restore(tmp_path, sample_pdf):
    repo, report, backup = backup_data(tmp_path, sample_pdf)
    corrupted = repack(backup.read_bytes(), lambda name, payload: b"corrompido" if name.endswith(".pdf") else payload)
    with pytest.raises(ValueError):
        inspect_backup(corrupted)
    with pytest.raises(ValueError):
        restore_backup(corrupted, tmp_path/"nao-criar")
    assert not (tmp_path/"nao-criar").exists()
    with pytest.raises(ValueError):
        inspect_backup(b"nao e um zip")


@pytest.mark.parametrize("entry", ["../fora.txt", "/absoluto.txt", "C:/fora.txt", "exports/../../fora.txt", "exports\\fora.txt", "osler.sqlite3"])
def test_unsafe_paths_and_duplicate_entries_are_refused(tmp_path, sample_pdf, entry):
    repo, report, backup = backup_data(tmp_path, sample_pdf)
    malicious = repack(backup.read_bytes(), extra=(entry, b"malicioso"))
    with pytest.raises(ValueError):
        restore_backup(malicious, tmp_path/"nova")
    assert not (tmp_path/"fora.txt").exists()
    assert not (tmp_path/"nova").exists()


def test_symlink_entry_is_refused(tmp_path, sample_pdf):
    repo, report, backup = backup_data(tmp_path, sample_pdf)
    link = zipfile.ZipInfo("exports/link")
    link.create_system = 3
    link.external_attr = 0o120777 << 16
    malicious = repack(backup.read_bytes(), extra=(link, b"../../fora"))
    with pytest.raises(ValueError):
        inspect_backup(malicious)


def test_active_folder_switch_is_local_and_previous_data_remains(tmp_path, sample_pdf, monkeypatch):
    monkeypatch.delenv("OSLER_DATA_DIR", raising=False)
    repo, report, backup = backup_data(tmp_path, sample_pdf)
    restored = restore_backup(backup.read_bytes(), tmp_path/"data-restaurada")
    activate_data_dir(tmp_path, restored)
    assert active_data_dir(tmp_path) == restored.resolve()
    assert repo.original_path(report.file_sha256).is_file()
    activate_data_dir(tmp_path, repo.root)
    assert active_data_dir(tmp_path) == repo.root
    with pytest.raises(ValueError):
        activate_data_dir(tmp_path, tmp_path.parent)


def test_valid_hashes_do_not_make_incompatible_sqlite_schema_usable(tmp_path):
    import hashlib
    from contextlib import closing
    path = tmp_path/"bad.sqlite3"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE reports(file_sha256 TEXT)")
        db.execute("PRAGMA user_version=5")
        db.commit()
    payload = path.read_bytes()
    manifest = {"format_version": 1, "files": {"osler.sqlite3": {"sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}}}
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("osler.sqlite3", payload)
        archive.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(ValueError, match="[Ee]strutura|schema"):
        inspect_backup(output.getvalue())
    with pytest.raises(ValueError):
        restore_backup(output.getvalue(), tmp_path/"nao-ativar")
    assert not (tmp_path/"nao-ativar").exists()


def test_transient_windows_folder_lock_does_not_lose_restoration(tmp_path, sample_pdf, monkeypatch):
    import osler.backups
    repo, report, backup = backup_data(tmp_path, sample_pdf)
    original = osler.backups.os.rename
    attempts = []
    def locked_once(source, destination):
        if Path(source).is_dir():
            attempts.append(source)
            if len(attempts) == 1:
                error = PermissionError(13, "Pasta temporariamente ocupada")
                error.winerror = 5
                raise error
        return original(source, destination)
    monkeypatch.setattr(osler.backups.os, "rename", locked_once)
    target = restore_backup(backup.read_bytes(), tmp_path/"restaurada")
    assert len(attempts) == 2
    assert (target/"osler.sqlite3").is_file()
