from collections import Counter
import csv
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
from io import StringIO
import json
from pathlib import Path

from .assessment_storage import AssessmentStore
from .classification import ClassifierConfig, classify
from .exports import _safe_cell
from .files import write_immutable
from .matching_service import load_matching
from .observations import Observation, OBSERVATION_FIELDS, parse_observation
from .study_signals import poor_study_paths
from .models import normalize_path


def eligible(row):
    return row.row_type in {"terminal_comparavel", "terminal_uma_fonte"} and not row.association.startswith("bloqueada")


def _hierarchy(row):
    return " → ".join((row.qbank or row.flashcards).path)


def result_records(result):
    output = []
    for item in result["items"]:
        c, o = item["classification"], item["observation"] or {}
        row = {"registro_id": item["row_id"], "hierarquia": item["hierarchy"], "elegivel": item["eligible"],
               "categoria": c["category"], "prioridade": c["priority"], "justificativa": " ".join(c["reasons"]),
               "dados_ausentes": "; ".join(c["missing"]), "observacao_id": item["observation_id"],
               "data_observacao": o.get("data_observacao"), "origem": o.get("origem_da_informacao"),
               "confiabilidade": o.get("nivel_de_confiabilidade"), "acerto_pdf": item["pdf_accuracy"],
               "revisado_pdf": item["review_coverage"], "respondidas_pdf": item["pdf_answered"],
               "estudados_pdf": item["pdf_studied"], "cartoes_avaliaveis": c["cards_involved"],
               "acerto_pdf_operador": item["pdf_accuracy_operator"], "acerto_pdf_texto": item["pdf_accuracy_text"],
               "revisado_pdf_operador": item["review_coverage_operator"], "revisado_pdf_texto": item["review_coverage_text"],
               "wilson_inferior_aproximado": c["wilson_low"], "wilson_superior_aproximado": c["wilson_high"],
               "cobertura_pesos": c["weight_coverage"], "suspensao_aplicada": False}
        for field in OBSERVATION_FIELDS:
            if field not in row:
                row[field] = o.get(field)
        row["evidencias"] = " ".join(c["evidence"])
        row["limites"] = " ".join(c["warnings"])
        output.append(row)
    return output


def classification_csv(result):
    rows = result_records(result)
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else [], delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows({k: v if k.endswith("_operador") else _safe_cell(v) for k, v in r.items()} for r in rows)
    return output.getvalue().encode("utf-8-sig")


@dataclass(frozen=True)
class AssessmentExport:
    folder: Path
    csv_path: Path
    json_path: Path


