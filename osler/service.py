from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .exports import records_csv, report_json
from .extraction import extract_pdf
from .models import Report
from .storage import Repository
from .files import write_immutable


@dataclass
class ImportResult:
    report: Report
    state: str
    duplicate_of: str | None
    csv_path: Path
    json_path: Path


def _write_once(path: Path, data: bytes):
    try:
        write_immutable(path, data)
    except FileExistsError:
        raise FileExistsError("Exportação existente divergente. Nenhum arquivo sobrescrito; use outra pasta de dados para uma nova versão de extração.") from None


def import_bytes(repository: Repository, data: bytes, filename: str) -> ImportResult:
    safe_name = PureWindowsPath(filename).name
    report = extract_pdf(data, safe_name)
    state, duplicate_of = repository.save_report(report, data)
    if state == "ja_importado":
        # Reimportar não substitui resultados históricos por nova interpretação.
        report = repository.get_report(report.file_sha256)
    folder = repository.exports / report.file_sha256
    folder.mkdir(parents=True, exist_ok=True)
    csv_path, json_path = folder / "registros.csv", folder / "relatorio.json"
    _write_once(csv_path, records_csv(report))
    _write_once(json_path, report_json(report))
    return ImportResult(report, state, duplicate_of, csv_path, json_path)
