import csv
from dataclasses import asdict
from io import StringIO
import json

from .models import Report


def record_dicts(report: Report) -> list[dict]:
    output = []
    for row in report.records:
        path = row.path
        item = {
            "relatorio_sha256": report.file_sha256, "tipo_relatorio": report.kind,
            "escopo": report.scope, "data_relatorio": report.report_date, "tema_id": row.topic_id,
            "area": path[0], "especialidade": path[1] if len(path) > 1 else None,
            "tema": path[2] if len(path) > 2 else None, "subtema": path[-1] if len(path) > 3 else None,
            "nome": row.name, "hierarquia": " → ".join(path), "hierarquia_json": json.dumps(path, ensure_ascii=False),
            "nivel": row.level, "registro_terminal": row.is_leaf,
            "questoes_disponiveis": row.total if report.kind == "qbank" else None,
            "questoes_respondidas": row.studied if report.kind == "qbank" else None,
            "cartoes_total": row.total if report.kind == "flashcards" else None,
            "cartoes_estudados": row.studied if report.kind == "flashcards" else None,
        }
        for label in ["percentual_visto", "acerto_pdf", "percentual_revisado"]:
            pct = getattr(row, label)
            item[label] = pct.value
            item[f"{label}_operador"] = pct.operator
            item[f"{label}_texto"] = pct.raw
        for label in ["acerto_primeira_tentativa", "acerto_ultima_tentativa", "questoes_distintas",
                      "respostas_totais", "cartoes_ativos", "cartoes_pendentes", "cartoes_futuros",
                      "origem_da_informacao", "nivel_de_confiabilidade"]:
            item[label] = getattr(row, label)
        item.update(pagina=row.page, linha_original=row.raw_row, x_origem=row.source_x, y_origem=row.source_y)
        output.append(item)
    return output


def _safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "@", "-")) and value.strip() != "-":
        return "'" + value
    return value


def records_csv(report: Report) -> bytes:
    rows = record_dicts(report)
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [], delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows({k: v if k.endswith("_operador") else _safe_cell(v) for k, v in row.items()} for row in rows)
    return stream.getvalue().encode("utf-8-sig")


def report_json(report: Report) -> bytes:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
