# Explicações opcionais

Refinamento da interface existente, sem mudar resultados, metas, datas, prioridades ou gravações. Pedido do usuário: retirar a prosa auxiliar da leitura diária e permitir consultá-la quando quiser.

| Região | Classe Visant | Variável atendida | Persuasão |
| --- | --- | --- | --- |
| Hoje, atenção, calendário, temas, evolução e flashcards | B — trabalho | Tempo para localizar e executar o próximo estudo | Nenhuma |
| Formulário e resultado de registro | C — confiança | Compreensão das contagens e correção do registro | Nenhuma |
| Ajustes, arquivos e simulados | C — confiança | Controle de dados e mudanças na agenda | Nenhuma |

Decisão: uma opção de sessão “Mostrar explicações” na barra lateral controla orientações auxiliares das telas. Desligada por padrão. Detalhes já recolhidos continuam acessíveis independentemente da opção. No feedback do registro, contagens, fonte e interpretação ficam em “Detalhes do resultado e da revisão”; métricas e próximo contato ficam expostos. Avisos de erro, consequências de gravações e confirmações não dependem da opção.

Alternativas: esconder todas as legendas por CSS removeria também dados e acessibilidade; um acordeão por frase manteria a poluição. Ambos descartados. Um helper explícito de apresentação permite selecionar a prosa opcional sem interceptar componentes nem mudar o domínio.

Skills: Superpowers (plano, testes e verificação), Find Skills (busca; capacidades necessárias já instaladas), Revenue-Centric Design (remover informação para dar direção), Impeccable distill/Operate, Taste app screens, Apple e Frontend Design (preservar identidade e controles nativos), Visant Frontend/Killer declutter/Copy/Refine e Web Design Guidelines. Motion preserva os controles nativos e movimento reduzido; branding, aquisição e preflight de projeto novo não se aplicam a este refinamento. Caveman foi usado para transportar referências; não se presume economia quando retorna conteúdo sem compressão.

Plano de execução:
- [x] Provar com testes o padrão recolhido, a opção de sessão e a preservação dos dados.
- [x] Reorganizar o feedback e marcar prosa auxiliar nas rotas existentes.
- [x] Verificar registro, navegação, confirmações e renderização em computador e celular com dados sintéticos.

Critério: o usuário consegue ler o resultado e encontrar a próxima ação sem atravessar explicações; toda informação técnica continua disponível. Sem novas dependências, migrações ou alterações nos dados pessoais.

Validação: 101 testes direcionados passaram; após reduzir também as legendas de Hoje, os 17 testes afetados passaram novamente. QA real com dados sintéticos em 1440, 768 e 390 px: ajuda opt-in, detalhes fechados, teclado, gravação única e ausência de rolagem horizontal da página. Evidências: `evidencias/explicacoes-opcionais/resultado.json` e capturas correspondentes. A base temporária foi removida. O detector Visant não reconhece Python (0 arquivos de interface); seu resultado vazio não foi tratado como aprovação visual.
