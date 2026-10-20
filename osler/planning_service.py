"""Orquestra medições/cenários e exporta seus parâmetros junto aos resultados."""
import csv
from dataclasses import dataclass
import hashlib
from io import StringIO
import json
from pathlib import Path

from .files import write_immutable
from .planning import simulate_capacity
from .planning_storage import PlanningStore


def planning_csv(result):
    rows = [{k: v for k, v in row.items() if k != "unfilled_goals"} for row in result["days"]]
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


@dataclass
class PlanningExport:
    folder: Path
    csv_path: Path
    json_path: Path


class PlanningService:
    def __init__(self, repository):
        self.repository = repository
        self.store = PlanningStore(repository)

    def save_measurement(self, measurement):
        return self.store.save_measurement(measurement)

    def measurements(self):
        return self.store.measurements()

    def save_profile(self, name, config):
        return self.store.save_profile(name, config)

    def profiles(self):
        return self.store.profiles()

    def simulate(self, config, measurement_id=None):
        measurement = None
        if measurement_id is not None:
            measurement = next((m for m in self.measurements() if m["id"] == measurement_id), None)
            if not measurement or measurement["kind"] == "cartoes_pendentes":
                raise ValueError("Escolha uma medição de revisões do período; cartões pendentes têm outro denominador.")
        result = simulate_capacity(config, measurement["count"] if measurement else None, measurement["horizon_days"] if measurement else None)
        result["measurement"] = {k: v for k, v in measurement.items() if k not in {"payload", "digest"}} if measurement else None
        if measurement:
            result["warnings"].append("Medição declarada em " + measurement["observed_date"] + "; o início/corte do cenário pode diferir. Compare a origem antes de interpretar o excedente.")
        return result

    def export(self, result):
        payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
        folder = self.repository.exports/"planejamento"/hashlib.sha256(payload).hexdigest()
        folder.mkdir(parents=True, exist_ok=True)
        csv_path, json_path = folder/"rotina.csv", folder/"cenario.json"
        write_immutable(csv_path, planning_csv(result))
        write_immutable(json_path, payload)
        return PlanningExport(folder, csv_path, json_path)
