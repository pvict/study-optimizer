# Atenção em página própria — escopo final

Em29/10/2026 o usuário cancelou a integração das revisões externas Osler à carga do app e pediu restaurar o planejamento anterior. O código experimental de carga/avaliação integrada e seus testes foram retirados. Nenhuma configuração dessa integração havia sido aplicada no banco ativo; meta120 e perfil14 preservados. O pequeno registro automático de análise permanece no histórico, sem influência no cálculo.

## Entrega mantida

- [x] Temas em atenção como item próprio da barra lateral; Hoje preservado.
- [x] Tabela completa buscável, nunca praticados por importância institucional, fontes, acerto e tempo sem contato separados.
- [x] Skills Visant de design instaladas e aplicação compatível com Apple/Streamlit.
- [x] Correção de UX: saldo do lote de revisão explícito; converter um rascunho para lista do tema mantém contagens e não quita indevidamente o lote anterior.
- [x] Testes de navegação, dados e registro; QA sintética desktop/tablet/celular.

## Limites

A rotina, agenda, cálculo estatístico e metas voltaram ao código anterior à integração. Os retornos vinculados já existentes continuam com suas regras originais. Nenhum dado de estudo foi apagado ou inventado. A instalação de skills foi mantida. Documentação científica do painel: docs/research/atencao-temas-2026-10-29.md.

Backup do estado anterior: tag remota backup/pre-rotina-integrada-2026-10-29. Código descartado não é uma funcionalidade disponível.

Validação final:57 testes dirigidos aprovados para o escopo final (atenção, navegação, registro vinculado, dia e regressões existentes). QA sintética em1440/768/390px confirmou Hoje sem os painéis novos, página própria preenchida e sem estouro horizontal do documento. Saúde local HTTP200. Arquivos de cálculo/agenda/calendário retornaram exatamente ao conteúdo anterior, sem diferenças funcionais no Git. A suíte de1057 testes da etapa experimental havia passado, mas não é apresentada como prova exclusiva deste escopo final: os testes dirigidos e a QA foram executados após a retirada.
