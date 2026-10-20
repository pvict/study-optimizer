import csv
from io import StringIO
import json

from .exports import _safe_cell
from .matching import MatchingResult


def unified_records(result: MatchingResult) -> list[dict]:
    output = []
    for row in result.rows:
        q, f = row.qbank, row.flashcards
        path = (q or f).path
        item = {"registro_id": row.row_id, "tema_id_qbank": q.topic_id if q else None, "tema_id_flashcards": f.topic_id if f else None,
                "area": path[0], "nome": path[-1], "associacao": row.association, "tipo_registro": row.row_type,
                "qualidade_dados": row.quality, "nota_associacao": row.note,
                "hierarquia_qbank": " → ".join(q.path) if q else None, "hierarquia_flashcards": " → ".join(f.path) if f else None,
                "qbank_ordinal": row.qbank_index, "flashcards_ordinal": row.flashcards_index,
                "qbank_relatorio": result.qbank_report_id if q else None, "flashcards_relatorio": result.flashcards_report_id if f else None,
                "data_qbank": result.qbank_date if q else None, "data_flashcards": result.flashcards_date if f else None,
                "escopo_qbank": result.qbank_scope if q else None, "escopo_flashcards": result.flashcards_scope if f else None,
                "pagina_qbank": q.page if q else None, "pagina_flashcards": f.page if f else None,
                "qbank_terminal": q.is_leaf if q else None, "flashcards_terminal": f.is_leaf if f else None,
                "questoes_disponiveis": q.total if q else None, "questoes_respondidas": q.studied if q else None,
                "cartoes_total": f.total if f else None, "cartoes_estudados": f.studied if f else None}
        for name, source, attr in [("percentual_visto_qbank", q, "percentual_visto"), ("acerto_pdf", q, "acerto_pdf"),
                                   ("percentual_visto_flashcards", f, "percentual_visto"), ("percentual_revisado", f, "percentual_revisado")]:
            pct = getattr(source, attr) if source else None
            item[name] = pct.value if pct else None
            item[f"{name}_operador"] = pct.operator if pct else None
            item[f"{name}_texto"] = pct.raw if pct else None
        for name, source in [("acerto_primeira_tentativa", q), ("acerto_ultima_tentativa", q), ("questoes_distintas", q),
                             ("respostas_totais", q), ("cartoes_ativos", f), ("cartoes_pendentes", f), ("cartoes_futuros", f)]:
            item[name] = getattr(source, name) if source else None
        item["origem_qbank"] = q.origem_da_informacao if q else None
        item["origem_flashcards"] = f.origem_da_informacao if f else None
        item["confiabilidade_qbank"] = q.nivel_de_confiabilidade if q else None
        item["confiabilidade_flashcards"] = f.nivel_de_confiabilidade if f else None
        absent = [name for name in ["acerto_primeira_tentativa", "acerto_ultima_tentativa", "questoes_distintas", "respostas_totais",
                                    "acerto_pdf", "percentual_revisado", "cartoes_ativos", "cartoes_pendentes", "cartoes_futuros"] if item[name] is None]
        if not q:
            absent.insert(0, "fonte_qbank")
        if not f:
            absent.insert(0, "fonte_flashcards")
        item["dados_ausentes"] = "; ".join(absent)
        output.append(item)
    return output


def matching_csv(result: MatchingResult) -> bytes:
    rows = unified_records(result)
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [], delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows({k: v if k.endswith("_operador") else _safe_cell(v) for k, v in r.items()} for r in rows)
    return stream.getvalue().encode("utf-8-sig")


def matching_json(result: MatchingResult) -> bytes:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
