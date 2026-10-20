"""Importador do layout textual Acervo & acurácia Osler, versão observada em 2026.

Sem chamadas de rede. Geometria de colunas e recuos preserva níveis e nomes longos.
Layouts desconhecidos geram erros explícitos em vez de tabelas vazias silenciosas.
"""
from datetime import datetime
import hashlib
import json
import re

import pymupdf

from .models import Finding, Report, TopicRecord, normalize_path, parse_percentage, stable_topic_id
from .validation import validate_report


class ImportFailure(ValueError):
    """Arquivo inválido, protegido, sem texto ou com layout não suportado."""


def _integer(raw: str) -> int:
    raw = raw.strip()
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:\.\d{3})+)", raw):
        raise ValueError("Contagem não reconhecida")
    return int(raw.replace(".", ""))


def _lines(page) -> list[list[dict]]:
    spans = [s for b in page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]
             if b["type"] == 0 for line in b["lines"] for s in line["spans"] if s["text"].strip()]
    groups = []
    for span in sorted(spans, key=lambda s: (s["origin"][1], s["bbox"][0])):
        if groups and abs(groups[-1][0]["origin"][1] - span["origin"][1]) <= 1.5:
            groups[-1].append(span)
        else:
            groups.append([span])
    return [sorted(group, key=lambda s: s["bbox"][0]) for group in groups]


def _text(spans: list[dict]) -> str:
    return " ".join(s["text"].strip() for s in spans).strip()


def _identify(doc, filename: str, data: bytes) -> Report:
    cover = doc[0].get_text()
    header = doc[1].get_text() if len(doc) > 1 else ""
    if not (cover + header).strip():
        raise ImportFailure("PDF sem camada textual. Exporte novamente como PDF textual; OCR não está disponível neste marco.")
    first_lines = "\n".join(cover.splitlines()[:5])
    names = [name for name in ["qbank", "flashcards"] if name in first_lines.casefold()]
    if len(names) != 1 or "acervo" not in (cover + header).casefold():
        raise ImportFailure("Conteúdo não identificado como relatório Osler de Qbank ou Flashcards Acervo & acurácia.")
    kind = names[0]
    combined = cover + "\n" + header
    normal = normalize_path([combined])[0]
    scope = "iniciados" if "iniciados" in normal else "todos" if re.search(r"\btodos\b|no acervo", normal) else "desconhecido"
    dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", combined)
    report_date = None
    findings = []
    if dates:
        try:
            report_date = datetime.strptime(dates[0], "%d/%m/%Y").date().isoformat()
        except ValueError:
            findings.append(Finding("data_invalida", "erro", "Data do relatório inválida no documento."))
        if len(set(dates)) > 1:
            findings.append(Finding("datas_conflitantes", "erro", "Capa e cabeçalho apresentam datas diferentes."))
    summary = {}
    match = re.search(r"([\d.]+)\s+de\s+([\d.]+)\s+(?:questões respondidas|cards feitos)", cover, re.I)
    if match:
        summary.update(estudados=_integer(match[1]), total=_integer(match[2]))
    match = re.search(r"([\d.]+)\s+(?:temas|decks)\s+(?:no acervo|iniciados)", cover, re.I)
    if match:
        summary["nos_declarados"] = _integer(match[1])
    match = re.search(r"([\d.]+)\s+acertos em\s+([\d.]+)\s+respondidas", cover)
    if match:
        summary.update(acertos_pdf=_integer(match[1]), denominador_acerto_pdf=_integer(match[2]))
    match = re.search(r"([\d.]+)\s+de\s+([\d.]+)\s+feitos já vistos 2\+ vezes", cover)
    if match:
        summary.update(cartoes_vistos_duas_vezes=_integer(match[1]), denominador_revisao=_integer(match[2]))
    metadata = {k: doc.metadata.get(k) for k in ["title", "author", "creator", "producer", "creationDate", "modDate"]}
    return Report(filename, hashlib.sha256(data).hexdigest(), kind, scope, report_date, len(doc), metadata, summary, findings=findings)