class AssessmentService:
    def __init__(self, repository):
        self.repository = repository
        self.store = AssessmentStore(repository)

    def _validate_context(self, matching, changes):
        fresh = load_matching(self.repository, matching.qbank_report_id, matching.flashcards_report_id)
        rows = {r.row_id: r for r in fresh.rows}
        if len({c[0] for c in changes}) != len(changes):
            raise ValueError("Contexto repetido no lote; nenhum indicador foi salvo.")
        for row_id, observation, revision in changes:
            if row_id not in rows or not eligible(rows[row_id]):
                raise ValueError("Contexto inexistente, agregado, alterado ou bloqueado. Atualize o cruzamento.")
            observation.validate()
        return fresh

    def save_observation(self, matching, row_id, observation, expected_revision):
        changes = [(row_id, observation, expected_revision)]
        fresh = self._validate_context(matching, changes)
        return self.store.save_batch(fresh, changes)[0]

    def revoke(self, observation_id, expected_revision):
        self.store.revoke(observation_id, expected_revision)

    def analyze(self, matching, as_of, config=None):
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError("Data de análise inválida.")
        cfg = (config or ClassifierConfig()).validate()
        selected = self.store.selected(as_of)
        weak_paths={tuple(normalize_path(p)) for p in poor_study_paths(self.repository,as_of)}
        items, counts = [], Counter()
        for row in matching.rows:
            selected_row = selected.get(row.row_id)
            observation = selected_row["observation"] if selected_row else None
            accuracy = row.qbank.acerto_pdf.value if row.qbank else None
            review = row.flashcards.percentual_revisado.value if row.flashcards else None
            accuracy_text = row.qbank.acerto_pdf.raw if row.qbank else None
            review_text = row.flashcards.percentual_revisado.raw if row.flashcards else None
            classification = classify(observation, cfg, eligible=eligible(row), pdf_accuracy=accuracy_text if accuracy is not None else None,
                                      review_coverage=review_text if review is not None else None)
            if eligible(row) and any(tuple(normalize_path(source.path))[:len(weak)]==weak for source in [row.qbank,row.flashcards] if source for weak in weak_paths):
                classification.category,classification.priority='C','manter_revisao'
                classification.reasons.insert(0,'Bloco recente de questões com dificuldade registrada: reforçar e reavaliar antes de reduzir.')
            if observation and (date.fromisoformat(as_of)-date.fromisoformat(observation.data_observacao)).days > cfg.max_age_days:
                classification.category, classification.priority = "D", "sem_dados"
                classification.reasons.insert(0, f"Observação antiga: ultrapassa a validade configurada de {cfg.max_age_days} dias; reavaliar.")
            if observation and any(d is None or observation.data_observacao != d for d in [matching.qbank_date, matching.flashcards_date]):
                classification.warnings.append("Observação manual e PDFs podem ter cortes diferentes; não unir denominadores.")
            if eligible(row):
                counts[classification.category] += 1
            items.append({"row_id": row.row_id, "hierarchy": _hierarchy(row), "row_type": row.row_type,
                          "eligible": eligible(row), "observation_id": selected_row["id"] if selected_row else None,
                          "observation": observation.to_dict() if observation else None, "classification": asdict(classification),
                          "pdf_accuracy": accuracy, "review_coverage": review,
                          "pdf_accuracy_text": accuracy_text, "pdf_accuracy_operator": row.qbank.acerto_pdf.operator if row.qbank else None,
                          "review_coverage_text": review_text, "review_coverage_operator": row.flashcards.percentual_revisado.operator if row.flashcards else None,
                          "pdf_answered": row.qbank.studied if row.qbank else None,
                          "pdf_studied": row.flashcards.studied if row.flashcards else None})
        return {"algorithm_version": "1.0", "qbank_report_id": matching.qbank_report_id, "flashcards_report_id": matching.flashcards_report_id,
                "qbank_date": matching.qbank_date, "flashcards_date": matching.flashcards_date, "analysis_date": as_of,
                "config": cfg.to_dict(), "stats": {**{c: counts[c] for c in "ABCD"}, "excluidos": sum(not i["eligible"] for i in items)}, "items": items}

    def csv_template(self, matching, as_of):
        output = StringIO(newline="")
        columns = ["registro_id", "hierarquia", "revisao_atual", *OBSERVATION_FIELDS]
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for row in matching.rows:
            if eligible(row):
                writer.writerow({"registro_id": row.row_id, "hierarquia": _safe_cell(_hierarchy(row)),
                                 "revisao_atual": self.store.revision(row.row_id), "data_observacao": as_of})
        return output.getvalue().encode("utf-8-sig")

    def import_csv(self, matching, data):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV precisa estar em UTF-8 com separador ponto e vírgula.") from exc
        reader = csv.DictReader(StringIO(text), delimiter=";")
        allowed = {"registro_id", "hierarquia", "revisao_atual", *OBSERVATION_FIELDS}
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or set(reader.fieldnames)-allowed or not {"registro_id", "revisao_atual"}.issubset(reader.fieldnames):
            raise ValueError("Cabeçalhos CSV inválidos. Baixe o modelo da tela Classificação.")
        by_id = {r.row_id: r for r in matching.rows}
        changes = []
        metadata = {"data_observacao", "origem_da_informacao", "nivel_de_confiabilidade"}
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Linha {line}: número de colunas inválido.")
            values = {name: row[name] for name in OBSERVATION_FIELDS if name in row}
            if not any(str(v).strip() for name, v in values.items() if name not in metadata):
                continue
            try:
                row_id = row["registro_id"]
                if row_id not in by_id:
                    raise ValueError("registro de outro contexto")
                if "hierarquia" in row and row["hierarquia"] != _safe_cell(_hierarchy(by_id[row_id])):
                    raise ValueError("hierarquia não corresponde ao registro")
                revision = int(row["revisao_atual"])
                changes.append((row_id, parse_observation(values), revision))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Linha {line}: {exc}") from exc
        if not changes:
            raise ValueError("CSV sem indicadores preenchidos; nenhuma alteração realizada.")
        fresh = self._validate_context(matching, changes)
        self.store.save_batch(fresh, changes)
        return len(changes)

    def export(self, result):
        payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        folder = self.repository.exports/"classificacoes"/digest
        folder.mkdir(parents=True, exist_ok=True)
        csv_path, json_path = folder/"classificacao.csv", folder/"classificacao.json"
        write_immutable(csv_path, classification_csv(result))
        write_immutable(json_path, payload)
        return AssessmentExport(folder, csv_path, json_path)
