"""Leitura local de tabelas copiadas; nunca executa HTML ou consulta a Osler."""
from collections import defaultdict
import csv
from html.parser import HTMLParser
from io import StringIO
import math
import re

from .models import normalize_path


class _TableReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.ignore = 0
        self.spans = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignore += 1
        if self.ignore:
            return
        attrs = dict(attrs)
        if tag in {"table", "tbody", "tr"} and self.table is None:
            self.table = {"headers": [], "rows": []}
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {"text": [], "primary": [], "secondary": [], "labels": [], "header": tag == "th"}
            self.spans = []
        elif tag == "span" and self.cell is not None:
            classes = attrs.get("class", "")
            role = "primary" if "PrimaryText" in classes or "ThemeTitle-" in classes else "secondary" if "SecondaryText" in classes or "ThemePath-" in classes else None
            self.spans.append(role or (self.spans[-1] if self.spans else None))
        if self.cell is not None:
            label = attrs.get("aria-label") or attrs.get("title")
            if label and label not in self.cell["labels"]:
                self.cell["labels"].append(label)

    def handle_data(self, data):
        if not self.ignore and self.cell is not None and data.strip():
            self.cell["text"].append(data.strip())
            if self.spans and self.spans[-1]:
                self.cell[self.spans[-1]].append(data.strip())

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignore = max(0, self.ignore-1)
            return
        if self.ignore:
            return
        if tag == "span" and self.spans:
            self.spans.pop()
        elif tag in {"td", "th"} and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row and self.table is not None:
            if any(c["header"] for c in self.row):
                self.table["headers"] = [_cell_text(cell) for cell in self.row]
            else:
                self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.finish_table()

    def finish_table(self):
        if self.table is not None:
            self.tables.append(self.table)
            self.table = None


_THEME_HEADERS = {"tema", "assunto", "subtema", "hierarquia", "caminho"}
_QUESTION_SUFFIX = re.compile(r"(\d[\d.]*)\s*quest(?:ao|oes)\b")
_QUESTION_COUNT = re.compile(r"\d+|\d{1,3}(?:\.\d{3})+")
_NATIVE_BANDS = {
    "incidencia altissima": "alta", "incidencia alta": "alta",
    "incidencia media": "media", "incidencia baixa": "baixa",
    "incidencia baixissima": "baixa", "sem incidencia": "baixa",
}


def _cell_text(cell):
    return " ".join(cell["text"] or cell["labels"])


def _theme_text(cell):
    if not cell["primary"] or not cell["secondary"]:
        return _cell_text(cell)
    primary, secondary = " ".join(cell["primary"]), " ".join(cell["secondary"])
    path = [p.strip() for p in re.split(r">>|→|>|»|›", secondary) if p.strip()]
    if not path or normalize_path([path[-1]]) != normalize_path([primary]):
        path.append(primary)
    return " → ".join(path)


def _institution_column(headers, rows, theme, infer):
    declared = [i for i,h in enumerate(headers) if i != theme and "institu" in h
                and ("incid" in h or "quest" in h) and "%" not in h and "percent" not in h
                and not any("%" in row[i] for row in rows)]
    if len(declared) == 1:
        return declared[0]
    if infer:
        columns = [i for i in range(len(headers)) if i != theme and
                   all(_QUESTION_SUFFIX.fullmatch(normalize_path([row[i]])[0].strip()) for row in rows)]
        if columns:
            return columns[-1]
    return None