def _page_records(page, number: int, report: Report, stack: list[str]) -> list[str]:
    scale = page.rect.width / 595.28
    lines = _lines(page)
    header = next((line for line in lines if _text(line).startswith("Tema ")
                   and "% visto" in _text(line)), None)
    if header is None:
        report.findings.append(Finding("pagina_sem_tabela", "erro", "Cabeçalho da tabela não reconhecido; página não extraída.", number))
        return []  # Não propagar hierarquia através de uma página não lida.
    header_y = header[0]["origin"][1]
    if not (580 <= page.rect.width <= 610 and 820 <= page.rect.height <= 860):
        report.findings.append(Finding("layout_incompativel", "erro", "Dimensões diferentes do layout suportado; página não extraída.", number))
        return []
    expected = "Respondidas" if report.kind == "qbank" else "Feitos"
    if expected not in _text(header) or ("% acerto" if report.kind == "qbank" else "% revisado") not in _text(header):
        report.findings.append(Finding("colunas_incompativeis", "erro", "Colunas não correspondem ao tipo do relatório.", number))
        return []
    report.table_pages += 1
    pending = None

    def finish():
        nonlocal pending, stack
        if pending is None:
            return
        name, x, y, cells = pending
        pending = None
        level = round((x / scale - 48) / 10.5)
        if level < 0 or abs(x / scale - (48 + level * 10.5)) > 1.5:
            report.findings.append(Finding("recuo_incompativel", "erro", f"Recuo do tema não reconhecido: {name}.", number))
            stack = []
            return
        if level > len(stack):
            report.findings.append(Finding("hierarquia_incompleta", "erro", f"{name}: nível {level} sem todos os ancestrais. Caminho parcial preservado.", number))
        path = stack[:level] + [name]
        raw = " | ".join([name, *cells])
        try:
            row = TopicRecord(stable_topic_id(path), path, level, _integer(cells[0]), _integer(cells[1]),
                              parse_percentage(cells[2]), number, raw, x, y)
            metric = parse_percentage(cells[3])
            if report.kind == "qbank":
                row.acerto_pdf = metric
            else:
                row.percentual_revisado = metric
                row.nivel_de_confiabilidade = "extração documental; revisão representa cobertura"
            if level > len(stack):
                row.nivel_de_confiabilidade = "hierarquia incompleta; exige revisão manual"
            report.records.append(row)
        except ValueError:
            report.findings.append(Finding("linha_invalida", "erro", f"Contagens ou percentuais não reconhecidos: {raw}", number))
        stack = path

    for line in lines:
        y = line[0]["origin"][1]
        if y <= header_y + 10 or y >= page.rect.height - 40:
            continue
        text = _text(line)
        if "(continuação)" in text:
            finish()
            prefix = [p.strip() for p in re.split(r"›|→|>", text.replace("(continuação)", "").strip()) if p.strip()]
            if normalize_path(stack[:len(prefix)]) != normalize_path(prefix):
                stack = prefix
            continue
        names = [s for s in line if s["bbox"][0] < 310 * scale]
        numeric = [s for s in line if s["bbox"][0] >= 310 * scale]
        if numeric:
            finish()
            cells = [_text([s for s in numeric if a * scale <= s["bbox"][0] < b * scale]).replace(" ", "")
                     for a, b in [(310, 363), (363, 440), (440, 505), (505, 570)]]
            if not names or not all(cells):
                report.findings.append(Finding("linha_incompleta", "erro", "Linha da tabela sem nome ou sem as quatro colunas numéricas.", number))
                stack = []
                continue
            pending = (_text(names), names[0]["bbox"][0], y, cells)
        elif names:
            if pending and 0 < y - pending[2] <= 14 * scale and abs(names[0]["bbox"][0] - pending[1]) <= 1.5:
                pending = (pending[0] + " " + _text(names), pending[1], pending[2], pending[3])
            else:
                report.findings.append(Finding("texto_nao_associado", "erro", f"Texto da tabela sem associação segura: {text}", number))
    finish()
    return stack


def _content_digest(report: Report) -> str:
    # Exclui datas de criação, nomes dos arquivos, páginas e linhas originais.
    rows = [{"path": normalize_path(r.path), "level": r.level, "total": r.total, "studied": r.studied,
             "coverage": [r.percentual_visto.value, r.percentual_visto.operator],
             "accuracy": [r.acerto_pdf.value, r.acerto_pdf.operator],
             "review": [r.percentual_revisado.value, r.percentual_revisado.operator]} for r in report.records]
    payload = {"kind": report.kind, "scope": report.scope, "date": report.report_date,
               "summary": report.summary, "records": sorted(rows, key=lambda r: json.dumps(r, sort_keys=True))}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def extract_pdf(data: bytes, filename: str) -> Report:
    if not data.startswith(b"%PDF-"):
        raise ImportFailure("Arquivo não é um PDF válido.")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise ImportFailure("PDF corrompido ou ilegível.") from exc
    with doc:
        if doc.needs_pass:
            raise ImportFailure("PDF protegido por senha. Exporte uma cópia sem proteção; não são coletadas senhas.")
        if not len(doc):
            raise ImportFailure("PDF sem páginas.")
        report = _identify(doc, filename, data)
        stack = []
        for index in range(1, len(doc)):
            stack = _page_records(doc[index], index + 1, report, stack)
        if not report.records:
            raise ImportFailure("Nenhuma tabela extraída. Layout não suportado; original não alterado.")
    for i, row in enumerate(report.records[:-1]):
        nxt = report.records[i + 1]
        row.is_leaf = not (nxt.level > row.level and normalize_path(nxt.path[:len(row.path)]) == normalize_path(row.path))
    report.findings.extend(validate_report(report))
    report.content_sha256 = _content_digest(report)
    return report
