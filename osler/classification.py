"""Heurísticas de triagem; nunca aprovação ou execução de suspensão."""
from dataclasses import asdict, dataclass, field
import math

from .observations import Observation

DEFAULT_WEIGHTS = {"inicial": 3, "ultima": 2, "amostra": 2, "volume": 2, "relevancia": 1,
                   "incidencia": 1, "erros": 2, "dificuldade": 1, "risco": 2}


@dataclass(frozen=True)
class ClassifierConfig:
    min_questions: int = 30
    a_initial: float = 85
    a_last: float = 90
    b_initial: float = 75
    b_improvement: float = 5
    c_recent: float = 75
    min_weight_coverage: float = 0.65
    volume_reference: int = 300
    max_age_days: int = 90
    wilson_floor: float = 70
    weights: dict = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def validate(self):
        if type(self.min_questions) is not int or self.min_questions < 1 or type(self.volume_reference) is not int or self.volume_reference < 1:
            raise ValueError("Amostra mínima e referência de volume devem ser inteiros positivos.")
        if type(self.max_age_days) is not int or self.max_age_days < 1:
            raise ValueError("Validade temporal deve ser um número positivo de dias.")
        for name in ["a_initial", "a_last", "b_initial", "b_improvement", "c_recent", "wilson_floor"]:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError(f"Critério inválido: {name}.")
        if self.b_initial >= self.a_initial or self.a_last < self.a_initial:
            raise ValueError("Critérios devem satisfazer B inicial < A inicial <= A última.")
        if not isinstance(self.min_weight_coverage, (float, int)) or not math.isfinite(self.min_weight_coverage) or not 0 < self.min_weight_coverage <= 1:
            raise ValueError("Cobertura mínima de pesos deve estar em (0,1].")
        if not self.weights or set(self.weights) - set(DEFAULT_WEIGHTS):
            raise ValueError("Pesos desconhecidos ou ausentes.")
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0 for v in self.weights.values()) or sum(self.weights.values()) <= 0:
            raise ValueError("Pesos devem ser finitos, não negativos e pelo menos um deve ser positivo.")
        return self

    def to_dict(self):
        return asdict(self)


def wilson_interval(percent: float, n: int) -> tuple[float, float]:
    """Wilson bilateral 95%, aproximado quando o percentual foi arredondado.

    Fórmula: NIST/SEMATECH Handbook, seção 7.2.4.1. Não demonstra causalidade,
    independência entre questões ou validade dos limites de classificação.
    """
    if n <= 0 or not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError("Wilson exige n positivo e percentual válido.")
    z = 1.959963984540054
    p, z2 = percent / 100, z*z
    center = (p + z2/(2*n)) / (1 + z2/n)
    radius = z * math.sqrt(p*(1-p)/n + z2/(4*n*n)) / (1 + z2/n)
    return max(0, 100*(center-radius)), min(100, 100*(center+radius))


@dataclass
class Classified:
    category: str
    priority: str
    reasons: list[str]
    missing: list[str]
    evidence: list[str]
    warnings: list[str]
    cards_involved: int | None
    weight_coverage: float = 0
    wilson_low: float | None = None
    wilson_high: float | None = None
    suspension_applied: bool = False


