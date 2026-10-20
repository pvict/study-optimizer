"""Checklists locais; campos para registrar decisões não são preenchidos por inferência."""
import csv
from io import StringIO

from .exports import _safe_cell


def checklist_records(batch):
    output = []
    for item in batch["items"]:
        s, o = item["snapshot"], item["snapshot"]["observation"] or {}
        c = s["classification"]
        output.append({"lote": batch["name"], "item_id": item["id"], "hierarquia": " → ".join(s["flashcards_path"]),
                       "estado": item["status"], "categoria": c["category"], "prioridade": c["priority"],
                       "questoes_distintas": o.get("questoes_distintas"), "respostas_totais": o.get("respostas_totais"),
                       "acerto_primeira_tentativa": o.get("acerto_primeira_tentativa"), "acerto_ultima_tentativa": o.get("acerto_ultima_tentativa"),
                       "acerto_recente": o.get("acerto_recente"), "cartoes_avaliaveis": c["cards_involved"],
                       "cartoes_estudados_manual": o.get("cartoes_estudados"), "cartoes_estudados_pdf": s["pdf_studied"],
                       "cartoes_ativos": o.get("cartoes_ativos"), "cartoes_pendentes": o.get("cartoes_pendentes"), "cartoes_futuros": o.get("cartoes_futuros"),
                       "justificativa": " | ".join(c["reasons"]), "dados_ausentes": ", ".join(c["missing"]),
                       "origem": o.get("origem_da_informacao"), "data_observacao": o.get("data_observacao"),
                       "confiabilidade": o.get("nivel_de_confiabilidade"), "data_aprovacao": item["approved_date"],
                       "data_aplicacao": item["applied_date"], "data_reativacao": item["reactivated_date"],
                       "confirmacao_manual": "Informada pelo usuário" if item["applied_date"] else "",
                       "data_reavaliacao": item["reevaluation_date"], "observacoes": item["note"],
                       "qbank_fonte": batch["qbank_report_id"], "flashcards_fonte": batch["flashcards_report_id"]})
    return output


def checklist_csv(batch):
    records = checklist_records(batch)
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(records[0]), delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows({k: _safe_cell(v) if isinstance(v, str) else v for k, v in r.items()} for r in records)
    return output.getvalue().encode("utf-8-sig")


def checklist_markdown(batch):
    def text(value):
        return str(value).replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;") if value is not None else "não informado"
    lines = [f"# {text(batch['name'])}", "", "Checklist de validação e execução MANUAL. Um candidato não é aprovação nem aplicação.",
             "Cartões envolvidos não equivalem a revisões eliminadas. Preserve os conceitos frágeis.", "", f"Análise: {batch['analysis_date']}", ""]
    for r in checklist_records(batch):
        lines += [f"## Item {r['item_id']} — {text(r['hierarquia'])}", "", f"Estado: {r['estado']} · categoria {r['categoria']} · faixa {r['prioridade']}",
                  f"Questões distintas: {text(r['questoes_distintas'])}; inicial {text(r['acerto_primeira_tentativa'])}%; última {text(r['acerto_ultima_tentativa'])}%.",
                  f"Cartões avaliáveis: {text(r['cartoes_avaliaveis'])}; pendentes {text(r['cartoes_pendentes'])}; futuros {text(r['cartoes_futuros'])}.",
                  f"Justificativa: {text(r['justificativa'])}", f"Dados ausentes: {text(r['dados_ausentes'])}",
                  f"Origem: {text(r['origem'])}; data {text(r['data_observacao'])}; confiabilidade {text(r['confiabilidade'])}.",
                  "", "- [ ] Conferi os conceitos frágeis, erros críticos/recorrentes e o caminho exato.",
                  "- [ ] Aprovo a ação após validação pessoal.", "- [ ] CONFIRMAÇÃO MANUAL: realizei a ação na interface oficial da Osler.",
                  f"Data da aplicação: {r['data_aplicacao'] or '________________'}", f"Reavaliação: {r['data_reavaliacao'] or '________________'}",
                  f"Observações: {text(r['observacoes'])}", "", f"Fonte Qbank: {r['qbank_fonte']}", f"Fonte Flashcards: {r['flashcards_fonte']}", ""]
    return "\n".join(lines)
