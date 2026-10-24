# Revisões equilibradas — desenho e plano

> Execução inline com Superpowers:executing-plans/TDD. Usuário autorizou ajustar o método e dispensou ciclos de aprovação. Usar branch codex/revisoes-equilibradas, sem copiar o projeto/dados e sem publicar.

**Goal:** retirar a penalização excessiva por convicção e o piso indiscriminado de 20, preservando retenção, metas, versões, fontes e capacidade.
**Architecture:** estratégia explícita `review_strategy=balanced_v2` no perfil, padrão legado para arquivos antigos. Funções puras em `balanced_reviews.py` para evidência diária, intervalos, dose e coordenação. Wrappers mantêm o resultado exato de legacy_v1. Serviço monta prévia de 28 dias, valida token na transação e salva nova versão; parâmetros V1 não são alterados.
**Stack:** Python/Streamlit/SQLite/pytest. UI existente com Revenue-Centric Design/Impeccable.

## Abordagens e decisões

Reduzir só o piso resolveria a aparência, mantendo o reinício por convicção. Ajustar um modelo de memória por questão exigiria IDs e histórico que não temos. Escolha do implementador: política por tema transparente, baseada nos acertos informados e na incerteza, sem alegar calibração ou ótimo científico.

Acertos novos, mistos e repetidos permanecem separados. Por dia, novas têm precedência, depois mistas, depois repetidas sem vínculo. Lotes vinculados nunca provam domínio do tema. Sem acertos objetivos, preservar triagem documental e solicitar medição; segurança importada não vira acerto bruto.

Primeiro encontro suficiente e sem baixo rendimento: 7 dias por padrão, sem encurtamento automático pela incidência. Bons encontros realmente espaçados ampliam o intervalo continuamente usando a média Beta(1+acertos,1+erros), limitada pelos parâmetros e prazo. Resultados <70% encurtam; sinais críticos continuam protegidos. Um bloco abaixo de 95%, mas cujo intervalo de Wilson ainda inclui 95%, não é classificado como déficit confirmado. Incidência segue no score e na dose, sem fingir que altera velocidade de esquecimento.

Dose contínua: mínimo configurado + lacuna do acerto para a meta + incerteza + incidência. Não impor 20 a todo resultado abaixo da meta. Diagnóstico sem medição e erros críticos preservam dose diagnóstica; manutenção exige dois encontros espaçados e amostra suficiente. Aproximações, blocos pequenos, repetição vinculada e passagem do tempo não criam domínio.

Coordenar datas do tema e de lote a até 2 dias de distância, dentro do limite máximo de contato, sem adiar erros urgentes, vésperas protegidas ou o vencimento dos lotes. Essa janela é convenção operacional, não intervalo ótimo comprovado. Lotes pequenos têm tamanho real, sem complemento automático obrigatório; bloco combinado identifica lotes e prática representativa separadamente, contando cada tentativa uma vez. Confiança continua exigida para baixar cada lote.

## Tasks e testes

- [x] RED/GREEN: estratégia e compatibilidade; 17/19 com 15 convictas e meta95 deixa de receber piso20; baixa confiança não imita erro; erro objetivo mantém reforço; faltas de dados não viram zero.
- [x] RED/GREEN: crescimento com resultados espaçados, sem salto por repetição precoce, proteção de fontes/amostras/erros; passado e máximos; dose sobe com piora e estagnação, manutenção condicionada.
- [x] RED/GREEN: coordenação sem antecipar lotes; conhecidos não apagados; planejamento/registro de lote + complemento sem duplicação, orçamento e simulados respeitados.
- [x] Prévia/aplicar/desfazer por nova versão do perfil; compare doses/intervalos/prioridades/datas e plano de hoje, token/CAS. UI com explicação no feedback e opção avançada para estratégia.
- [x] Suíte completa e baseline V1 intacto; revisão independente, QA em cópia mínima real, backup e prévia antes de ativar o ajuste autorizado; navegador, versão e documentação. Preservar todos os registros ativos e simulados. 672 testes aprovados, detector sem achados, perfil12 ativo.

## Evidência e limites

Cepeda et al. 2008 (doi:10.1111/j.1467-9280.2008.02209.x): relação entre espaçamento e prazo de retenção. Butler et al. 2008 (doi:10.1037/0278-7393.34.4.918): feedback beneficia acertos de baixa confiança; não os transforma em erros. Larsen et al. 2009 (doi:10.1111/j.1365-2923.2009.03518.x): testes espaçados com feedback em educação médica. Pavlik/Anderson 2008 (doi:10.1037/1076-898X.14.2.101): adaptação dinâmica por item; sem dados individuais não reproduzimos seu modelo. Nossos coeficientes e limites são heurísticos e precisam de validação longitudinal. Wilson/Beta descrevem incerteza sob hipóteses de amostragem; questões selecionadas por tema não estimam aprovação nem nota de prova.

Ruling: falhas objetivas em lotes vinculados impedem domínio/manutenção enquanto a cadeia estiver sem recuperação, sem somar suas tentativas ao posterior de inéditas — protege dificuldades reais sem equiparar baixa convicção a erro.

Ruling: se faltar capacidade para o bloco combinado, cumprir primeiro o retorno conhecido, com crédito para o complemento realizado a até dois dias — não inflar o lote, não fingir medição geral e não cobrar novamente o total no dia seguinte.

Ruling: preservar o ajuste diário existente de 130 e a troca Dacrioestenose → Tamponamento; meta padrão continua120. A prévia real mantém o bloco atual de15 questões. A aplicação cria perfil12 e auditoria atômica após backup, sem estudos fictícios.
