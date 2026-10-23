# Registro estruturado de erros

## Fonte e hipótese

A revisão [The Use of Feedback in Improving the Knowledge, Attitudes and Skills of Medical Students (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8651958/) encontrou resultados favoráveis ao feedback na aprendizagem de estudantes de medicina, com variação entre intervenções e resultados. Isso apoia estudar os erros; não valida um algoritmo pessoal de aprovação.

Hipótese do produto: anotar o conceito que faltou e a causa percebida ajuda a escolher o que retomar. O registro é opcional após salvar o bloco, com tema já preenchido, causa e frase curta. Aplica a redução de esforço percebido da referência [Checkout & Forms, Revenue-Centric Design](https://github.com/heliocosta-dev/revenue-centric-design): pedir apenas o dado útil naquele momento, deixando a tarefa principal concluída.

## Regra adotada

- Um erro marcado como crítico pelo usuário é sinal adverso enquanto estiver aberto, independentemente da idade.
- Dois erros distintos, abertos, com a mesma causa no mesmo caminho normalizado e idade de até 30 dias são sinal de recorrência. Duas versões do mesmo erro contam como um único erro.
- O sinal pede prioridade alta e bloqueia sugestão de reduzir flashcards. Não cria urgência, não altera o espaçamento e não aumenta o denominador dos blocos de questões.
- Resolver ou desconsiderar cria evento, preservando conceito, origem, versões e auditoria. Correção também cria nova versão; pode reabrir um registro resolvido.
- A consulta por data usa o estado corrigido mais recente de cada chave e filtra a data declarada do erro, como as sessões de estudo. Não é uma reconstrução do que a tela mostrava num timestamp passado. Resoluções atuais não voltam a gerar sinal em consultas antigas.

## Limites

As seis causas são autorrelato, não diagnóstico validado. O limiar de dois registros em 30 dias é uma escolha conservadora do produto, não um resultado estabelecido pela revisão. Marcar como resolvido significa que o usuário decidiu encerrar aquela anotação; não comprova domínio. A interface não mede automaticamente o tempo de registro e a meta de até 15 segundos ainda exige avaliação com uso real.

São guardados somente os conceitos escritos pelo usuário, limitados a 280 caracteres, sem importar enunciados. A origem pode apontar para um bloco local do mesmo tema. Catálogo presente exige um tema específico e único; o histórico continua acessível se o tema deixar de constar nos PDFs atuais. A exportação CSV contém todas as versões e protege células contra fórmulas.

Testes usam somente bancos sintéticos temporários. Não há acesso à plataforma, importação de respostas remotas ou aplicação automática de suspensão/reativação.
