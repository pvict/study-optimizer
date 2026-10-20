from dataclasses import replace

import pytest

from osler.classification import ClassifierConfig, classify, wilson_interval
from osler.observations import Observation, parse_observation


def known(**kwargs):
    base = dict(data_observacao="2026-10-14", origem_da_informacao="Informado pelo usuário",
                nivel_de_confiabilidade="informado_usuario", questoes_distintas=44, respostas_totais=66,
                acerto_primeira_tentativa=82, acerto_ultima_tentativa=95, cartoes_estudados=146,
                cartoes_pendentes=11, cartoes_futuros=135, cartoes_selecionaveis=146)
    return Observation(**{**base, **kwargs})


def test_known_feridas_is_b_and_never_suspended():
    result = classify(known())
    assert result.category == "B"
    assert result.priority == "pendente_validacao"
    assert result.cards_involved == 146
    assert result.suspension_applied is False
    assert "erros_criticos" in result.missing
    assert result.wilson_low < 82 < result.wilson_high


def test_missing_first_attempt_is_not_replaced_by_pdf_or_review():
    result = classify(known(acerto_primeira_tentativa=None), pdf_accuracy=95, review_coverage=98)
    assert result.category == "D"
    assert result.priority == "sem_dados"


@pytest.mark.parametrize("n", [0, 1, 29])
def test_small_samples_cannot_be_a(n):
    assert classify(known(questoes_distintas=n, acerto_primeira_tentativa=100, acerto_ultima_tentativa=100,
                          erros_criticos=False, erros_recorrentes=False)).category == "D"


def test_a_requires_explicit_absence_of_errors():
    observation = known(questoes_distintas=60, acerto_primeira_tentativa=85, acerto_ultima_tentativa=90)
    assert classify(observation).category == "D"
    assert classify(replace(observation, erros_criticos=False, erros_recorrentes=False)).category == "A"


@pytest.mark.parametrize("initial,last,category", [(74.9, 95, "C"), (75, 90, "B"), (84.9, 95, "B"), (85, 90, "A"), (80, 84, "C")])
def test_threshold_boundaries(initial, last, category):
    result = classify(known(questoes_distintas=60, acerto_primeira_tentativa=initial,
                            acerto_ultima_tentativa=last, erros_criticos=False, erros_recorrentes=False))
    assert result.category == category


def test_explicit_errors_and_poor_recent_performance_require_review():
    assert classify(known(erros_criticos=True, acerto_primeira_tentativa=None)).category == "C"
    assert classify(known(erros_recorrentes=True)).category == "C"
    assert classify(known(acerto_recente=50)).category == "C"
    assert classify(known(risco_perda="alto")).category == "C"


def test_estimated_or_insufficient_coverage_not_mastered():
    assert classify(known(nivel_de_confiabilidade="estimado")).category == "D"
    assert classify(known(cobertura_suficiente=False)).category == "D"
    assert classify(known(), eligible=False).category == "D"


def test_config_and_weights_change_behavior_without_precise_ranking():
    assert classify(known(), config=ClassifierConfig(min_questions=50)).category == "D"
    observation = known(questoes_distintas=60, erros_criticos=False, erros_recorrentes=False, cartoes_ativos=300,
                        cartoes_pendentes=None, cartoes_futuros=None)
    cfg = ClassifierConfig(weights={"volume": 1})
    assert classify(observation, config=cfg).priority == "alta"
    assert classify(replace(observation, cartoes_ativos=30), config=cfg).priority == "baixa"
    assert classify(replace(observation, confianca_flashcards=1), config=cfg).priority == "pendente_validacao"


def test_missing_weights_do_not_get_average_values():
    result = classify(known(erros_criticos=False, erros_recorrentes=False), config=ClassifierConfig(weights={"incidencia": 1}))
    assert result.priority == "sem_dados"
    assert result.weight_coverage == 0


def test_wilson_interval_known_binomial_example():
    low, high = wilson_interval(50, 100)
    assert low == pytest.approx(40.383, abs=0.01)
    assert high == pytest.approx(59.617, abs=0.01)


@pytest.mark.parametrize("changes", [{"questoes_distintas": -1}, {"questoes_distintas": True},
    {"acerto_primeira_tentativa": float("nan")}, {"acerto_ultima_tentativa": 101},
    {"respostas_totais": 2}, {"data_observacao": "2026-02-30"}, {"origem_da_informacao": ""},
    {"cartoes_ativos": 10}, {"erros_criticos": "não"}, {"incidencia_provas": "alta"}])
def test_inconsistent_observation_rejected(changes):
    with pytest.raises(ValueError):
        known(**changes).validate()


def test_csv_numbers_and_unknown_flags_preserve_meaning():
    values = dict(data_observacao="2026-10-14", origem_da_informacao="Consulta manual", nivel_de_confiabilidade="informado_usuario",
                  questoes_distintas="44", acerto_primeira_tentativa="82,5%", erros_criticos="", erros_recorrentes="não")
    item = parse_observation(values)
    assert item.acerto_primeira_tentativa == 82.5
    assert item.erros_criticos is None
    assert item.erros_recorrentes is False


@pytest.mark.parametrize("changes", [{"min_questions": 0}, {"a_initial": 70}, {"weights": {"volume": -1}},
    {"weights": {"inventado": 1}}, {"weights": {"volume": 0}}, {"min_weight_coverage": float("nan")}])
def test_invalid_policies_rejected(changes):
    with pytest.raises(ValueError):
        ClassifierConfig(**changes).validate()
