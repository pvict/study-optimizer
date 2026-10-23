"""Seleção, validação e checklist para ações realizadas exclusivamente pelo usuário."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .assessment_service import AssessmentService
from .classification import ClassifierConfig
from .files import write_immutable
from .matching_service import load_matching
from .models import stable_topic_id
from .planner_storage import PlannerStore, TRANSITIONS


def today_local():
    """Dia de estudo: das 04h até antes das 04h seguintes, em Brasília.

    Datas declaradas/importadas e timestamps de auditoria não são deslocados.
    """
    return (datetime.now(ZoneInfo("America/Sao_Paulo"))-timedelta(hours=4)).date()


def valid_date(value, *, past=False):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or (past and parsed > today_local()):
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError("Data inválida ou futura para uma ação já realizada.") from None
    return parsed


@dataclass
class ChecklistExport:
    folder: Path
    csv_path: Path
    json_path: Path
    markdown_path: Path


class PlannerService:
    def __init__(self, repository):
        self.repository = repository
        self.assessments = AssessmentService(repository)
        self.store = PlannerStore(repository)

    def create_batch(self, matching, row_ids, name, note, as_of, config=None):
        valid_date(as_of)
        if not isinstance(name, str) or not name.strip() or not isinstance(note, str) or not note.strip():
            raise ValueError("Informe nome e finalidade do lote.")
        if not row_ids or len(row_ids) != len(set(row_ids)):
            raise ValueError("Selecione temas distintos para o lote.")
        token = self.store.evidence_token()
        fresh = load_matching(self.repository, matching.qbank_report_id, matching.flashcards_report_id)
        cfg = (config or ClassifierConfig()).validate()
        result = self.assessments.analyze(fresh, as_of, cfg)
        by_id = {i["row_id"]: i for i in result["items"]}
        sources = {r.row_id: r for r in fresh.rows}
        items = []
        for row_id in row_ids:
            item, row = by_id.get(row_id), sources.get(row_id)
            if not item or not item["eligible"] or item["classification"]["category"] not in {"A", "B"} or not row.flashcards or not row.flashcards.is_leaf:
                raise ValueError("Seleção contém tema sem candidato A/B atual e terminal de flashcards válido.")
            snapshot = {**item, "flashcards_path": row.flashcards.path, "flashcards_ordinal": row.flashcards_index,
                        "pdf_cards_total": row.flashcards.total, "source_dates": {"qbank": fresh.qbank_date, "flashcards": fresh.flashcards_date}}
            items.append({"row_id": row_id, "topic_key": stable_topic_id(row.flashcards.path), "snapshot": snapshot})
        return self.store.create({"name": name.strip(), "note": note.strip(), "qbank_report_id": fresh.qbank_report_id,
                                  "flashcards_report_id": fresh.flashcards_report_id, "analysis_date": as_of, "config": cfg.to_dict()}, items, token)

    def get_batch(self, batch_id):
        return self.store.get_batch(batch_id)

    def list_batches(self):
        return self.store.list_batches()

    def events(self):
        return self.store.events()

    def _current_evidence(self, item, action_date):
        token = self.store.evidence_token()
        batch = self.get_batch(item["batch_id"])
        matching = load_matching(self.repository, batch["qbank_report_id"], batch["flashcards_report_id"])
        analyzed = self.assessments.analyze(matching, action_date, ClassifierConfig(**batch["config"]))
        current = next((i for i in analyzed["items"] if i["row_id"] == item["row_id"]), None)
        if not current or not current["eligible"] or current["classification"]["category"] not in {"A", "B"} or current["observation_id"] != item["snapshot"]["observation_id"]:
            raise ValueError("Evidência mudou ou deixou de sustentar o candidato. Cancele este item e crie nova avaliação.")
        return token

    def transition(self, item_id, status, note, expected_revision, action_date, *, confirmed=False, reevaluation_date=None):
        valid_date(action_date, past=True)
        item = self.store.item(item_id)
        if status not in TRANSITIONS[item["status"]]:
            raise ValueError("Transição de estado inválida. Siga validação e aprovação antes da aplicação manual.")
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Informe a justificativa da decisão.")
        if reevaluation_date is not None:
            valid_date(reevaluation_date)
            if reevaluation_date < action_date:
                raise ValueError("Data de reavaliação não pode preceder a ação.")
        if status in {"aprovado_usuario", "aplicado_manualmente", "reativado"} and confirmed is not True:
            raise ValueError("Esta etapa exige confirmação explícita do usuário.")
        token = self._current_evidence(item, action_date) if status == "aprovado_usuario" else None
        self.store.change(item_id, expected_revision, note.strip(), reevaluation_date or item["reevaluation_date"], status=status, action_date=action_date, evidence_token=token)

    def update_item(self, item_id, note, reevaluation_date, expected_revision):
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Informe uma observação sobre o item.")
        if reevaluation_date is not None:
            valid_date(reevaluation_date)
        self.store.change(item_id, expected_revision, note.strip(), reevaluation_date)

    def due_items(self, as_of):
        valid_date(as_of)
        return [i for i in self.store.all_items() if i["status"] in {"aprovado_usuario", "aplicado_manualmente"}
                and i["reevaluation_date"] is not None and i["reevaluation_date"] <= as_of]

    def export(self, batch_id):
        from .planner_exports import checklist_csv, checklist_markdown
        batch = self.get_batch(batch_id)
        payload = json.dumps(batch, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        folder = self.repository.exports/"checklists"/digest
        folder.mkdir(parents=True, exist_ok=True)
        csv_path, json_path, md_path = folder/"checklist.csv", folder/"checklist.json", folder/"checklist.md"
        write_immutable(json_path, payload)
        write_immutable(csv_path, checklist_csv(batch))
        write_immutable(md_path, checklist_markdown(batch).encode("utf-8"))
        return ChecklistExport(folder, csv_path, json_path, md_path)
