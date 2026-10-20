from dataclasses import replace
import json
import math
import sqlite3

import pytest

from osler.planning import DayProfile, Measurement, RoutineConfig, plan_days, simulate_capacity
from osler.planning_service import PlanningService
from osler.storage import Repository


def roomy(**kwargs):
    base = RoutineConfig(start_date="2026-10-14", exam_every_days=0,
                         profiles={"normal": DayProfile(300, 40, 100, 30), "plantao": DayProfile(45, 10, 20, 10),
                                   "descanso": DayProfile(0, 0, 0, 0), "minimo": DayProfile(15, 3, 5, 5)})
    return replace(base, **kwargs)


def test_known_90_day_capacity_and_excess():
    result = simulate_capacity(roomy(), 31149, 90)
    assert result["nominal_capacity"] == 13500
    assert result["time_capacity"] == 13500
    assert result["excess_at_limit"] == 17649
    assert result["excess_with_time"] == 17649
    assert result["load_count"] == 31149
    assert "agendamento" in " ".join(result["warnings"]).lower()


def test_reservations_limit_capacity_and_time_units_are_correct():
    cfg = roomy(days=1, seconds_per_general=30, profiles={**roomy().profiles, "normal": DayProfile(60, 10, 100, 20)})
    result = simulate_capacity(cfg, 100, 1)
    # 60 min - 10×3 min - 20×30 s = 20 min; 40 cartões de 30 s.
    assert result["nominal_capacity"] == 150
    assert result["time_capacity"] == 40
    assert result["days"][0]["general_cards"] == 40
    assert result["days"][0]["planned_minutes"] <= 60


def test_rest_shift_and_minimum_never_generate_next_day_debt():
    cfg = roomy(days=4, overrides={"2026-10-14": "descanso", "2026-10-15": "plantao", "2026-10-16": "minimo"})
    days = plan_days(cfg)
    assert days[0]["questions"] == days[0]["general_cards"] == days[0]["error_cards"] == 0
    assert days[0]["time_capacity"] == 0
    assert days[1]["questions"] == 10
    assert days[2]["questions"] == 3
    assert days[3]["questions"] == 40
    assert all(d["planned_minutes"] <= d["available_minutes"] for d in days)


def test_exam_must_fit_and_missed_exam_does_not_become_debt():
    cfg = roomy(days=3, exam_every_days=2, exam_minutes=120,
                overrides={"2026-10-15": "plantao"})
    days = plan_days(cfg)
    assert days[1]["exam_minutes"] == 0
    assert "cabe" in days[1]["warning"]
    assert days[2]["exam_minutes"] == 0
    assert days[2]["questions"] == 40
    fitting = plan_days(roomy(days=2, exam_every_days=2, exam_minutes=240))
    assert fitting[1]["exam_minutes"] == 240
    assert fitting[1]["planned_minutes"] <= 300


def test_horizon_mismatch_is_not_extrapolated():
    with pytest.raises(ValueError, match="[Hh]orizonte"):
        simulate_capacity(roomy(days=30), 31149, 90)
    result = simulate_capacity(roomy(days=30), None, None)
    assert result["excess_with_time"] is None


@pytest.mark.parametrize("changes", [{"seconds_per_general": 0}, {"seconds_per_error": float("nan")}, {"minutes_per_question": math.inf},
                                     {"days": 0}, {"days": True}, {"daily_limit": -1}, {"exam_every_days": -1},
                                     {"start_date": "2026-02-30"}, {"weekday_types": {7: "normal"}}, {"overrides": {"ontem": "plantao"}}])
def test_invalid_config_is_rejected(changes):
    with pytest.raises(ValueError):
        roomy(**changes).validate()


def test_profiles_are_validated_and_serialization_preserves_weekdays():
    with pytest.raises(ValueError):
        roomy(profiles={**roomy().profiles, "normal": DayProfile(20, True, 100, 20)}).validate()
    cfg = roomy(weekday_types={0: "plantao", 6: "descanso"})
    assert RoutineConfig.from_dict(json.loads(json.dumps(cfg.to_dict()))).to_dict() == cfg.to_dict()


def test_measurements_and_profiles_are_immutable_and_exported(tmp_path):
    repo = Repository(tmp_path)
    service = PlanningService(repo)
    measure = Measurement("revisoes_periodo", 31149, "2026-10-14", "Informado pelo usuário", 90)
    mid = service.save_measurement(measure)
    assert service.save_measurement(measure) == mid
    service.save_measurement(Measurement("revisoes_high_yield", 26789, "2026-10-14", "Teste separado informado pelo usuário", 90))
    service.save_measurement(Measurement("cartoes_pendentes", 2002, "2026-10-14", "Outra tela informada pelo usuário", approximate=True))
    assert len(service.measurements()) == 3
    pid = service.save_profile("Cenário experimental", roomy())
    assert service.profiles()[0]["id"] == pid
    result = service.simulate(roomy(), mid)
    exported = service.export(result)
    assert json.loads(exported.json_path.read_bytes())["measurement"]["count"] == 31149
    assert exported.csv_path.is_file()
    with pytest.raises(ValueError):
        service.simulate(roomy(), service.measurements()[0]["id"])  # último: cartões, não revisões
    from osler.planner_service import PlannerService
    PlannerService(Repository(tmp_path))
    with sqlite3.connect(repo.db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
