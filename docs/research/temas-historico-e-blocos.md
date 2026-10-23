# Temas: histórico importado e blocos recentes

A visão de histórico exibia apenas a quantidade e a segurança acumuladas no retrato
importado da Osler (ou no PDF quando não havia retrato). Último contato, prioridade
e estado já incorporavam os blocos locais. Por isso um tema estudado recentemente
podia aparecer com zero em “Questões realizadas”: essa coluna descrevia uma fonte
antiga, enquanto as outras colunas descreviam o estado atual.

A tabela e a lista mostram as contagens dos dois conjuntos lado a lado:

- **No app:** respostas dos blocos registrados, acertos e convicção com os respectivos
  denominadores. Nesta visão, os totais incluem todo o período.
- **No histórico:** questões distintas e segurança acumulada no retrato importado,
  com a fonte e a data. Um novo lançamento não reescreve esse retrato.

As bases não são somadas: podem conter as mesmas questões e representam métricas
diferentes. A visão **Blocos registrados no app** mantém os filtros de dia, semana,
mês, todo o período e modalidade. Correções usam apenas a versão ativa da sessão.
Zero de convicção informado continua diferente de convicção desconhecida.

## Uma convicção principal na apresentação

A tabela e a lista mostram uma única convicção principal, identificando a fonte,
a data (ou janela dos blocos) e a quantidade de questões que sustenta o percentual.
Na visão de histórico, escolhemos entre as medições existentes pela data mais
recente. Quando têm a mesma data, mostramos o app com indicação do empate, sem
presumir qual ocorreu primeiro dentro do dia. Sem convicção local, o retrato Osler
pode ser usado; percentual de acerto do PDF não substitui convicção desconhecida.

Na visão de blocos, somente os registros do período e da modalidade escolhidos
alimentam essa exibição. Um retrato importado não preenche artificialmente um
período sem convicção informada. Os valores originais das duas fontes ficam em
**Ver fontes e medições originais**. O CSV da tabela inclui a medição escolhida e
sua base. Nenhuma média entre as fontes é calculada.

Essa seleção usa os percentuais descritivos já existentes, sem recalcular o
planejador, seus posteriors, domínio, prioridades, doses ou intervalos. O módulo de
apresentação retorna cópias das linhas; os dados que alimentam o modelo não mudam.

A alteração é de apresentação. Não muda registros, desempenho calculado, política
de revisão, prioridades ou arquivos importados. Os testes verificam o caso de um
retrato com zero seguido de17 respostas locais, sem alterar o denominador importado.
