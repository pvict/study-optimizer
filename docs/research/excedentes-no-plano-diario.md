# Excedentes sem remover temas — desenho e plano

Pedido: responder além da quantidade de um bloco não pode consumir o espaço dos demais temas já propostos. Execução autorizada; manter metas, números reais, histórico, trocas, descansos e simulados.

Causa: allocate_day usa todas as tentativas em budget=target−done e nas cotas de novos/revisões. Uma sobra de duas questões pode impedir o encaixe de um bloco inteiro. O diário já guarda propostas; elas permitem distinguir o que foi apresentado ao aluno do que excedeu cada bloco.

Decisão: manter done_questions real; calcular crédito para alocação limitado à dose apresentada antes do registro. Excedentes não descontam cotas nem orçamento dos outros temas. Quando houver excedente, preservar os blocos restantes da proposta correspondente, respeitando trocas, reservas e mudanças explícitas de rotina. Não elevar silenciosamente a meta, transformar tentativas em questões distintas, nem congelar prioridades futuras.

daily_excess.py lê propostas e versões de sessões, sem escrita. Novas propostas registram corte de eventos, quantidade já realizada, total planejado com base no crédito, perfil e revisões do dia/agenda; propostas antigas continuam legíveis com datas de auditoria. Correções/desconsiderações recalculam os créditos usando as versões ativas, sem congelar a contagem de uma sessão anterior. Sem proposta anterior identificável, manter comportamento existente, sem inventar dose original. Descanso, simulado, revisão final e alterações explícitas continuam tendo precedência.

Exemplo de funcionamento: plano com seis blocos de20, meta120. Registrar22 no primeiro deixa os outros cinco blocos de20, mantendo o total real de22 e identificando duas excedentes. Concluir tudo soma122; a meta não é elevada silenciosamente. A distinção é só de alocação: acerto, convicção, amostra, histórico e tempos usam as22 tentativas reais.

Preservar uma proposta não cancela uma troca manual nem uma nova programação exclusiva de revisões. O app protege apenas propostas compatíveis com as configurações efetivas. Uma mudança apenas do método interno de revisão mantém os compromissos do dia; metas, configuração do dia e programação explícita continuam tendo precedência. Se a última proposta com excedente não tiver mais blocos pendentes, a busca considera as propostas anteriores compatíveis. No dia seguinte, não há crédito excedente herdado nem estudo dado como realizado. O dia de estudo continua virando às04h de Brasília.

Plano (Superpowers:executing-plans/TDD; UI existente com Revenue-Centric Design/Impeccable):

- [x] Reproduzir +2 em modo fixo/adaptativo e proposta legada; testar registro parcial, correção, desconsideração, dia seguinte e ausência de proposta.
- [x] Implementar cálculo puro de crédito e excedente, metadados aditivos das propostas e proteção de blocos restantes; preservar swaps/extras e V1 sem contexto diário.
- [x] Mostrar excedente claramente no resumo, sem mudar meta/progresso reais; garantir calendário de hoje consistente e datas futuras recalculadas normalmente.
- [x] Testes de integração, revisão independente, suíte completa e QA em cópia mínima dos dados reais; validar preservação, registrar versão e integrar localmente sem publicação.

## Verificação — v0.25.1, 23/10/2026

A suíte completa final passou com **687 testes em153,64 segundos**, incluindo o baseline V1; um aviso intencional do teste de ZIP duplicado. A validação específica de excedentes, UI, trocas e dias por questões passou com39 casos. Detector estático sem apontamentos e whitespace conferido. Metadados de versão e política passaram para0.25.1/4.1; fórmulas de desempenho e parâmetros de aprendizagem não foram alterados.

A revisão independente encontrou captura congelada após corrigir um registro anterior e preservação de temas novos após ativar uma programação exclusiva de revisões. Foram corrigidos o total planejado acumulado e a compatibilidade com a agenda; regressões cobrem ambos os casos, além de troca manual, descanso e CAS de proposta obsoleta. Registrar uma proposta antiga não pode fazer parecer que ela foi apresentada antes de um estudo ocorrido em outra tela.

Na cópia mínima dos dados reais, um cenário explicitamente simulado em24/10 usou o bloco de Dacrioestenose de15 questões e registrou17. Os outros cinco blocos e a meta diária130 foram preservados, sem exceções no AppTest, mudança de perfil ou simulados. Esse estudo existiu apenas na cópia descartável; não representa realização do usuário. A cópia e os snapshots auxiliares foram removidos automaticamente. Nenhum arquivo de teste replicou backups.

O servidor local foi reiniciado e a tela Hoje confirmou o aviso de excedentes e a contagem real de108 questões. A auditoria das30 tabelas não encontrou remoção ou alteração de nenhuma linha anterior; apenas uma nova proposta diária foi acrescentada ao histórico. A conexão local respondeu normalmente. Propostas antigas incompatíveis não foram restauradas retroativamente.

Sem proposta anterior identificável não há dose original segura para comparar: o app mantém a contagem usual, em vez de inventar excedente. Propostas anteriores incompatíveis com uma nova configuração não são ressuscitadas. Versões antigas continuam no histórico. Não há migração de schema, alteração de resultados ou necessidade de restaurar o banco para reverter o código; o schema permanece12.
