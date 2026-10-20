"""Backup consistente, verificado por hash e restauração em uma pasta nova."""
from datetime import datetime, timezone
from contextlib import closing
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import tempfile
import time
import zipfile

from .files import write_immutable
from .database_check import check_database

MAX_TOTAL_BYTES = 512*1024*1024
MAX_ENTRIES = 10000


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe_name(name):
    parts = PurePosixPath(name).parts
    if not parts or name.startswith("/") or "\\" in name or any(p in {".", ".."} or ":" in p or p.rstrip(" .") != p for p in parts) or "/".join(parts) != name:
        raise ValueError("Backup contém caminho inseguro.")
    if name not in {"manifest.json", "osler.sqlite3"} and not (len(parts) >= 2 and parts[0] in {"originals", "exports"}):
        raise ValueError("Backup contém arquivo fora das pastas de dados permitidas.")
    if any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", p) for p in parts):
        raise ValueError("Backup contém nome reservado no Windows.")


def create_backup(repo):
    files = {}
    with tempfile.TemporaryDirectory(prefix="osler-backup-") as temp:
        snapshot = Path(temp)/"osler.sqlite3"
        with repo._connection() as source, closing(sqlite3.connect(snapshot)) as destination:
            source.backup(destination)
        files["osler.sqlite3"] = snapshot.read_bytes()
    for folder in (repo.originals, repo.exports):
        if folder.is_symlink():
            raise ValueError("Pasta de dados com link simbólico não suportada no backup.")
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError("Link simbólico encontrado; backup recusado.")
            if path.is_file() and not path.name.startswith("."):
                resolved = path.resolve()
                if not resolved.is_relative_to(repo.root):
                    raise ValueError("Arquivo fora da pasta local de dados.")
                name = path.relative_to(repo.root).as_posix()
                _safe_name(name)
                files[name] = path.read_bytes()
    if len(files)+1 > MAX_ENTRIES or sum(map(len, files.values())) > MAX_TOTAL_BYTES:
        raise ValueError("Backup excede o limite local de tamanho ou arquivos.")
    manifest = {"format_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "files": {name: {"sha256": _sha(data), "size": len(data)} for name, data in files.items()}}
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    data = output.getvalue()
    inspect_backup(data)
    target = repo.root/"backups"/f"osler_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{_sha(data)[:16]}.zip"
    target.parent.mkdir(exist_ok=True)
    write_immutable(target, data)
    return target


def _validate(data):
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_ENTRIES or sum(e.file_size for e in entries) > MAX_TOTAL_BYTES:
                raise ValueError("Backup excede os limites de segurança de tamanho ou quantidade.")
            names = set()
            for entry in entries:
                _safe_name(entry.filename)
                if entry.filename.casefold() in names or entry.is_dir() or entry.flag_bits & 1 or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Backup tem entrada duplicada, link, diretório ou arquivo cifrado não suportado.")
                names.add(entry.filename.casefold())
            manifest = json.loads(archive.read("manifest.json"))
            if not isinstance(manifest, dict) or manifest.get("format_version") != 1 or not isinstance(manifest.get("files"), dict):
                raise ValueError("Manifesto de backup inválido.")
            if set(manifest["files"]) != {e.filename for e in entries if e.filename != "manifest.json"}:
                raise ValueError("Manifesto e arquivos do backup divergem.")
            files = {}
            for name, expected in manifest["files"].items():
                payload = archive.read(name)
                if not isinstance(expected, dict) or expected.get("sha256") != _sha(payload) or expected.get("size") != len(payload):
                    raise ValueError("Backup corrompido: hash ou tamanho divergente.")
                files[name] = payload
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError, RuntimeError, OSError) as exc:
        raise ValueError("Arquivo de backup inválido, incompleto ou corrompido.") from exc
    if "osler.sqlite3" not in files:
        raise ValueError("Backup sem banco SQLite.")
    try:
        with tempfile.TemporaryDirectory(prefix="osler-verify-") as temp:
            database = Path(temp)/"osler.sqlite3"
            database.write_bytes(files["osler.sqlite3"])
            version, reports = check_database(database)
            for digest in reports:
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or _sha(files.get(f"originals/{digest}.pdf", b"")) != digest:
                    raise ValueError("Original referido pelo banco ausente ou divergente no backup.")
    except sqlite3.Error as exc:
        raise ValueError("Banco SQLite do backup inválido.") from exc
    return {"created_at": manifest.get("created_at"), "schema_version": version, "reports": len(reports),
            "file_count": len(files), "total_bytes": sum(map(len, files.values()))}, files


def inspect_backup(data):
    return _validate(data)[0]


def restore_backup(data, destination):
    details, files = _validate(data)
    target = Path(destination).resolve()
    if target.exists():
        raise ValueError("Destino já existe. Restaure em uma pasta nova; dados anteriores serão preservados.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".osler-restore-", dir=target.parent) as temp:
        staging = Path(temp)/"data"
        staging.mkdir()
        for name, payload in files.items():
            path = staging/Path(*PurePosixPath(name).parts)
            if not path.resolve().is_relative_to(staging.resolve()):
                raise ValueError("Caminho escaparia da pasta de restauração.")
            path.parent.mkdir(parents=True, exist_ok=True)
            write_immutable(path, payload)
        if target.exists():
            raise ValueError("Destino criado por outro processo. Nenhum dado foi substituído.")
        for attempt in range(6):
            try:
                os.rename(staging, target)
                break
            except PermissionError as exc:
                if os.name != "nt" or getattr(exc, "winerror", None) not in {5, 32} or attempt == 5:
                    raise
                time.sleep(0.1*2**attempt)
    return target
