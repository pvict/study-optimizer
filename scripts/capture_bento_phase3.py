"""Capturas de Temas/Registrar com cenário sintético descartável; somente porta8602."""
import argparse
from pathlib import Path
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import capture_bento
from scripts.seed_demo_data import seed_demo_data
from osler.planner_service import today_local


def capture(label):
    with tempfile.TemporaryDirectory(prefix='osler-bento-fase3-') as temporary:
        root=Path(temporary).resolve()
        assert root.is_relative_to(Path(tempfile.gettempdir()).resolve()) and root.name.startswith('osler-bento-fase3-')
        scenario=root/'scenario';seed_demo_data(scenario,today_local())
        capture_bento.SCREENS=[s for s in capture_bento.SCREENS if s[0] in {'temas','registrar'}]
        result=capture_bento.capture(scenario,ROOT/'evidencias/bento/fase3',label,all_screens=True)
        print(f"{len(result['screens'])} capturas · {len(result['blocked_remote_requests'])} requisições externas")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label',choices=['antes','depois'])
    capture(parser.parse_args().label)
