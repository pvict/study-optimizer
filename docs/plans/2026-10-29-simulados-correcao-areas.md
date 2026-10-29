# Simulados, treino por área e correção

Execução autorizada pelo usuário, sem ciclos adicionais de aprovação. Usar Superpowers (plano, testes e verificação), Impeccable e Revenue no Bento existente. Find Skills consultado; nenhuma dependência nova necessária.

## Comportamento e invariantes

- Simulado completo conserva seu dia exclusivo e seu histórico.
- Treino de área é uma tarefa separada dos temas: instituição × uma das cinco grandes áreas. Sugestão inicial operacional: um treino de 20 questões por semana; permitir dois e edição por ocorrência. Rodízio cobre todas as combinações, sem deduzir incidência individual a partir de dados conjuntos.
- Questões reservadas para o treino saem dos 120 habituais, não são extras. Resultados ficam em MockExams. Conversões por tema não podem ser somadas novamente nem completar a correção do próprio simulado.
- Erros podem ser informados no registro ou depois. Mapear tema específico e número opcional de erros; sem denominador não calcular acerto por tema. Guardar anotação versionada separada da nota, inclusive após conversão. Alteração da versão do resultado exige reconferência.
- Quarta-feira é sugestão editável para prática de correção após o simulado. Antes de haver temas, o calendário mostra orientação para informar erros, sem inventar estudo ou bloquear carga.
- Correção distribui até uma carga escolhida (referência 40) por incidência disponível, dificuldade observada e quantidade de erros com peso sublinear. Usar doses limitadas pela recomendação atual e banco conhecido, sem inflar só para preencher o dia. Temas que não cabem recebem datas seguintes ou limitação explícita. Mostrar reservas substituídas e capacidade na prévia.
- Mudanças de agenda usam token, comparação com prévia recalculada, histórico e desfazer; datas passadas e resultados preservados. Nenhuma mudança automática nos dados ativos ao abrir tela.
- Interface em português, abas Treinos por área e Correção, controles nativos e busca hierárquica de temas; calendário e Hoje mostram compromissos.

## Evidências e limites

Prática distribuída, recuperação e feedback têm respaldo; frequência semanal, quarta-feira e pesos de distribuição são decisões operacionais revisáveis, não ótimos científicos demonstrados. Uma área não permite inferir subtemas. Não prometer 90% nem probabilidade de aprovação.

- [Revisão em profissões da saúde](https://pubmed.ncbi.nlm.nih.gov/37615780/)
- [Recuperação e feedback: evidências e perguntas abertas](https://pmc.ncbi.nlm.nih.gov/articles/PMC10409703/)
- [Espaçamento e horizonte de retenção](https://pubmed.ncbi.nlm.nih.gov/19076480/)

## Execução e prova

1. Testes de rodízio, validação de erros, doses e capacidade.
2. Estender StudyAgenda/MockExams e camada de serviço com reservas e anotações; não criar outro banco.
3. Integrar capacidade, Hoje, calendário e resultados sem dupla contagem.
4. UI Bento, prévia e edição; documentação do método.
5. Testes de integração, regressão, UI em desktop/celular; revisão independente final e correções.

Não copiar banco ativo para QA; fixtures sintéticas. Não acessar a plataforma Osler.

## Registro da execução

- Implementado em `codex/simulados-correcao-areas`, versão 0.29.0. Não foi necessário instalar dependências ou alterar o schema.
- Ruling: manter o teto da correção separado da capacidade total do dia. Reutilizar diretamente o reagendamento comum reduziria indevidamente um dia de 120 para 40; um alocador pequeno no módulo responsável usa os dois limites e protege reservas, descanso e treinos.
- Ruling: mudanças de frequência/carga preservam ocorrências passadas e com resultado, substituindo apenas a série futura após prévia. Não é necessário retirar um resultado para reconfigurar o futuro.
- Ruling: resultados de área somam volume, mas não geram acerto ou domínio por tema. Conversões explícitas são descontadas do volume externo para não duplicar contagens.
- A revisão independente identificou que o botão legado de dia feito dispensaria a rotina após um treino parcial. Reproduzido com teste vermelho, corrigido na camada de serviço e retirado da UI para esses treinos. A revisão independente foi interrompida por limite de uso do agente; a revisão restante foi local, com testes e QA, sem alegar aprovação independente completa.
- O QA encontrou uma suposição antiga de que todos os planos eram redistribuições comuns. O calendário agora identifica o formato responsável antes de oferecer desfazer. Teste de reprodução incluído.
- Prova: suíte completa **984 aprovados, 1 ignorado** (symlink indisponível), 1 aviso esperado de teste de ZIP inválido; 275,66s. Rodada dirigida: 74 aprovados. Após ajuste da descrição de fonte sem incidência, os testes de serviço/UI afetados passaram: **12 aprovados**, 15,61s.
- QA: 16 combinações de tela/tamanho, sem exceções ou estouro horizontal do documento. Tamanhos 1440×900, 1366×768, 768×1024, 390×844. Conferidas capturas de desktop e celular; tabelas e abas mantêm rolagem nativa. Evidências locais pequenas em `evidencias/exam-practice`, cenário descartável removido.
- Saúde do servidor local: HTTP 200 em `http://127.0.0.1:8501/_stcore/health`. Dados ativos não foram usados para QA; nenhum resultado de estudo ou configuração de treino foi fabricado no perfil do usuário. O rodízio aguarda a prévia aplicada na interface.
