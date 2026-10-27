from pathlib import Path

import pymupdf
import pytest


@pytest.fixture(autouse=True)
def stable_scenario_clock(monkeypatch):
    """Os cenários usam 15/10/2026; a passagem dos dias não deve alterar seus resultados.

    Somente o relógio do domínio é substituído. Arquivos, timestamps de auditoria
    e o aplicativo fora dos testes continuam usando a data real.
    """
    from datetime import datetime
    import osler.planner_service
    class ScenarioClock(datetime):
        @classmethod
        def now(cls,tz=None):
            return cls(2026,10,15,12,tzinfo=tz)
    monkeypatch.setattr(osler.planner_service,'datetime',ScenarioClock)


@pytest.fixture
def sample_pdf():
    """Layout de teste; contagens e expectativas independentes do importador."""
    def build(kind="qbank", scope="Todos", date="14/10/2026", bad_counts=False):
        doc = pymupdf.open()
        cover = doc.new_page(width=595.28, height=841.89)
        title = "Qbank" if kind == "qbank" else "Flashcards"
        cover.insert_text((48, 50), date)
        cover.insert_text((48, 80), f"{title.upper()} - ACERVO & ACURÁCIA")
        cover.insert_text((48, 110), "Detalhado por área - 3 temas no acervo")
        if kind == "qbank":
            cover.insert_text((48, 140), "44 de 100 questões respondidas")
            cover.insert_text((48, 160), "42 acertos em 44 respondidas")
        else:
            cover.insert_text((48, 140), "146 de 147 cards feitos")
            cover.insert_text((48, 160), "140 de 146 feitos já vistos 2+ vezes")

        def page():
            p = doc.new_page(width=595.28, height=841.89)
            p.insert_text((48, 60), f"Estatísticas > {title} > Acervo & acurácia")
            p.insert_text((48, 78), f"{scope} · {date}")
            p.insert_text((48, 112), "Tema")
            for x, txt in zip([320, 385, 462, 515],
                              ["Questões" if kind == "qbank" else "Cards",
                               "Respondidas" if kind == "qbank" else "Feitos",
                               "% visto", "% acerto" if kind == "qbank" else "% revisado"]):
                p.insert_text((x, 112), txt, fontsize=8)
            return p

        def row(p, y, level, name, total, studied, coverage, metric):
            p.insert_text((48 + 10.5 * level, y), name, fontsize=9)
            for x, txt in zip([330, 402, 472, 530], [str(total), str(studied), coverage, metric]):
                p.insert_text((x, y), txt, fontsize=9)

        p = page()
        row(p, 145, 0, "Clínica Cirúrgica", 100 if kind == "qbank" else 147,
            44 if kind == "qbank" else 146, "44%" if kind == "qbank" else "99%", "95%")
        row(p, 167, 1, "Cirurgia Plástica", 100 if kind == "qbank" else 147,
            44 if kind == "qbank" else 146, "44%" if kind == "qbank" else "99%", "95%")
        p = page()
        p.insert_text((48, 143), "Clínica Cirúrgica > Cirurgia Plástica (continuação)", fontsize=9)
        row(p, 165, 2, "Cicatrização e Avaliação", 99 if kind == "qbank" else 146,
            (110 if bad_counts else 44) if kind == "qbank" else 146, "44%" if kind == "qbank" else "100%", "95%")
        p.insert_text((69, 177), "de Feridas", fontsize=9)
        row(p, 198, 2, "Outro", 1, 0, "<1%", "-")
        data = doc.tobytes()
        doc.close()
        return data
    return build


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parents[1]


def open_view(app, main=None, adaptive=None):
    """Navega pelas mesmas chaves de estado do menu único, sem widgets legados."""
    if main is not None: app.session_state['main_view']=main
    elif adaptive is not None: app.session_state['main_view']='Plano de questões'
    if adaptive is not None: app.session_state['adaptive_view']=adaptive
    return app.run()
