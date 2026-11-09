# Atualização de dados sem Codex

Objetivo: atualizar o progresso do Planner e a árvore dos cards pessoais diretamente no app local, com descoberta na lateral, data de captura, leitura segura e comparação antes de aplicar.

Autorização: pedido explícito do usuário; AGENTS autoriza escolhas reversíveis sem novo ciclo de aprovação. Reutilizar parsers, armazenamento versionado e confirmações atuais. Evitar uma segunda plataforma ou acesso à conta Osler.

Decisões: nova rota Atualizar dados, com duas abas nativas e somente a selecionada calculada. Upload HTML/TXT ou HTML colado; ajuda de exportação recolhida. Data obrigatória até o dia de estudo atual. Planner mostra questões distintas, segurança, contato derivado e pendências; atualizar incidência é opcional e exige o conjunto de instituições. Uma atualização parcial preserva os temas ausentes. Cards requerem distinguir saldo pendente, inventário e nova passagem; pais/filhos não se somam. Comparar saldos e mostrar temas ausentes antes da confirmação. Originais e versões preservados, sem transformar importação em sessões de estudo.

Invariantes: parser não executa HTML; limite20MiB; rejeitar números inválidos e duplicatas; associação exata e única pelo caminho, sem nomes aproximados; campos desconhecidos ficam ausentes; data de captura não vira contato quando faltam dias sem contato; convicção acumulada não vira acerto em primeira tentativa; importação repetida idempotente; prévia não grava e aplicação recusa token desatualizado; nenhum dado ativo usado por testes.

- [x] Inspecionar leitores, originais e fluxos existentes.
- [x] Testes e suporte ao formato ThemeTitle/ThemePath da tabela real, mantendo o formato anterior.
- [x] Serviço de prévia/aplicação do progresso, persistência compatível e proteção de incidências quando só há progresso.
- [x] Prévia dos cards pelo serviço existente; reaproveitar as mesmas regras no fluxo novo. Criações posteriores à captura também entram no saldo previsto, corrigido após revisão independente.
- [x] UI integrada, com ajuda de exportação, comparação, histórico e confirmação/toast. Rascunhos entre abas preservados; fontes e datas alteradas exigem outra prévia.
- [x] Testar serviços e UI, renderizar em desktop/celular e documentar o caminho de uso. Oito capturas em1440/1366/768/390px e duas importações completas em cenário sintético. Suíte completa:1.102passaram, um pulado, aviso esperado de ZIP duplicado.

Prova: testes sintéticos de dados com zeros e ausências, datas, duplicação, exportação parcial, concorrência, separação estatística e filas de cards; amostra real lida apenas em modo leitura; navegação e importação em cópia descartável. Cálculos do plano usam os novos dados somente após a confirmação do usuário.
