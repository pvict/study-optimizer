# Confirmações e feedback de gravação

## Desenho
O app é Streamlit, sem frontend React/shadcn. Usar st.dialog e st.toast nativos, integrados à direção Apple. Não instalar uma árvore React sem uso. Não alterar serviços, regras ou persistência.

Camada explícita de botões de confirmação: solicitações de gravação abrem diálogo; Cancelar/Escape não gravam; Confirmar libera uma única submissão do mesmo formulário, conferindo contexto e valores. Callback de ação só executa depois de confirmar. Tokens/revisões dos serviços continuam válidos. Preview, navegação e edição de campos não abrem confirmação.

Toasts são agendados somente depois que uma chamada de gravação retorna com sucesso. Erros mantêm as mensagens existentes, sem toast falso. Fluxos de sucesso existentes preservados.

## Plano
- [x] Implementar controlador pequeno e testes de cancelamento, confirmação única, valores alterados e falha.
- [x] Aplicar explicitamente a registros, importações, configurações, remanejamentos, desfazer e restauração.
- [x] Mostrar resumo concreto de registros e alterações importantes, com Cancelar e ação clara.
- [x] Validar fluxos reais em testes e navegador: teclado, celular, cancelamento e toast após gravar.

Autorização de execução direta conforme AGENTS.md. Skills Apple Design/Frontend/Revenue para apresentação; Superpowers para implementação/testes; Caveman para leituras compactas. Dados sintéticos isolados para validação.

## Entrega e validação

O controlador explícito `osler/action_feedback.py` concentra solicitação, cancelamento, aprovação única e notificação. Mantém as chaves originais dos widgets. Não intercepta globalmente o Streamlit nem muda serviços. A confirmação verifica valores estruturados, base, prazo de 10 minutos e dia de estudo. Callbacks conservam os argumentos e versões da tela original; validações dos serviços continuam obrigatórias. SQLite de leitura usa fechamento explícito para não bloquear arquivos no Windows.

Resumos de resultados mostram tema, data e contagens; mudanças de rotina e rodízio mostram seu alcance. Restauração e troca de pasta identificam origem e preservação. Cancelar, X e Escape não gravam. Erros não geram toast de sucesso; a restauração só avisa sucesso depois de ativar a pasta. Navegação, busca, prévias e downloads continuam diretos.

Provas reproduzíveis:

- `tests/test_action_feedback.py`: seis casos de cancelamento, gravação única, erro, mudança de formulário/base, callback e falha de ativação de pasta.
- Testes existentes de UI passaram a incluir a confirmação de forma explícita, sem autoaprovação global.
- `scripts/check_confirmation_ui.py`: Edge em 1440, 768 e 390px; Cancelar/Escape preservam dados; Tab fica no diálogo; confirmação grava uma vez; toast aparece após salvar; recarregar não duplica.
- Capturas e resultado sintético local: `evidencias/confirmacoes/`. Base temporária removida automaticamente; dados ativos não usados na QA.

Os componentes são equivalentes nativos do Streamlit, e não os pacotes React do shadcn. O teste móvel é por viewport emulado, não por aparelho físico.

Resultado em 29/10/2026: suíte completa com 997 testes aprovados, um ignorado por indisponibilidade de symlink no Windows e um aviso. Depois da última proteção da troca de pasta, conjunto dirigido de confirmação/revisão semanal/complemento/erros com 12 aprovados, incluindo os seis casos do controlador. QA em navegador aprovada nos três tamanhos. Saúde do app local: HTTP200.
