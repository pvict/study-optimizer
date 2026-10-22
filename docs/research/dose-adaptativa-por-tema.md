# Quantidade de questões por tema: recomendação do próximo bloco

A antiga trajetória copiava a dose e o intervalo atuais até a prova. Por exemplo,
23 questões em 81 encontros viravam 1.863 “recomendadas”. Esse produto aritmético
não estima uma necessidade individual validada. Ele foi retirado da trajetória
individual, da tabela geral e das exportações de etapas.

## O que muda no uso

- O próximo bloco tem uma referência baseada nos dados disponíveis.
- Revisões seguintes aparecem como **A recalcular**, sem datas ou doses inventadas.
  As quatro linhas seguintes ilustram a continuidade, não um limite de revisões.
- Registrar ou corrigir resultados recalcula a dose e o intervalo reais. Os dados
  originais, versões dos resultados, lotes de erros e planos guardados são preservados.
- O Calendário ainda estima vagas futuras com os dados atuais, respeitando carga,
  distribuição, banco e agenda. Contatos previstos não geram evidência de sucesso.
- Evolução mantém seus cenários explicitamente condicionais de espaçamento. Não
  presume acertos futuros para reduzir a dose. Uma simulação de capacidade não é
  uma prescrição do total de questões necessário para aprender.

## Política do aplicativo (heurística, não dose científica validada)

O ponto de partida continua combinando mínimo por bloco, distância da meta,
incerteza descritiva da medida disponível e incidência relativa. Para um mínimo
`m`, lacuna relativa `g`, incerteza normalizada `u` e incidência normalizada `h`,
usa-se `ceil(m + 10g + 5u + 5h)`. Diagnóstico sem medição suficiente mantém piso
de 20 tentativas, respeitando o mínimo configurado. Segurança Osler atual pode
orientar a triagem inicial, sem virar uma amostra de acertos de primeira tentativa.

A manutenção menor exige dois dias suficientes com convicção na meta, separados
por pelo menos três dias. Cada dia deve somar ao menos o mínimo configurado e ter
convicção informada para todo o bloco. Agregação diária evita contar duas sessões
no mesmo dia como evidências espaçadas. Dias com medição incompleta interrompem
a sequência; blocos pequenos e revisões de lotes não desbloqueiam manutenção.

A evidência não pode ficar antiga: o prazo é o menor entre a janela recente e
duas vezes o intervalo atual do tema. Um afastamento maior entre encontros também
interrompe a sequência. Passar o tempo, sozinho, não reduz a dose. Esta escolha
de prazo, assim como o mínimo de dois dias/três dias, é uma regra conservadora do
produto, sem alegação de ótimo universal.

Na manutenção, a referência é `m + ceil(3h)`. Resultados adversos recentes por
modalidade, convicção observada abaixo da meta, erro em bloco pequeno ou lote
posterior, sinais manuais de erro ou medição antiga impedem essa redução. Reforço
ou nova avaliação após afastamento usa pelo menos 20 tentativas. Uma pendência
vencida impede o desbloqueio da manutenção. O intervalo continua sendo calculado
separadamente pela política de espaçamento real já existente.

O banco limita a parte disponível. Bancos abaixo do mínimo continuam indicando o
complemento de outra fonte para o mesmo tema específico. Revisão de um lote de
erros tem data e quantidade próprias; a trajetória usa a dose, data e complemento
da revisão completa do tema. Na divisão fixa, o alocador pode ampliar o bloco para
preencher a meta diária; isso é informado, não apresentado como necessidade científica.

Acertos e convicção em repetidas continuam separados do desempenho em questões
novas. Uma manutenção menor não declara domínio, aprendizagem de todo o conteúdo
ou uma taxa esperada de acerto na prova. Sem identificação dos itens e conceitos,
o aplicativo não mede a representatividade da amostra nem calibra esquecimento pessoal.

## Evidências e limites de transferência

- [Rawson e Dunlosky (2011)](https://pubmed.ncbi.nlm.nih.gov/21707204/): recuperação
  até critérios de sucesso e reaprendizagem espaçada podem combinar durabilidade e
  eficiência. O estudo não fornece uma dose universal de questões clínicas por tema.
- [Larsen e colaboradores (2009)](https://pubmed.ncbi.nlm.nih.gov/19930508/): ensaio
  em educação médica sustenta testes repetidos com feedback para retenção de longo prazo.
- [Cepeda e colaboradores (2008)](https://digitalcommons.usf.edu/psy_facpub/1766/):
  o espaçamento útil depende do horizonte de retenção.
- [Karpicke e Bauernschmidt (2011)](https://pubmed.ncbi.nlm.nih.gov/21574747/):
  espaçamento total importa; não há superioridade geral de uma única sequência
  relativa de intervalos no paradigma estudado.

Os valores numéricos acima são escolhas de implementação passíveis de revisão com
histórico real. Não são uma fórmula validada para alcançar 90%, nem probabilidade
ou garantia de aprovação.

## Validação

Testes cobrem manutenção após sucesso espaçado, retorno ao reforço por falhas,
afastamento, dias próximos/incompletos, blocos pequenos, lotes, separação entre
questões novas e repetidas, banco pequeno, dose no alocador, datas de início e fim,
etapas futuras desconhecidas, tabela e exportação. Tudo roda com dados de teste;
nenhum resultado pessoal é criado para demonstrar melhora.
