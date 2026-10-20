from dataclasses import dataclass
import hashlib
from pathlib import Path

from .files import write_immutable
from .matching import ManualMatch, MatchingResult, build_matching
from .matching_exports import matching_csv, matching_json
from .storage import Repository


@dataclass(frozen=True)
class MatchingExport:
    folder: Path
    csv_path: Path
    json_path: Path


def _decisions(repo, q_id, f_id):
    return [ManualMatch(row["qbank_ordinal"], row["flashcards_ordinal"], row["note"], row["id"])
            for row in repo.active_matches(q_id, f_id)]


def load_matching(repo: Repository, q_id: str, f_id: str, threshold: float = 0.86) -> MatchingResult:
    return build_matching(repo.get_report(q_id), repo.get_report(f_id), _decisions(repo, q_id, f_id), threshold)


def approve_match(repo: Repository, q_id: str, f_id: str, q_index: int, f_index: int, note: str) -> int:
    # Valida antes de persistir; restrições SQLite também protegem concorrência.
    build_matching(repo.get_report(q_id), repo.get_report(f_id),
                   [*_decisions(repo, q_id, f_id), ManualMatch(q_index, f_index, note)])
    return repo._add_match(q_id, f_id, q_index, f_index, note)


def revoke_match(repo: Repository, decision_id: int):
    repo._remove_match(decision_id)


def export_matching(repo: Repository, result: MatchingResult) -> MatchingExport:
    # O próprio JSON define a versão: novos parâmetros/decisões geram nova pasta.
    payload = matching_json(result)
    digest = hashlib.sha256(payload).hexdigest()
    folder = repo.exports / "cruzamentos" / digest
    folder.mkdir(parents=True, exist_ok=True)
    csv_path, json_path = folder / "tabela_unificada.csv", folder / "cruzamento.json"
    write_immutable(csv_path, matching_csv(result))
    write_immutable(json_path, payload)
    return MatchingExport(folder, csv_path, json_path)
