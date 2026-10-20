"""Guia diário que funciona antes de preencher indicadores individuais."""
from datetime import timedelta
import hashlib
import json

from .assessment_service import AssessmentService
from .files import write_immutable
from .guide import GuideSettings, daily_blocks, rank_topics, roadmap
from .guide_storage import GuideStore
from .incidence import parse_html_table, parse_incidence, table_as_text
from .matching_service import load_matching
from .models import normalize_path
from .planner_service import today_local
from .planning import _date


class GuideService:
    def __init__(self, repository):
        self.repository = repository
        self.store = GuideStore(repository)

    def settings(self):
        return self.store.settings() or {"id": 0, "settings": GuideSettings().to_dict()}

    def save_settings(self, settings, expected_id):
        return self.store.save_settings(settings, expected_id)

    def _report(self, kind, as_of):
        choices = [r for r in self.repository.list_reports(False) if r["kind"] == kind and r["complete"] and (r["report_date"] or "") <= as_of]
        if not choices:
            return None
        preferred = [r for r in choices if r["scope"] == "todos"] or choices
        chosen = max(preferred, key=lambda r: (r["report_date"] or "", r["imported_at"]))
        return self.repository.get_report(chosen["file_sha256"])

    def datasets(self):
        return self.store.datasets()

    def import_incidence(self, text, unit, institutions, observed_date, value_column=None):
        _date(observed_date)
        if not institutions or any(not isinstance(i, str) or not i.strip() for i in institutions):
            raise ValueError("Dê um nome ao conjunto de instituições desta tabela.")
        qbank = self._report("qbank", today_local().isoformat())
        if qbank is None:
            raise ValueError("Importe um PDF de questões para reconhecer os caminhos dos temas.")
        source_text, table = text, None
        if text.lstrip().startswith("<"):
            table = parse_html_table(text)
            if value_column is None:
                # Preferir a contagem explicitamente identificada das instituições.
                columns = [i for i, label in enumerate(table["headers"]) if i and "institu" in normalize_path([label])[0] and ("quest" in normalize_path([label])[0] if unit == "questoes" else "incid" in normalize_path([label])[0])]
                if len(columns) != 1:
                    columns = [i for i, label in enumerate(table["headers"]) if i and ("quest" in normalize_path([label])[0] if unit == "questoes" else "percent" in normalize_path([label])[0])]
                if len(columns) != 1:
                    raise ValueError("Escolha qual coluna da tabela deseja usar.")
                value_column = columns[0]
            text = table_as_text(table, value_column)
        rows = parse_incidence(text, qbank, unit)
        if table and value_column+1 < len(table["headers"]) and "incid" in normalize_path([table["headers"][value_column+1]])[0]:
            labels = {"incidencia altissima": "alta", "incidencia alta": "alta", "incidencia media": "media", "incidencia baixa": "baixa", "sem incidencia": "baixa"}
            for parsed, raw in zip(rows, table["rows"]):
                native = raw[value_column+1]
                parsed["native_incidence"] = native
                parsed["band"] = labels.get(normalize_path([native])[0], parsed["band"])
        source = source_text.encode("utf-8")
        digest = hashlib.sha256(source).hexdigest()
        folder = self.repository.exports/"incidencia"/digest
        folder.mkdir(parents=True, exist_ok=True)
        write_immutable(folder/("origem.html" if table else "origem.txt"), source)
        payload = {"institutions": [i.strip() for i in institutions], "observed_date": observed_date, "unit": unit, "rows": rows,
                   "qbank_report_id": qbank.file_sha256, "source_sha256": digest, "source_path": str(folder.relative_to(self.repository.root)),
                   "received_rows": len(rows), "matched_rows": sum(r["path"] is not None for r in rows)}
        return self.store.save_dataset(payload)

    def save_day(self, day, status, path, feedback="nao_registrei"):
        parsed = _date(day)
        if parsed > today_local() or status not in {"feito", "parcial", "descanso"} or feedback not in {"nao_registrei", "dificil", "tranquilo"}:
            raise ValueError("Escolha como foi um dia já realizado.")
        if not isinstance(path, list) or any(not isinstance(p, str) or not p.strip() for p in path):
            raise ValueError("Assunto inválido.")
        return self.store.save_day({"day": day, "status": status, "path": path, "feedback": feedback})

    def days(self):
        return self.store.days()

    def guide(self, as_of, minutes=None, kind="normal"):
        _date(as_of)
        settings = GuideSettings(**self.settings()["settings"]).validate()
        minutes = minutes if minutes is not None else settings.shift_minutes if kind == "plantao" else settings.normal_minutes
        q, f = self._report("qbank", as_of), self._report("flashcards", as_of)
        observations, classification = {}, None
        if q and f:
            matching = load_matching(self.repository, q.file_sha256, f.file_sha256)
            classification = AssessmentService(self.repository).analyze(matching, as_of)
            source_rows = {r.row_id: r.qbank for r in matching.rows}
            for item in classification["items"]:
                if item["observation"]:
                    source = source_rows.get(item["row_id"])
                    if source:
                        observations[tuple(normalize_path(source.path))] = item["observation"]
        recent_days = [d for d in self.days() if _date(as_of)-timedelta(days=14) <= _date(d["day"]) <= _date(as_of)]
        difficult = [tuple(normalize_path(d["path"])) for d in recent_days if d["feedback"] == "dificil"]
        recent = [tuple(normalize_path(d["path"])) for d in recent_days[:3]]
        queue = rank_topics(q, observations, self.datasets(), settings.institutions, as_of, difficult, recent) if q else []
        chosen, areas = [], set()
        for item in queue:
            if item["area"] not in areas or item["tier"] == 0:
                chosen.append(item)
                areas.add(item["area"])
            if len(chosen) == 3:
                break
        if len(chosen) < 3:
            chosen += [i for i in queue if i not in chosen][:3-len(chosen)]
        for item in chosen:
            item.pop("_sort", None)
        return {"date": as_of, "settings": settings.to_dict(), "blocks": daily_blocks(minutes, kind), "topics": chosen,
                "classification": classification, "phases": roadmap(settings.start_date, settings.target_date),
                "days": recent_days, "sources": {"qbank": q.file_sha256 if q else None, "flashcards": f.file_sha256 if f else None},
                "has_incidence": any(i["incidence"] for i in chosen), "kind": kind}
