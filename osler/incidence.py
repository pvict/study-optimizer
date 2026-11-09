"""Leitura local de tabelas copiadas; nunca executa HTML ou consulta a Osler."""
from collections import Counter, defaultdict
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
        self.span = None

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignore += 1
        if self.ignore:
            return
        attrs = dict(attrs)
        if tag == "table" and self.table is None:
            self.table = {"headers": [], "rows": []}
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {"text": [], "primary": [], "secondary": [], "labels": [], "header": tag == "th"}
        elif tag == "span" and self.cell is not None:
            classes = attrs.get("class", "")
            self.span = "primary" if "PrimaryText" in classes or "ThemeTitle-" in classes else "secondary" if "SecondaryText" in classes or "ThemePath-" in classes else None
        if self.cell is not None:
            label = attrs.get("aria-label") or attrs.get("title")
            if label and label not in self.cell["labels"]:
                self.cell["labels"].append(label)

    def handle_data(self, data):
        if not self.ignore and self.cell is not None and data.strip():
            self.cell["text"].append(data.strip())
            if self.span:
                self.cell[self.span].append(data.strip())

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignore = max(0, self.ignore-1)
            return
        if self.ignore:
            return
        if tag == "span":
            self.span = None
        elif tag in {"td", "th"} and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row and self.table is not None:
            values = []
            for index, cell in enumerate(self.row):
                value = " ".join(cell["text"] or cell["labels"])
                if index == 0 and cell["primary"] and cell["secondary"]:
                    primary, secondary = " ".join(cell["primary"]), " ".join(cell["secondary"])
                    path = [p.strip() for p in re.split(r">>|→|>|»|›", secondary) if p.strip()]
                    if not path or normalize_path([path[-1]]) != normalize_path([primary]):
                        path.append(primary)
                    value = " → ".join(path)
                values.append(value)
            if any(c["header"] for c in self.row):
                self.table["headers"] = values
            else:
                self.table["rows"].append(values)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_html_table(text):
    parser = _TableReader()
    parser.feed(text)
    if not parser.tables:
        raise ValueError("Não encontrei uma tabela. Copie o elemento <table> com Copy outerHTML.")
    table = max(parser.tables, key=lambda t: len(t["rows"]))
    if not table["rows"]:
        raise ValueError("A tabela não contém linhas de temas no arquivo recebido.")
    width = max(len(r) for r in table["rows"])
    if width < 2 or any(len(r) != width for r in table["rows"]):
        raise ValueError("A tabela tem colunas incompletas. Copie o elemento <table> inteiro.")
    if len(table["headers"]) != width:
        table["headers"] = ["Tema", *[f"Coluna {i+1}" for i in range(1, width)]]
    return table


def table_as_text(table, value_column):
    if type(value_column) is not int or not 1 <= value_column < len(table["headers"]):
        raise ValueError("Escolha uma coluna numérica da tabela.")
    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Tema", "Valor"])
    writer.writerows([r[0], r[value_column]] for r in table["rows"])
    return output.getvalue()


def parse_incidence(text, report, unit):
    if unit not in {"questoes", "percentual"}:
        raise ValueError("Escolha questões ou percentual para esta tabela.")
    lines = [line for line in text.lstrip("\ufeff").splitlines() if line.strip()]
    if not lines:
        raise ValueError("A tabela está vazia.")
    delimiter = "\t" if "\t" in lines[0] else ";" if ";" in lines[0] else ","
    raw = list(csv.reader(lines, delimiter=delimiter))
    if normalize_path([raw[0][0]])[0] in {"tema", "assunto", "subtema", "hierarquia", "caminho"}:
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
            if "%" in value or not re.fullmatch(r"\d+|\d{1,3}(?:\.\d{3})+", number):
                raise ValueError(f"Linha {line}: quantidade de questões inválida.")
            number = int(number.replace(".", ""))
        else:
            if not re.fullmatch(r"\d+(?:[.,]\d+)?", number):
                raise ValueError(f"Linha {line}: percentual inválido.")
            number = float(number.replace(",", "."))
            if not math.isfinite(number) or not 0 <= number <= 100:
                raise ValueError(f"Linha {line}: percentual fora de 0 a 100.")
        path_parts = [p.strip() for p in re.split(r">>|→|>", topic) if p.strip()]
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
