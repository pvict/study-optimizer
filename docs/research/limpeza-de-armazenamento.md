# Limpeza local em23/10/2026

Após a correção de apresentação dos resultados por tema e a aprovação de488testes,
foram removidos45diretórios descartáveis: cópias/restaurações de teste, checkouts de
verificação e caches do código e dos testes. Muitas cópias antigas também continham
duplicações dos backups, desnecessárias após a validação.

Foram removidos **3.709.943.493 bytes**, aproximadamente **3,71 GB** (3,46 GiB).
Todos os caminhos foram resolvidos e conferidos dentro do projeto; pastas de dados
ativos, worktrees registrados e diretórios vinculados a processos foram protegidos.
Links e junções impediriam a execução sem revisão.

Os **102 arquivos da pasta de dados ativos** foram comparados por SHA-256 antes e
depois da remoção, sem alterações. Originais importados, histórico, backups originais,
ambiente de execução, código, Git, documentação e documentos finais foram preservados.
Relatórios pequenos de validação permaneceram disponíveis. Não houve limpeza fora
da pasta do projeto.

O aplicativo foi reiniciado na porta8501. Logs correntes e os manifestos da limpeza
ficam em `tmp/runtime`. Caches necessários podem ser regenerados pelo Python.
A preferência de não acumular cópias de teste foi registrada em `AGENTS.md`.
