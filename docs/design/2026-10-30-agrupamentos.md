# Agrupamentos e incidência hierárquica

## O que muda
Menu Agrupamentos: Osler (padrão), Balanceado automático e seleção manual. A fronteira alternativa alimenta hoje, calendário, próximas revisões e evolução através do mesmo overview. As fontes, os estudos e as estatísticas individuais não são reescritos. Nenhuma opção foi aplicada à base ativa durante o desenvolvimento.

## Critérios e limites
- Categoria com no mínimo três níveis hierárquicos e 2–12 unidades filhas. Nunca uma grande área/especialidade inteira.
- Cada filho com incidência de pelo menos um bloco mínimo (atualmente 10 questões na fonte institucional) impede agrupar o pai. Esse limiar é operacional, não um teste de significância nem uma constante de aprendizagem.
- Lacunas da fonte não impedem a recomendação automática quando os demais critérios são atendidos (ajuste autorizado pelo usuário). Dados ausentes permanecem desconhecidos; somas parciais continuam limites inferiores, não zero imputado.
- Preferência pelas categorias mais específicas; seleção sem pai/filho simultâneos. Subárvores completas apenas: não se mistura um registro do pai com um subconjunto arbitrário dos filhos.
- Se um irmão importante impede agrupar o pai, categorias internas menores ainda podem ser candidatas. Não são criados grupos virtuais de irmãos restantes sob um nome que também inclui o irmão excluído.
- Conteúdo residual próprio, contagens contraditórias, retornos vinculados de filhos e agendamentos explícitos impedem agrupar essa categoria. As justificativas permanecem visíveis na lista completa.

## Aritmética
Dentro de cada contexto de instituição/período, usa-se a contagem inclusiva do pai, quando disponível. Caso contrário, somam-se somente raízes descendentes disjuntas: nunca pai + filhos. Essa soma é um limite inferior quando há filhos sem informação. Fontes percentuais sem denominador comum não geram recomendações. Conjuntos institucionais sobrepostos não são somados. Os contextos seguem a seleção do algoritmo existente.

O número de questões do acervo é diferente da incidência institucional. Não é usado como substituto desta. A comparação não estima a probabilidade de aprovação nem a chance exata de cobrança futura.

## Evidência individual
Blocos de filhos não são tratados como bloco conjunto completo, nem transferem seu último contato aos irmãos. Antes do primeiro bloco conjunto, a referência temporal é conservadora. Um bloco conjunto é guardado na categoria, sem inventar uma distribuição de acertos entre filhos. A ausência de acertos por filho continua ausência. Estatísticas individuais ficam disponíveis na tabela original; a próxima oportunidade conjunta vem identificada como tal.

## Calendário e reversão
Prévia reproduzível até a prova, limitada à janela máxima já suportada (548 dias), sem pressupor acertos futuros. Contém todos os dias antes/depois, blocos, quantidades, integrantes, dias alterados e próximas oportunidades por tema. Download JSON completo e CSV das sugestões.

Antes da aplicação: revalidar token/data/conteúdo e gerar backup consistente com banco e arquivos originais/exportados. Perfil e auditoria são salvos numa transação com proteção contra concorrência. O histórico guarda calendários antes/depois e caminho do backup. Reversão gera nova prévia da configuração anterior preservando estudos posteriores; a agenda antiga exata fica arquivada. Para recuperar o estado integral daquele momento, usar a restauração existente em pasta nova. Retornos já criados por grupos são preservados inclusive ao voltar ao modo Osler.

Código anterior salvo em data/backups/codigo_antes_agrupamentos_20261030T110154.zip. Dados anteriores em data/backups/osler_20261030T140154Z_44a7534a4cede35b.zip. Os backups não são enviados ao GitHub.

## Fundamentação
Prática intercalada pode ajudar discriminação e transferência; espaçamento e recuperação ativa continuam necessários. O benefício depende da tarefa e da semelhança das categorias. Estes estudos não validam um tamanho específico de grupo para residência médica:
- Samani & Pan (2021), estudo experimental em física: https://www.nature.com/articles/s41539-021-00110-x
- Carvalho & Goldstone (2014), estudo experimental de categorias e limites da intercalação: https://pmc.ncbi.nlm.nih.gov/articles/PMC4141442/

Não há calibração longitudinal individual que autorize chamar estes limites de ótimo estatístico. A política é conservadora, explícita e reversível. A descoberta de skills não encontrou ferramenta mais apropriada que o código estatístico e a hierarquia já existentes; nenhuma dependência foi adicionada.
