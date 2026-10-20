"""Preferência reversível da pasta local de dados; variáveis explícitas são respeitadas."""
import json
import os
from pathlib import Path
import tempfile
from .database_check import check_database


def active_data_dir(project_root):
    root = Path(project_root).resolve()
    if os.environ.get("OSLER_DATA_DIR"):
        return Path(os.environ["OSLER_DATA_DIR"]).resolve()
    settings = root/".osler-local.json"
    if settings.exists():
        try:
            target = Path(json.loads(settings.read_text(encoding="utf-8"))["active_data_dir"]).resolve()
            if target == root or not target.is_relative_to(root) or not (target/"osler.sqlite3").is_file():
                raise ValueError()
            return target
        except (ValueError, KeyError, TypeError, OSError):
            raise ValueError("Preferência da pasta de dados inválida. Preserve .osler-local.json e confira a pasta antes de abrir.") from None
    return root/"data"


def activate_data_dir(project_root, path):
    root, target = Path(project_root).resolve(), Path(path).resolve()
    if target == root or not target.is_relative_to(root) or not (target/"osler.sqlite3").is_file():
        raise ValueError("Escolha uma pasta de dados existente dentro do projeto.")
    check_database(target/"osler.sqlite3")
    payload = json.dumps({"active_data_dir": str(target)}, ensure_ascii=False, indent=2).encode("utf-8")
    handle, temporary = tempfile.mkstemp(prefix=".osler-settings-", dir=root)
    temp_path = Path(temporary)
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, root/".osler-local.json")
    finally:
        temp_path.unlink(missing_ok=True)
