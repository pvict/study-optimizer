from collections import Counter

from .models import Finding, Report


def validate_report(report: Report) -> list[Finding]:
    findings = []
    if not report.report_date:
        findings.append(Finding("data_ausente", "aviso", "Data do relatório ausente: não inferida pelo nome do arquivo."))
    if report.scope == "desconhecido":
        findings.append(Finding("escopo_ausente", "aviso", "Não foi possível determinar se o relatório contém todos os temas ou somente os iniciados."))
    for row in report.records:
        def add(code, severity, text):
            findings.append(Finding(code, severity, text, row.page, row.topic_id))
        if row.studied > row.total:
            add("estudados_maior_total", "erro", f"{row.name}: estudados ({row.studied}) excedem total ({row.total}). Dados preservados.")
        if report.scope == "iniciados" and row.studied == 0:
            add("nao_iniciado_no_filtro", "aviso", f"{row.name}: registro sem estudo em relatório de iniciados.")
        for label, pct in [("% visto", row.percentual_visto), ("% revisado", row.percentual_revisado), ("acerto PDF", row.acerto_pdf)]:
            if pct.value is not None and not 0 <= pct.value <= 100:
                add("percentual_fora_intervalo", "erro", f"{row.name}: {label} fora de 0 a 100%.")
        pct = row.percentual_visto
        if row.total > 0 and pct.value is not None:
            ratio = 100 * row.studied / row.total
            compatible = ((pct.operator == "=" and abs(ratio - pct.value) <= 0.51)
                          or (pct.operator == "<" and ratio < pct.value)
                          or (pct.operator == ">" and ratio > pct.value))
            if not compatible:
                add("cobertura_inconsistente", "aviso", f"{row.name}: % visto não corresponde às contagens, considerando arredondamento de 0,5 ponto percentual.")
    repeated = Counter(row.topic_id for row in report.records)
    for topic_id, count in repeated.items():
        if count > 1:
            findings.append(Finding("hierarquia_repetida", "aviso", f"Hierarquia repetida {count} vezes; nenhum registro eliminado automaticamente.", topic_id=topic_id))
    roots = [r for r in report.records if r.level == 0]
    leaves = [r for r in report.records if r.is_leaf]
    for label, rows in [("areas", roots), ("folhas", leaves)]:
        totals = {"total": sum(r.total for r in rows), "estudados": sum(r.studied for r in rows)}
        report.summary[f"soma_{label}"] = totals
        for key in ["total", "estudados"]:
            if key in report.summary and totals[key] != report.summary[key]:
                findings.append(Finding(f"total_{label}_divergente", "aviso" if label == "areas" else "info",
                                        f"Soma de {key} em {label}: {totals[key]}; capa: {report.summary[key]}. Pais podem conter unidades próprias; não somar pais e filhos."))
    declared = report.summary.get("nos_declarados")
    if declared is not None and len(leaves) != declared:
        findings.append(Finding("numero_nos_divergente", "aviso", f"Capa declara {declared} temas/decks; tabela contém {len(leaves)} registros terminais. Verificar a definição do contador."))
    if report.kind == "qbank":
        findings.append(Finding("tentativas_ausentes", "info", "O acerto do PDF não identifica primeira ou última tentativa. Questões distintas e respostas totais também não são inferidas."))
    else:
        findings.append(Finding("revisado_e_cobertura", "info", "% revisado é cobertura de revisão, não acerto. Cartões ativos, pendentes e futuros não constam destas tabelas."))
    return findings
