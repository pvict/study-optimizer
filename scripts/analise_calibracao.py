"""Uso: python scripts/analise_calibracao.py --db ... --output ... --as-of ..."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from osler.calibration_analysis import write_report
from osler.workspace import active_data_dir
from osler.planner_service import today_local


def main():
    parser=argparse.ArgumentParser(description='Análise local somente leitura; não ajusta parâmetros.')
    parser.add_argument('--db',type=Path,default=active_data_dir(ROOT)/'osler.sqlite3')
    parser.add_argument('--output',type=Path,default=ROOT/'analises'/'calibracao')
    parser.add_argument('--as-of',default=today_local().isoformat())
    args=parser.parse_args()
    try:
        for path in write_report(args.db,args.output,args.as_of): print(path)
    except (ValueError,OSError) as exc: parser.exit(1,str(exc)+'\n')


if __name__=='__main__': main()