def parse_html_table(text):
    parser = _TableReader()
    parser.feed(text)
    parser.close()
    parser.finish_table()
    if not parser.tables:
        raise ValueError("Não encontrei linhas de temas no HTML. Copie a tabela ou as linhas do Planner.")
    table = max(parser.tables, key=lambda t: len(t["rows"]))
    if not table["rows"]:
        raise ValueError("A tabela não contém linhas de temas no arquivo recebido.")
    width = max(len(r) for r in table["rows"])
    if width < 2 or any(len(r) != width for r in table["rows"]):
        raise ValueError("A tabela tem colunas incompletas. Copie o elemento <table> inteiro.")
    complete_headers = len(table["headers"]) == width
    headers = table["headers"] if complete_headers else [f"Coluna {i+1}" for i in range(width)]
    declared = [i for i, label in enumerate(headers) if normalize_path([label])[0] in _THEME_HEADERS]
    marked = {i for row in table["rows"] for i,cell in enumerate(row) if cell["primary"] and cell["secondary"]}
    theme = declared[0] if len(declared) == 1 else next(iter(marked)) if len(marked) == 1 else 0
    if not complete_headers:
        headers[theme] = "Tema"
    rows = [[_theme_text(cell) if i == theme else _cell_text(cell) for i,cell in enumerate(row)]
            for row in table["rows"]]
    institution = _institution_column(normalize_path(headers), rows, theme, not complete_headers and len(marked) == 1)
    if institution is not None and not complete_headers:
        headers[institution] = "Incidência das instituições"
    return {"headers": headers, "rows": rows, "theme_column": theme, "institution_count_column": institution,
            "cell_labels": [[cell["labels"] for cell in row] for row in table["rows"]]}


def table_as_text(table, value_column):
    theme = table.get("theme_column", 0)
    if type(value_column) is not int or not 0 <= value_column < len(table["headers"]) or value_column == theme:
        raise ValueError("Escolha uma coluna numérica da tabela.")
    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Tema", "Valor"])
    writer.writerows([r[theme], r[value_column]] for r in table["rows"])
    return output.getvalue()


def suggested_value_column(table, unit):
    if unit == "questoes" and table["institution_count_column"] is not None:
        return table["institution_count_column"]
    headers = normalize_path(table["headers"])
    marker = "quest" if unit == "questoes" else "percent"
    candidates = [i for i,label in enumerate(headers) if i != table["theme_column"] and marker in label]
    institutional = [i for i,label in enumerate(headers) if i != table["theme_column"] and "institu" in label
                     and (marker in label or unit == "percentual" and ("incid" in label or "%" in label))]
    chosen = institutional or candidates
    return chosen[0] if len(chosen) == 1 else None


def apply_html_incidence_labels(rows, table, value_column):
    following = value_column + 1
    separate = following < len(table["headers"]) and "incid" in normalize_path([table["headers"][following]])[0]
    institutional = value_column == table["institution_count_column"]
    for row, values, labels in zip(rows, table["rows"], table["cell_labels"]):
        native = next((label for label in labels[value_column]
                       if normalize_path([label])[0] in _NATIVE_BANDS), None)
        if native is None and separate and not institutional and following != table["institution_count_column"]:
            native = values[following]
        if native:
            row["native_incidence"] = native
            if not institutional:
                row["band"] = _NATIVE_BANDS.get(normalize_path([native])[0], row["band"])


def parse_incidence(text, report, unit):
    if unit not in {"questoes", "percentual"}:
        raise ValueError("Escolha questões ou percentual para esta tabela.")
    lines = [line for line in text.lstrip("\ufeff").splitlines() if line.strip()]
    if not lines:
        raise ValueError("A tabela está vazia.")
    delimiter = "\t" if "\t" in lines[0] else ";" if ";" in lines[0] else ","
    raw = list(csv.reader(lines, delimiter=delimiter))
    if normalize_path([raw[0][0]])[0] in _THEME_HEADERS:
        raw = raw[1:]
    if not raw:
        raise ValueError("A tabela precisa conter temas e valores.")
    by_path, by_name = defaultdict(list), defaultdict(list)
    for row in report.records:
        by_path[tuple(normalize_path(row.path))].append(row)
        by_name[normalize_path([row.name])[0]].append(row)
    parsed, seen = [], set()
    for line, cells in enumerate(raw, 2):
        if len(cells) != 2 or not cells[0].strip():
            raise ValueError(f"Linha {line}: use duas colunas, tema e valor.")
        topic, value = [c.strip() for c in cells]
        number = value.rstrip("%").strip()
        if unit == "questoes":
            match = _QUESTION_SUFFIX.fullmatch(normalize_path([number])[0].strip())
            if match:
                number = match[1]
            if "%" in value or not _QUESTION_COUNT.fullmatch(number):
                raise ValueError(f"Linha {line}: quantidade de questões inválida.")
            number = int(number.replace(".", ""))
        else:
            if not re.fullmatch(r"\d+(?:[.,]\d+)?", number):
                raise ValueError(f"Linha {line}: percentual inválido.")
            number = float(number.replace(",", "."))
            if not math.isfinite(number) or not 0 <= number <= 100:
                raise ValueError(f"Linha {line}: percentual fora de 0 a 100.")
        path_parts = [p.strip() for p in re.split(r">>|→|>|»|›", topic) if p.strip()]
        key = tuple(normalize_path(path_parts))
        if key in seen:
            raise ValueError(f"Linha {line}: tema repetido na mesma tabela. Nenhuma linha foi importada.")
        seen.add(key)
        matches = by_path.get(key, []) if len(key) > 1 else by_name.get(key[0], [])
        match = matches[0] if len(matches) == 1 else None
        parsed.append({"topic": topic, "value": number, "path": match.path if match else None,
                       "reason": "associação exata" if match else "nome ambíguo" if matches else "não encontrado nos PDFs"})
    positive = sorted({p["value"] for p in parsed if p["value"] > 0}, reverse=True)
    for row in parsed:
        rank = positive.index(row["value"])/len(positive) if row["value"] > 0 else 1
        row["band"] = "alta" if rank < 1/3 else "media" if rank < 2/3 else "baixa"
    return parsed


