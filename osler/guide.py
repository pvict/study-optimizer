"""Um próximo passo de estudo com informações existentes, sem falsa medida de domínio."""
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from .incidence import incidence_for_topic, prepare_incidence
from .models import normalize_path, stable_topic_id
from .planning import _date, _number


@dataclass(frozen=True)
class GuideSettings:
    institutions: list[str] = field(default_factory=list)
    normal_minutes: int = 120
    shift_minutes: int = 30
    start_date: str = "2026-10-15"
    target_date: str = "2027-11-30"

    def validate(self):
        if not isinstance(self.institutions, list) or any(not isinstance(i, str) or not i.strip() for i in self.institutions):
            raise ValueError("Informe os nomes das provas em linhas separadas.")
        for name in ("normal_minutes", "shift_minutes"):
            _number(getattr(self, name), name, positive=True, integer=True, maximum=720)
        if _date(self.target_date) <= _date(self.start_date):
            raise ValueError("A meta precisa estar depois do início da preparação.")
        return self

    def to_dict(self):
        return asdict(self)


def daily_blocks(minutes, kind):
    _number(minutes, "Tempo de hoje", positive=True, integer=True, maximum=720)
    if kind not in {"normal", "plantao", "descanso"}:
        raise ValueError("Escolha o tipo de dia.")
    if kind == "descanso":
        return []
    if kind == "plantao":
        minutes = min(minutes, 45)
    breaks = min(20, (minutes//60)*5)
    usable = minutes-breaks
    cards = min(15, (usable//30)*5)
    errors = max(0, 5*int((usable*0.2)//5))
    questions = usable-cards-errors
    output = [{"kind": "questoes", "title": "Resolva questões e entenda a correção", "minutes": questions},
              {"kind": "erros", "title": "Volte aos erros do bloco", "minutes": errors},
              {"kind": "gerais", "title": "Faça uma revisão curta de flashcards", "minutes": cards},
              {"kind": "pausa", "title": "Faça pausas entre os blocos", "minutes": breaks}]
    return [b for b in output if b["minutes"] > 0]


def roadmap(start, target):
    first, last = _date(start), _date(target)
    if last <= first:
        raise ValueError("A data da meta precisa ser posterior ao início.")
    days = (last-first).days+1
    cuts = [first, first+timedelta(days=int(days*.45)), first+timedelta(days=int(days*.8)), last+timedelta(days=1)]
    titles = ["Ganhar ritmo e cobrir as lacunas", "Treinar as provas que você quer", "Simular e ajustar os pontos frágeis"]
    actions = ["Questões comentadas, correção dos erros e revisão curta. Comece uma prova antiga a cada duas semanas, quando houver tempo.",
               "Aumente o contato com provas anteriores das instituições-alvo e use os erros para escolher o próximo estudo.",
               "Faça simulados completos em horários realistas e concentre a revisão nos erros que ainda se repetem."]
    return [{"title": title, "start": cuts[i].isoformat(), "end": (cuts[i+1]-timedelta(days=1)).isoformat(), "action": actions[i]} for i, title in enumerate(titles)]


def rank_topics(report, observations, incidence, targets, as_of, difficult_paths=None, recent_paths=None):
    day = _date(as_of)
    counts = Counter(tuple(normalize_path(r.path)) for r in report.records)
    areas = sorted({r.path[0] for r in report.records if r.path})
    rotation = day.toordinal() % max(1, len(areas))
    area_order = {a: (i-rotation) % len(areas) for i, a in enumerate(areas)}
    difficult, recent = set(difficult_paths or []), set(recent_paths or [])
    queue = {}
    prepared = prepare_incidence(incidence, targets, as_of)
    by_path = {tuple(normalize_path(r.path)): r for r in report.records if counts[tuple(normalize_path(r.path))] == 1}
    for row in report.records:
        key = tuple(normalize_path(row.path))
        if not row.is_leaf or len(row.path) != row.level+1 or counts[key] != 1 or row.total <= 0:
            continue
        difficult_parent = next((key[:length] for length in range(len(key)-1, 0, -1) if key[:length] in difficult and key[:length] in by_path), None)
        if key not in difficult and difficult_parent:
            row, key = by_path[difficult_parent], difficult_parent
        observation = observations.get(key)
        if observation and not 0 <= (day-_date(observation["data_observacao"])).days <= 90:
            observation = None
        frequency = incidence_for_topic(row.path, incidence, targets, as_of, prepared)
        high = any(i["band"] == "alta" and i["value"] > 0 for i in frequency)
        is_difficult = key in difficult or (observation is not None and (observation.get("erros_criticos") is True or observation.get("erros_recorrentes") is True or
            any(observation.get(p) is not None and observation[p] < 75 for p in ("acerto_primeira_tentativa", "acerto_recente"))))
        pdf_signal = row.studied >= 10 and row.acerto_pdf.value is not None and row.acerto_pdf.operator in {"=", "<"} and row.acerto_pdf.value < 70
        if high and not is_difficult and not pdf_signal:
            context = max(frequency, key=lambda s: len(s["path"]))["path"]
            context_key = tuple(normalize_path(context))
            if context_key in by_path:
                row, key = by_path[context_key], context_key
                frequency = incidence_for_topic(row.path, incidence, targets, as_of, prepared)
        if is_difficult:
            tier, reason = 0, "Você sinalizou dificuldade ou erros neste assunto. Vamos reforçá-lo com questões."
        elif high:
            tier, reason = 1, "Este assunto aparece entre os mais frequentes na tabela das provas que você trouxe."
        elif pdf_signal:
            tier, reason = 2, "Seu relatório sinaliza espaço para reforçar este tema. Um bloco de questões ajuda a localizar as dificuldades."
        elif row.studied < 10:
            tier, reason = 3, "Há pouca prática registrada neste tema. Comece com um bloco curto para conhecer suas dificuldades."
        else:
            tier, reason = 4, "Um bloco misto deste tema ajuda a conferir o que ficou e o que precisa voltar à revisão."
        native_order = {"incidencia altissima": 0, "incidencia alta": 1, "incidencia media": 2, "incidencia baixa": 3, "sem incidencia": 4}
        order = min((native_order.get(normalize_path([i.get("native_incidence", "")])[0], {"alta": 1, "media": 2, "baixa": 3}.get(i["band"], 4)) for i in frequency), default=4)
        item = {"topic_id": row.topic_id, "path": row.path, "name": row.name, "area": row.path[0], "reason": reason,
                      "incidence": frequency, "action": "praticar", "suspend": False, "tier": tier,
                      "practice_pdf": row.studied, "total_pdf": row.total, "recent": key in recent,
                      "_sort": (tier, key in recent, order, area_order[row.path[0]], row.studied/row.total, key)}
        if key not in queue or item["_sort"] < queue[key]["_sort"]:
            queue[key] = item
    return sorted(queue.values(), key=lambda i: i["_sort"])
