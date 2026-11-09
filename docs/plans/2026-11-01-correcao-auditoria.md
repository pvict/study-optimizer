# Correções da auditoria — plano de implementação

**Objetivo:** corrigir integralmente os defeitos comprovados na auditoria de 01/11, sem alterar registros históricos ou compromissos manuais. Autorizado pelo usuário nesta conversa, com backup prévio. As funções adicionais sugeridas na auditoria são propostas separadas; não exigem uma API inventada ou automação da Osler.

**Especificação:** `docs/audits/2026-11-01-auditoria-app.md` e reproduções em `evidencias/auditoria-2026-11-01/reproduzir_falhas.py`.

**Arquitetura:** estender os responsáveis existentes. Evidência individual e conjunta continuam separadas; a agenda consome sinais adversos sem duplicar denominadores. Streamlit renderiza somente seções abertas e conserva rascunhos independentemente dos widgets. Normalização e parâmetros preparados podem ser reutilizados sem cache de conexões ou dados desatualizados.

**Ambiente:** Python local, Streamlit 1.66, SQLite, Playwright/Edge. Trabalho no checkout atual `codex/attention-menu`, preservando alterações anteriores e índice; a autorização dispensa etapas adicionais de aprovação. Isolamento de dados para validação por cópia SQLite temporária, sem copiar backups anteriores.

## Segurança e invariantes

- [x] Backup do código atual, inclusive alterações não commitadas, em branch remota `codex/backup-pre-auditoria-20261101-175400`, commit `6d89cd3`.
- [x] Backup SQLite, originais e exportações validado por hashes e integridade: referência exata em `evidencias/correcao-auditoria-2026-11-01/backup.json`.
- Não alterar denominadores, modalidades, meta, convicção ou fontes por otimização.
- Não atribuir aos filhos acertos do grupo nem contato individual sem evidência.
- Proteger compromissos manuais, versões, concorrência e reversão; nenhuma migração silenciosa de estratégia.
- Não acessar plataforma autenticada, nem implementar integração automática sem interface oficial.
- Preservar idioma, componentes, espaçamento e foco acessível; explicações opcionais.

## Execução e responsáveis

### A. Evidências e revisões — agente de estatística

- [x] RED: grupo bom seguido de falha individual; evolução conjunta sem cobertura inventada; evidência mista suficiente acompanhada de 1 questão nova.
- [x] Corrigir `topic_grouping`, `balanced_reviews`, `study_evolution`, `evolution_service` e apresentação da Evolução.
- [x] GREEN: testes dirigidos, modalidades separadas, contato versus avaliação espaçada, preservação do histórico e da reversão.

### B. UI e fluxo — agente de interface

- [x] RED/AppTest: não calcular abas/ferramentas invisíveis; preservar rascunhos; atalhos precisos; validar antes de confirmar; download atualizado por versão.
- [x] Corrigir `adaptive_ui`, `error_cards_ui`, `study_calendar_ui`, `mock_exams_ui`, `study_registration_ui`, `mock_result_followup_ui`, `bento_day_ui` e auxiliares de confirmação/treino necessários.
- [x] GREEN: confirmar registros sem duplicar, adicionar/retirar rascunhos sem rerun completo; confirmação continua disponível.

### C. Preparação e tabela — agente principal

- [x] Testes de equivalência de preparação e invalidação: normalização retorna lista independente; alteração de parâmetros continua validada.
- [x] Otimizar normalização/índices/parâmetros nos responsáveis existentes, com limites de memória e sem caches de dados por TTL apenas.
- [x] Integrar chamada de evidência com mínimo configurado; retirar trabalho repetido comprovado.
- [x] Compactar filtros e bases de contadores em Temas, mantendo todas as ações e estatísticas detalhadas.

### D. Verificação integrada — agente principal + revisão independente

- [x] Rodar seleção afetada e suíte completa; investigar e registrar qualquer falha.
- [x] Verificar cópia dos dados reais em navegador, desktop e celular, inclusive rascunhos, busca, registro inválido e rotas.
- [x] Repetir tempos da auditoria e perfil do cálculo; comparar o resultado das otimizações com o algoritmo não otimizado no mesmo código corrigido.
- [x] Gerar evidência pequena com alterações de datas previstas, sem gravar a agenda ativa.
- [x] Revisão local concluída; revisão independente tentada, indisponível por limite de uso; relatório final com backup, prova, limites e arquivos.

## Registro de andamento

- 01/11: backup verificado e publicado antes de qualquer edição do produto. Análise prévia já reproduziu os defeitos. Escolha: corrigir arquitetura atual, sem reescrever frontend ou inventar novos serviços.
- 01/11: A, B e C concluídas com testes RED/GREEN. Integração corrigiu também a ordenação por prioridade de bancos pequenos e o uso da âncora espaçada no cenário futuro.
- 01/11: D concluída: suíte integral com 1.066 aprovados, um pulado (symlink no Windows), um aviso esperado de ZIP duplicado. Navegador e geometria mobile sem exceção/transbordamento nos recortes avaliados; snapshot e calendário idênticos com/sem otimizações no controle. Original das 30 tabelas preservado na conferência. Capturas redundantes e log repetitivo removidos; backup e evidências finais preservados. Revisão independente tentou executar, mas agentes ficaram indisponíveis por limite de uso; revisão local e provas automatizadas registradas no relatório.