def classify(observation: Observation | None, config: ClassifierConfig | None = None, *, eligible=True,
             pdf_accuracy=None, review_coverage=None) -> Classified:
    cfg = (config or ClassifierConfig()).validate()
    missing, evidence, warnings = [], [], ["Limites heurísticos configuráveis, sem validação científica para suspensão."]
    cards, low, high = None, None, None
    if observation is not None:
        o = observation.validate()
        required = ["questoes_distintas", "respostas_totais", "acerto_primeira_tentativa", "acerto_ultima_tentativa",
                    "erros_criticos", "erros_recorrentes", "cobertura_suficiente", "risco_perda", "relevancia_residencia", "incidencia_provas"]
        missing = [name for name in required if getattr(o, name) is None]
        cards = next((v for v in [o.cartoes_selecionaveis, o.cartoes_ativos, o.cartoes_estudados] if v is not None), None)
        evidence = [f"Origem: {o.origem_da_informacao}; data {o.data_observacao}; confiabilidade {o.nivel_de_confiabilidade}."]
        for name in ["questoes_distintas", "respostas_totais", "acerto_primeira_tentativa", "acerto_ultima_tentativa", "acerto_recente"]:
            if getattr(o, name) is not None:
                evidence.append(f"{name}: {getattr(o, name)} (informado pelo usuário).")
        if o.questoes_distintas and o.acerto_primeira_tentativa is not None:
            low, high = wilson_interval(o.acerto_primeira_tentativa, o.questoes_distintas)
            warnings.append("Wilson de 95% aproximado: percentual possivelmente arredondado; representatividade e independência não verificadas.")
    else:
        o = None
        missing = ["observacao_manual", "questoes_distintas", "acerto_primeira_tentativa", "acerto_ultima_tentativa"]
    if pdf_accuracy is not None:
        accuracy_label = str(pdf_accuracy) if str(pdf_accuracy).endswith("%") else f"{pdf_accuracy}%"
        evidence.append(f"PDF: acerto {accuracy_label} com tentativa não identificada; não substitui o inicial.")
    if review_coverage is not None:
        coverage_label = str(review_coverage) if str(review_coverage).endswith("%") else f"{review_coverage}%"
        evidence.append(f"Flashcards: {coverage_label} é cobertura de revisão, não acerto.")
    def answer(category, reason, priority=None):
        return Classified(category, priority or ("manter_revisao" if category == "C" else "sem_dados"), [reason],
                          missing, evidence, list(warnings), cards, wilson_low=low, wilson_high=high)
    if not eligible:
        return answer("D", "Agregado, hierarquia bloqueada ou granularidade diferente: não classificar como subtema consolidado.")
    if not o:
        return answer("D", "Sem observação manual: questões distintas e acertos por tentativa não estão confirmados.")
    if o.erros_criticos is True or o.erros_recorrentes is True:
        return answer("C", "Erros críticos ou recorrentes informados: manter revisão direcionada, mesmo com percentuais altos.")
    if o.nivel_de_confiabilidade == "estimado":
        return answer("D", "Indicadores estimados: não sustentar proposta de redução.")
    if o.questoes_distintas is None or o.questoes_distintas < cfg.min_questions or o.acerto_primeira_tentativa is None:
        return answer("D", f"Primeira tentativa ausente ou menos de {cfg.min_questions} questões distintas confirmadas.")
    if o.acerto_primeira_tentativa < cfg.b_initial or (o.acerto_recente is not None and o.acerto_recente < cfg.c_recent):
        return answer("C", "Desempenho inicial ou recente abaixo do limite configurado: priorizar lacunas e questões erradas.")
    if o.risco_perda == "alto":
        return answer("C", "Risco de perda informado como alto: manter revisão e reavaliar antes de reduzir.")
    if o.cobertura_suficiente is False:
        return answer("D", "Cobertura declarada insuficiente: não extrapolar a amostra para todo o tema.")
    if o.acerto_ultima_tentativa is None:
        return answer("D", "Última tentativa ausente: melhora e consolidação não confirmadas.")
    if o.acerto_primeira_tentativa >= cfg.a_initial and o.acerto_ultima_tentativa >= cfg.a_last:
        if o.erros_criticos is None or o.erros_recorrentes is None:
            return answer("D", "Percentuais altos, mas histórico de erros não avaliado: domínio não presumido.")
        result = answer("A", "Amostra e percentuais atendem aos limites, com ausência de erros explicitamente informada. Candidato, sujeito à validação.")
    elif o.acerto_primeira_tentativa >= cfg.b_initial and o.acerto_ultima_tentativa >= cfg.a_last and o.acerto_ultima_tentativa-o.acerto_primeira_tentativa >= cfg.b_improvement:
        result = answer("B", "Melhora nas tentativas e desempenho inicial intermediário: avaliar redução seletiva, preservando conceitos frágeis.")
    else:
        return answer("C", "Critérios de redução não satisfeitos: manter revisões direcionadas e investigar conceitos frágeis.")
    if o.erros_criticos is None or o.erros_recorrentes is None or (o.confianca_flashcards is not None and o.confianca_flashcards <= 2):
        result.priority = "pendente_validacao"
        result.reasons.append("Antes de priorizar redução, avaliar erros e baixa confiança subjetiva; confiança alta não substitui questões.")
        return result
    volume = next((v for v in [o.cartoes_ativos, o.cartoes_selecionaveis, o.cartoes_estudados] if v is not None), None)
    ordinal = {"baixa": 0, "media": 0.5, "alta": 1}
    features = {"inicial": o.acerto_primeira_tentativa/100, "ultima": o.acerto_ultima_tentativa/100,
                "amostra": min(1, o.questoes_distintas/(2*cfg.min_questions)),
                "volume": min(1, volume/cfg.volume_reference) if volume is not None else None,
                "relevancia": ordinal.get(o.relevancia_residencia), "incidencia": ordinal.get(o.incidencia_provas),
                "erros": 1, "dificuldade": 1-ordinal[o.dificuldade] if o.dificuldade else None,
                "risco": {"baixo": 1, "moderado": 0.5, "alto": 0}.get(o.risco_perda)}
    available = sum(weight for key, weight in cfg.weights.items() if features[key] is not None)
    result.weight_coverage = available/sum(cfg.weights.values())
    if result.weight_coverage < cfg.min_weight_coverage:
        result.priority = "sem_dados"
        result.reasons.append("Dados disponíveis não cobrem o peso mínimo; nenhum ranking preciso foi produzido.")
        return result
    score = sum(features[key]*weight for key, weight in cfg.weights.items() if features[key] is not None)/available
    result.priority = "alta" if score >= 0.75 else "media" if score >= 0.5 else "baixa"
    if low is not None and low < cfg.wilson_floor:
        result.priority = "baixa"
        result.reasons.append(f"Incerteza amostral elevada: limite inferior de Wilson <{cfg.wilson_floor}%; prioridade limitada a baixa.")
    result.warnings.append("Volume de cartões é proxy de itens avaliáveis; não estima revisões eliminadas nem autoriza suspensão.")
    return result
