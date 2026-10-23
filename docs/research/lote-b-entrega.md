# Lote B — registro da entrega

Proposta: `docs/roadmap/lote-B-dados-novos.md`. Base anterior: commit `566e1d9`, 495 testes passando. Implementação na branch `codex/lote-b-dados-novos`, sem publicação remota.

- B1: erros com seis causas, anotação curta opcional após salvar, erros abertos por tema, resolução, histórico e CSV. Erro crítico ou causa recorrente em 30 dias acrescenta prioridade alta e impede redução de flashcards.
- B2: simulados versionados com resultados opcionais por área/tema, evolução datada, condições e comparação documental de corte. Conversão explícita de inéditas por tema, idempotente; retirar conversão antes de corrigir. Cadência opcional e dia feito por simulado com prévia e desfazer.
- B3: provas/inscrições no calendário, pesos ligados à prova, aviso de aproximação e revisão final com prévia, aplicar, descanso na véspera e desfazer persistente.
- Schema 11: tabelas aditivas, validação de backup incluindo filhos, roundtrip e versões preservadas. Migrações nunca reduzem versão.

## Decisões reversíveis

- Manter a versão pública 0.19.0 já existente, em vez de retroceder pelas versões intermediárias propostas pelo documento. O conjunto é identificado por lote B/schema 11.
- Erros ficam em Temas → Erros abertos; Simulados é uma aba principal. Nenhum campo obrigatório foi acrescentado ao registro de bloco.
- Janela final admite 2–14 dias; sugere 7–14. Cada tema entra uma vez na proposta, e novos resultados orientam os próximos encontros.
- Programações especiais têm prioridade sobre recuperação/prevenção comuns; desfazer libera as datas novamente. Desfazer permanece disponível mesmo se a prova ou o simulado de origem forem desconsiderados.
- Após conversão em blocos, corrigir/desconsiderar o simulado exige retirada explícita daqueles blocos, preservando correções manuais e revisões dependentes.

## Preservação e reversão

Backup schema 10 criado antes de abrir a versão nova, em `data/backups/` (5,83 MB). Os dados pessoais não são incluídos em commits. Para voltar ao código anterior, restaure esse backup em outra pasta pela função de restauração e use o código anterior. Não reduza `user_version` manualmente. As programações temporárias podem ser desfeitas dentro do próprio aplicativo, sem restaurar backup.

Os tempos de 15 segundos para erro e um minuto para simulado são metas de usabilidade; não foram medidos com o usuário. A avaliação de toque em celular físico continua pendente. Não foram criados estudos, erros ou simulados de demonstração nos dados ativos, nem iniciadas tarefas do lote C.

## Verificação

- Suíte final: 563 testes passaram, com um aviso esperado do teste de ZIP duplicado. Inclui AppTest, versões/CAS, conversão idempotente, sinal adverso, backup/restauração e revisão final.
- Revisão independente encontrou três conflitos de integração: recuperação comum sobre a véspera protegida, desfazer de simulado dependente da sessão e abatimento duplo de estudo prévio na reserva final. Todos receberam regressões que falharam antes da correção e passaram depois.
- Comparação com o backup: todas as linhas anteriores preservadas; 57 arquivos de origem/exportação com hash conferido; quatro tabelas novas vazias nos dados reais. Schema ativo 11.
- Navegador local: Hoje manteve 120 questões em seis temas; Simulados e Temas → Erros abertos abriram sem dados demonstrativos. Inspeção visual na largura disponível de 614 px; campos empilhados e navegação visível. Não equivale a teste de toque ou cobertura de todos os aparelhos.
- Detector das novas telas sem apontamentos. A folha de estilos compartilhada contém dois apontamentos anteriores (sublinhado de aba e tamanho tipográfico); não foram introduzidos por este lote.
