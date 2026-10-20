"""Publicação completa e sem substituição de arquivos locais."""
import os
from pathlib import Path
import tempfile


def write_immutable(path: Path, data: bytes):
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("Arquivo existente divergente. Nenhum arquivo sobrescrito.")
        return
    fd, temporary = tempfile.mkstemp(prefix=".partial-", dir=path.parent)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        with temp_path.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if temp_path.read_bytes() != data:
            raise OSError("Gravação incompleta; destino definitivo não publicado.")
        try:
            if os.name == "nt":
                # No Windows, rename falha se o destino existe; não o substitui.
                os.rename(temp_path, path)
            else:
                # link publica exclusivamente no mesmo sistema de arquivos.
                os.link(temp_path, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise FileExistsError("Arquivo existente divergente. Nenhum arquivo sobrescrito.")
    finally:
        temp_path.unlink(missing_ok=True)
