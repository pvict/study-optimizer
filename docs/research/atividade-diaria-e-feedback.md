# Atividade do dia e retorno após registrar um bloco

## Hoje

A área de blocos tem duas abas nativas: **Para fazer** e **Feito hoje**. A segunda
mostra cada lançamento ativo daquele dia, tema específico, modalidade, quantidade,
acertos e convicção, com contagens e percentuais. **Corrigir** abre o mesmo registro
com sua versão atual; salvar uma correção preserva a anterior no histórico.

Somente tentativas em blocos compõem a quantidade realizada. Contatos sem questões
aparecem identificados, com quantidade zero. Totais acumulados anteriores e PDFs
não entram no progresso do dia. Sessões desconsideradas ou de outra data não aparecem;
duas sessões reais do mesmo tema são mantidas separadas. Repetições são tentativas,
não novas questões distintas.

## Registro concluído

O recibo mantém a identidade da sessão salva e consulta a versão ativa. Exibe:

- Data e modalidade do lançamento.
- Acerto no bloco e acerto com convicção, ambos sobre todas as questões do bloco.
- Erros e acertos sem convicção quando as contagens são conhecidas.
- Uma orientação curta de reforço, medição ou manutenção, considerando a meta do tema.
- Quantidade do próximo bloco de referência e data do contato indicado pelo planejador.
- Quantidade e data do lote de respostas sem convicção daquele registro, separadas
  do contato completo do tema. Revisões parciais mostram o lote residual da sessão filha.

Um campo de convicção vazio permanece desconhecido, sem virar zero ou criar uma fila
fictícia. Percentuais aproximados não são convertidos em contagens inteiras de acertos.
Um bloco bom não declara domínio; em repetidas, o resultado não estima acerto em novas.
O próximo contato é uma indicação; as vagas continuam no Calendário. Após a prova,
o recibo orienta conferir a data em vez de inventar uma vaga futura.

O recibo também trata contatos sem questões e acumulados anteriores com suas próprias
mensagens. Um registro desconsiderado deixa de produzir feedback de desempenho.
Voltar à página ou atualizar o recibo não grava outra sessão.

## Verificação

Testes de domínio e de interface cobrem o ciclo salvar → feedback → voltar a Hoje →
corrigir, além de desconhecidos, aproximados, datas e lotes vinculados. A conferência
dos dados existentes usa uma cópia local; não adiciona estudos demonstrativos ao banco original.