def prepare_incidence(datasets, targets, as_of):
    target_set = set(normalize_path(targets))
    latest = {}
    for dataset in sorted(datasets, key=lambda d: (d["observed_date"], d["id"])):
        if dataset.get('incidence_included') is False:
            continue
        group = frozenset(normalize_path(dataset["institutions"]))
        if dataset["observed_date"] <= as_of and (not target_set or group == target_set or (len(group) == 1 and group.issubset(target_set))):
            previous = latest.get(group)
            if previous and previous["observed_date"] == dataset["observed_date"] and previous["unit"] == dataset["unit"]:
                combined = {}
                for row in [*previous["rows"], *dataset["rows"]]:
                    row_key = tuple(normalize_path(row["path"])) if row["path"] else ("unmatched", row.get("topic", ""))
                    combined[row_key] = row
                latest[group] = {**dataset, "rows": list(combined.values())}
            else:
                latest[group] = dataset
    prepared = []
    for dataset in latest.values():
        prepared.append({**dataset, "_index": {tuple(normalize_path(r["path"])): r for r in dataset["rows"] if r["path"]}})
    return prepared


def active_incidence_sources(datasets, institution_weights, as_of):
    """Escolhe fontes disjuntas e mantém separado o peso de exploração."""
    targets = {normalize_path([name])[0]: weight for name,weight in institution_weights.items()}
    prepared = prepare_incidence(datasets, list(targets), as_of)
    groups = {frozenset(normalize_path(d["institutions"])): d for d in prepared}
    if targets:
        total = sum(targets.values())
        singles = [(groups[frozenset([name])], weight/total) for name,weight in targets.items()
                   if frozenset([name]) in groups]
        if len(singles) == len(targets):
            return singles, [], 0
        if frozenset(targets) in groups:
            warning = "Tabela conjunta: seus membros não podem receber pesos individuais sem tabelas separadas."
            return [(groups[frozenset(targets)], 1)], [warning], 0
        warning = "Faltam tabelas para parte das instituições. Essa parcela usa exploração uniforme, não incidência presumida."
        return singles, [warning], 1-sum(weight for _,weight in singles)
    if prepared:
        warning = "Sem pesos definidos, usei somente o conjunto mais recente; não somei conjuntos sobrepostos."
        return [(max(prepared,key=lambda d:(d["observed_date"],d["id"])), 1)], [warning] if len(prepared)>1 else [], 0
    return [], ["Sem incidência aplicável: distribuição exploratória uniforme, sem tratar ausência como zero."], 1


def incidence_for_topic(path, datasets, targets, as_of, prepared=None):
    prepared = prepare_incidence(datasets, targets, as_of) if prepared is None else prepared
    result, key = [], tuple(normalize_path(path))
    for dataset in prepared:
        selected = next((dataset["_index"][key[:length]] for length in range(len(key), 0, -1) if key[:length] in dataset["_index"]), None)
        if selected is None:
            continue
        result.append({**selected, "institutions": dataset["institutions"], "unit": dataset["unit"],
                       "observed_date": dataset["observed_date"], "exact": len(selected["path"]) == len(path)})
    return result
