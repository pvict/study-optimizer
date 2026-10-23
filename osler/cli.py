import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from .extraction import ImportFailure
from .service import import_bytes
from .storage import Repository
from .matching_service import load_matching, export_matching
from .workspace import active_data_dir
from .planner_service import today_local


def _choose_report(repo, kind, supplied, scope):
    if supplied:
        return supplied
    candidates = [r for r in repo.list_reports(False) if r["kind"] == kind and r["scope"] == scope and r["complete"]]
    if not candidates:
        raise ValueError(f"Relatório {kind}/{scope} não encontrado. Importe os PDFs primeiro.")
    return max(candidates, key=lambda r: (r["report_date"] or "", r["imported_at"]))["file_sha256"]


def _cross(args, repo) -> int:
    result = load_matching(repo, _choose_report(repo, "qbank", args.qbank, args.scope), _choose_report(repo, "flashcards", args.flashcards, args.scope), args.threshold)
    exported = export_matching(repo, result)
    print(f"Qbank: {result.qbank_date}/{result.qbank_scope}; Flashcards: {result.flashcards_date}/{result.flashcards_scope}")
    print(f"Pares exatos: {result.stats['pares_exatos']}; manuais: {result.stats['pares_manuais']}; terminais comparáveis: {result.stats['pares_terminais']}")
    print(f"Sem Flashcards: {result.stats['sem_flashcards']}; sem Qbank: {result.stats['sem_qbank']}; sugestões: {result.stats['sugestoes']}")
    for finding in result.findings:
        print(f"Aviso: {finding.message}")
    print(f"Tabela unificada: {exported.csv_path}")
    print(f"JSON auditável: {exported.json_path}")
    return 0


def _assess(args, repo):
    from .assessment_service import AssessmentService
    from .classification import ClassifierConfig
    matching = load_matching(repo, _choose_report(repo, "qbank", args.qbank, args.scope), _choose_report(repo, "flashcards", args.flashcards, args.scope))
    service = AssessmentService(repo)
    if args.indicators_csv:
        print(f"Observações importadas: {service.import_csv(matching, args.indicators_csv.read_bytes())}")
    config = ClassifierConfig()
    if args.policy_id is not None:
        policy = next((p for p in service.store.policies() if p["id"] == args.policy_id), None)
        if not policy:
            raise ValueError("Versão de critérios não encontrada.")
        config = ClassifierConfig(**policy["config"])
    result = service.analyze(matching, args.as_of, config)
    exported = service.export(result)
    print(f"Análise em {args.as_of}: " + "; ".join(f"{c}={result['stats'][c]}" for c in "ABCD"))
    print(f"Agregados/bloqueados/granularidade diferente: {result['stats']['excluidos']}")
    print(f"Classificação local: {exported.csv_path}")
    print("Categorias são triagem; nenhuma suspensão aplicada.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Importação local de PDFs exportados manualmente.")
    sub = parser.add_subparsers(dest="command", required=True)
    importer = sub.add_parser("import", help="Importar PDFs locais")
    importer.add_argument("paths", nargs="+", type=Path)
    crossing = sub.add_parser("cross", help="Cruzar um par de relatórios já importados")
    crossing.add_argument("--qbank", help="SHA-256 do Qbank; omissão seleciona o relatório mais recente no escopo")
    crossing.add_argument("--flashcards", help="SHA-256 dos Flashcards")
    crossing.add_argument("--scope", choices=["todos", "iniciados"], default="todos")
    crossing.add_argument("--threshold", type=float, default=0.86)
    assessment = sub.add_parser("assess", help="Classificar com indicadores manuais locais")
    assessment.add_argument("--qbank")
    assessment.add_argument("--flashcards")
    assessment.add_argument("--scope", choices=["todos", "iniciados"], default="todos")
    assessment.add_argument("--as-of", default=today_local().isoformat())
    assessment.add_argument("--indicators-csv", type=Path)
    assessment.add_argument("--policy-id", type=int)
    for command in [importer, crossing, assessment]:
        command.add_argument("--data-dir", type=Path)
    args = parser.parse_args(argv)
    repo = Repository(args.data_dir or active_data_dir(Path(__file__).resolve().parents[1]))
    if args.command == "assess":
        try:
            return _assess(args, repo)
        except (ValueError, KeyError, OSError) as exc:
            print(f"Classificação não realizada: {exc}")
            return 1
    if args.command == "cross":
        try:
            return _cross(args, repo)
        except (ValueError, KeyError, OSError) as exc:
            print(f"Cruzamento não realizado: {exc}")
            return 1
    files = []
    for path in args.paths:
        files.extend(sorted(path.glob("*.pdf")) if path.is_dir() else [path])
    if not files:
        print("Nenhum PDF encontrado.")
        return 1
    summary, failed = [], False
    for path in files:
        try:
            result = import_bytes(repo, path.read_bytes(), path.name)
            report = result.report
            entry = {"arquivo": path.name, "tipo": report.kind, "escopo": report.scope,
                     "data": report.report_date, "paginas": report.page_count, "paginas_extraidas": report.table_pages,
                     "linhas": len(report.records), "folhas": sum(r.is_leaf for r in report.records),
                     "status": report.status, "importacao": result.state, "duplicate_of": result.duplicate_of,
                     "file_sha256": report.file_sha256, "content_sha256": report.content_sha256,
                     "indicadores": report.summary, "achados": dict(Counter(f.code for f in report.findings)),
                     "csv": str(result.csv_path), "json": str(result.json_path)}
            summary.append(entry)
            failed |= any(f.severity == "erro" for f in report.findings)
            print(f"{path.name}: {report.kind}/{report.scope}, {len(report.records)} linhas, {result.state}, {report.status}")
        except (ImportFailure, OSError, ValueError) as exc:
            failed = True
            summary.append({"arquivo": path.name, "erro": str(exc)})
            print(f"{path.name}: erro - {exc}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = repo.exports / f"resumo_validacao_{stamp}.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resumo local: {target}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
