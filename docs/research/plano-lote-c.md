# Lote C — plano de execução

**Especificação:** `docs/roadmap/lote-C-decisao-e-uso.md`.
**Objetivo:** decisões de capacidade e meta com fontes separadas, estrutura de parâmetros sem recalibrar e revisão semanal opcional.
**Arquitetura:** novos módulos puros e telas dentro de Temas/Ajustes; schema 12 aditivo para versões/seleções de parâmetros e revisões semanais; mudanças de frequência somente por eventos StudyAgenda com prévia e cancelamento. Python, Streamlit, SQLite e pytest/AppTest.

## Restrições

Uso local, sem acesso às plataformas. Não alterar valores dos parâmetros. Sem nota prevista ou chance de aprovação. Fontes nunca dividem o mesmo denominador. Preservar versões/originais; não criar registros fictícios no banco ativo. UI em português e sem campos obrigatórios novos no registro rápido.

## Tarefas e interfaces

- [x] Confirmar A/B e registrar suíte inicial; backup antes de migrar os dados ativos.
- [x] C3/schema: `algorithm_parameters.py` com `AlgorithmParameters` congelado, valores atuais v1, `ParameterStore` com registro de versões imutáveis e seleção manual/CAS; `lote_c_schema.py` com tabelas de parâmetros, seleções e `weekly_reviews`. `AdaptiveProfile.parameters` resolve valores explícitos carregados por StudyStore. Refatorar constantes sem alterar saídas; regressão congelada anterior e teste de restauração.
- [x] C1: `study_triage_policy.py` puro produz demanda condicional/capacidade, candidatos protegidos e propostas manter/reduzir/adiar. `triage_service.py` implementa prévia/aplicar/desfazer no StudyAgenda; calendário e Hoje respeitam a política futura sem alterar lotes de 7 dias. UI em Temas → Plano de corte.
- [x] C2 independente: `goal_risk.py` e `goal_risk_ui.py`; função `goal_risk_report(service,as_of)` retorna por prova faixas Wilson/amostras separadas de simulados e inéditas por área; lacunas e temas responsáveis. Apenas leitura. UI Temas → Minha meta.
- [x] C4 independente: `weekly_review.py`, `weekly_review_ui.py`, `consolidated_export.py`; `WeeklyReviewStore(repo)` com eventos semanais/CAS; `weekly_summary(service,as_of)` e `render_weekly_review(service)`; resumo neutro em Hoje e CSV tipado de fontes separadas. Parent integra navegação e memória da modalidade.
- [x] C3 análise: `scripts/analise_calibracao.py`, somente leitura até com banco vazio/schema antigo; relatório Markdown e CSV tipados, lag/correlação/tempo/aderência e limites de amostra explícitos; UI seleção manual de versão em Ajustes.
- [x] Integração, AppTest, documentação de fonte/hipótese/limite por módulo, versão 0.23.0, revisão independente, suíte completa e verificação visual do app.

## Decisões e atenção na revisão

- Preservar os sete destinos atuais do lote B; o pedido de não criar destinos novos é atendido, sem remover Simulados ou Evolução.
- Demanda futura foi retirada da trajetória individual por não ser uma necessidade validada. Plano de corte calcula e identifica um cenário de demanda mantendo intervalos atuais; nunca o chama de número necessário para aprender.
- Sem medição válida, baixa convicção, erro adverso aberto ou incidência desconhecida: manter. Lotes conhecidos, reservas explícitas e revisão final não são adiados pelo corte.
- Calibração descreve dados; não recomenda nem salva valores novos. Troca de parâmetros só manual, entre versões cadastradas, com histórico.
- Rever conflitos entre corte e descansos/provas/trocas; regressão numérica da v1; sobreposição entre simulados convertidos e blocos; faixas sobrepostas ou amostra pequena; correções sem perda de histórico.

