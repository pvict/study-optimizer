# Bancos pequenos, temas novos e recuperação

Implementado na versão 0.30.0. O nome do arquivo mantém a referência à proposta v0.15.0. A versão anterior do app era 0.29.0.

## Agenda

O mínimo da rotina (`min_block`, 10 por padrão) define o acervo necessário para um bloco automático. Um acervo abaixo desse mínimo aparece em Temas com **Falta complemento**. O plano não ocupa uma vaga de tema com o fragmento. O usuário pode lançar um estudo ou adicionar um bloco manualmente. Compromissos específicos de uma prova ou troca feita pelo usuário mantêm seu tratamento próprio. Reservas gerais antigas abaixo do mínimo ficam no histórico e deixam de ocupar a agenda.

Recuperação usa contatos documentados. Uma proposta salva e não feita antes de qualquer contato continua sem realização. Uma revisão vencida ou um plano perdido depois de contato comprovado pode entrar na recuperação.

## Evidência e alcance do acervo

Uma amostra abaixo do mínimo continua visível no registro e pode sugerir conferir os erros. Ela não antecipa para três dias nem cria urgência pelo acerto ou pela convicção. Em um tema sem encontro anterior suficiente, a referência de diagnóstico é de sete dias no perfil padrão. Datas de prova, retornos vinculados e erros explicitamente críticos seguem as proteções da rotina. Acerto provisório em PDF continua identificado como evidência de outra origem, sem virar contato datado.

Para bancos menores que duas vezes o mínimo, a trajetória limita a projeção automática a três ciclos do banco (`MAX_BANK_CYCLES = 3`). As etapas seguintes continuam condicionais. O limite preserva extras, retornos vinculados e compromissos já assumidos. A disponibilidade de questões complementares muda o que é possível medir. Repetir o mesmo conjunto não mede aprendizado novo.

## Incidência e classificação

O Planner separa a incidência global da incidência das instituições selecionadas. A importação de incidência identifica a coluna usada, conserva o rótulo nativo como contexto e usa a contagem na alocação. No rateio de uma linha de pai, os bancos dos filhos determinam suas parcelas da massa residual, sem duplicação. Com todos os bancos ausentes ou zerados, a divisão é igual.

Um subtema sem evidência própria pode ser **Continuação de tema** quando há estudo no mesmo nó de incidência. O estágio e a cota mudam, mas nenhum contato ou desempenho dos irmãos é atribuído ao subtema. Novos elegíveis são ordenados pela incidência do nó nas fontes institucionais ativas, depois pelo volume do banco e pelo caminho. Quando há mais de uma fonte comparável, os pesos institucionais normalizam a contribuição de cada tabela.

Fragmentos elegíveis do mesmo tema podem formar **Subtemas menores** quando o acervo conjunto permite um bloco mínimo. Os membros continuam pesquisáveis e seus registros anteriores ficam preservados. O resultado conjunto guarda a composição confirmada, sem atribuir acerto individual a cada membro. Se a composição mudar durante o registro, confira a seleção e confirme de novo.

Os valores de mínimo, intervalo de diagnóstico, ordem e três ciclos são escolhas de engenharia. O app não tem calibração pessoal que determine uma dose ideal, nem garantia de 90% de acertos. A alteração lê os registros existentes e não migra o esquema.

## Verificação de regressões

- `test_small_bank_agenda` e `test_small_bank_review_policy` cobrem vagas, histórico, amostras, ordenação e ciclos, com uma inclusão manual depois do teto.
- `test_incidence_planning`, `test_guide` e `test_fragment_groups` cobrem coluna institucional, rateio, continuação, composição, registro e histórico.
- Atualizamos os testes de cobertura, piso de novos e prioridades que exigiam um fragmento automático. As verificações de recuperação e troca usam contato real no cenário. O teste de um lote curto ligado a uma revisão mantém o retorno de três dias com uma origem de amostra suficiente. A trajetória separa o acervo disponível da dose total buscada.
- A suíte completa passou com 1.279 testes e 9 ignorados pelo ambiente. Após as proteções finais de concorrência, datas de contato e composição dos agrupamentos, 104 testes focados e 5 subtestes passaram. O HTML pessoal foi lido localmente para conferir a coluna e as contagens. Ele não faz parte dos testes nem da versão.
