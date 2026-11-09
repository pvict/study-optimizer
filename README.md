# Osler Study Optimizer

Aplicativo local para organizar a preparação para residência médica: plano diário por quantidade de questões, acompanhamento de desempenho e revisões espaçadas por tema específico.

Também pode ser hospedado para acesso privado pelo celular com o PC desligado. A versão online usa armazenamento persistente no Supabase; a cópia local continua independente. [Configuração, backups e limites dos planos gratuitos](cloud/README.md).

O **dia de estudo vira às 04h, no horário de Brasília**: 22/10 inclui o período
de 22/10 às 04h até antes de 23/10 às 04h. Plano, registro padrão, calendário,
estatísticas e trocas usam esse mesmo dia. Datas já declaradas/importadas e horários
de auditoria permanecem intactos.

**Versão 0.29.0.** Interface em português, construída com Streamlit. Os resultados são informados pelo usuário ou importados de arquivos exportados manualmente; o aplicativo não acessa nem automatiza a plataforma Osler ou a FluidMed.

Em **Simulados → Treinos por área**, programe um ou dois treinos semanais por instituição, mova datas e registre resultados. As questões reservadas fazem parte da meta diária. O rodízio percorre as cinco grandes áreas e as instituições escolhidas; alterar frequência ou carga preserva os treinos já realizados.

Em **Simulados → Correção**, informe os temas errados agora ou depois de registrar o resultado. A quantidade de erros por tema é opcional. Escolha o dia e veja a distribuição antes de aplicar: os blocos respeitam a carga diária, com doses orientadas pela incidência disponível, pelo desempenho observado e pelos erros. Sem denominador, não se calcula um percentual de acerto por tema. Histórico, conversões e nota do simulado ficam preservados. [Método e limites](docs/research/treinos-e-correcao-de-simulados.md).

[Entrega do lote C: funções, validações, limites e reversão](docs/research/lote-c-entrega.md).

A interface Bento usa um menu lateral único, cards claros, ações visíveis e detalhes recolhidos. Hoje reúne o próximo bloco e o que já foi feito; Calendário distingue estudo registrado, hoje e previsão; Evolução abre pelo histórico real e mantém projeções em Cenários. Flashcards mostra decks e recomendações antes dos ajustes; Arquivos abre pela biblioteca e conserva as ferramentas técnicas em Avançado. Ajustes reúne Meta e rotina, Minhas provas e Instituições e incidências. O nome opcional é usado somente na sessão atual. [Entrega da fase 5, capturas e limites](docs/design/bento-fase5-entrega.md) · [Sistema de design](DESIGN.md).

## O que o aplicativo oferece

- **Cards criados nos blocos:** informe a quantidade ao registrar suas questões; a fila do tema acompanha edições e lançamentos desconsiderados, sem duplicar os cards já abrangidos por um novo HTML. Criar não conta como estudar e não muda sua carga diária. **Redução com dados atuais:** até três sugestões seletivas, com fontes datadas, temas protegidos e reavaliação em sete dias. [Funcionamento, critérios e limites](docs/research/reducao-atual-e-novos-cards.md).

- **Cards de erros acumulados:** decks inteiros por tema, com referência diária própria e até10% de margem, sem fragmentos para preencher a meta. Importação HTML sem duplicar pais e filhos, prioridade por tema específico, registros separados de cards diferentes e repetições e cenário dos próximos dias. Descansos e simulados são respeitados. [Funcionamento e limites](docs/research/cards-erros-recuperacao.md) · [Decks inteiros e complemento de Psiquiatria](docs/research/decks-inteiros-psiquiatria.md).

- **Simulados com datas flexíveis:** programe a primeira data e um intervalo; depois mova ou retire cada ocorrência separadamente. Calendário distingue programação e resultado; o dia reservado substitui os blocos normais, e a prévia mostra o remanejamento dentro da carga. [Regras, limites e histórico](docs/research/simulados-flexiveis.md).

- **Hoje:** abas Para fazer e Feito hoje, com blocos priorizados, resultados do dia e acesso à correção dos lançamentos. Após salvar, veja seu desempenho e os próximos passos do tema. [Fluxo e critérios](docs/research/atividade-diaria-e-feedback.md).
- **Questões além do bloco:** excedentes contam no total e no desempenho sem substituir os outros temas já propostos para hoje. A meta fica preservada e o resumo identifica o excedente. [Regras e limites](docs/research/excedentes-no-plano-diario.md).
- **Trocar tema:** escolha manual ou sugestão do mesmo tipo e prioridade semelhante; a prévia mostra a data reservada para o tema retirado, com opção de desfazer. [Funcionamento](docs/research/troca-de-temas.md).
- **Calendário:** Agenda, Semana e Mês; próximos contatos por tema, retornos conhecidos e revisões seguintes a recalcular após seus resultados. Recuperação e prevenção de pendências com comparação antes/depois e opção de desfazer. [Como interpretar a previsão](docs/research/calendario-proximos-contatos.md).
- **Rotina adaptativa:** referência de novos/revisões com ajuste à demanda e à capacidade de repetir nos próximos14dias; comparação com divisão fixa, custo em cobertura e riscos residuais visíveis. Doses não são infladas para preencher a meta. O modo fixo continua disponível.
- **Retomadas do histórico:** sinais de dificuldade preservados e prioridade crescente pelo tempo de espera. O modo adaptativo abre espaço para contatos antigos, com pressão futura explícita e sem descontar reservas duas vezes. A carga pode impedir o intervalo desejado para todos os temas. [Correção, comparação global e limites da política4.5](docs/research/prioridade-retomadas-4-5.md).
- **Evolução:** jornada por semanas, meses e fim da preparação, com respostas, cobertura e pontos de atenção. Compare intervalos atuais com avanço condicional das revisões ao atingir a meta; cada cenário respeita a carga e fica separado dos resultados reais. [Hipóteses e limites](docs/research/evolucao-espacamento-condicional.md).
- **Temas:** resultados registrados no app ao lado do histórico importado, com fontes separadas; filtros de situação e período, tabela ou lista paginada e exportação. A coluna Próxima revisão mostra a vaga prevista no calendário para o tema pesquisado, separada da data devida. [Entenda as contagens](docs/research/temas-historico-e-blocos.md).
- **Revisões por tema:** dose do próximo bloco ajustada aos resultados reais; manutenção menor após bons encontros espaçados, reforço após dificuldades e revisões seguintes a recalcular. [Critérios e limites](docs/research/dose-adaptativa-por-tema.md).
- **Revisões equilibradas:** acerto objetivo e tamanho da amostra orientam dose e intervalo; convicção continua nos retornos específicos. Sem piso automático de 20 a todo resultado abaixo da meta. Lotes e prática do tema compartilham o orçamento, com registros separados e crédito para complementos próximos. Mudança com prévia em Ajustes → Como o app calcula as revisões. [Método, evidência e limites](docs/research/revisoes-equilibradas.md).
- **Registro:** acertos, convicção, questões novas/repetidas/mistas, importação de CSV/TSV e histórico de correções.
- **Plano de corte:** em Temas, diferença entre demanda condicional e capacidade, com propostas protegendo temas frágeis e opção de prévia, aplicar e desfazer.
- **Minha meta:** em Temas, corte com fonte e faixas observadas de simulados e questões novas, mantendo denominadores separados. Não prevê aprovação.
- **Revisão semanal:** opcional em Hoje, com mudanças por área, aderência, erros e simulados; sugestões de carga não são aplicadas automaticamente.
- **Parâmetros e calibração:** versão 1 preserva os cálculos anteriores. Seleção só manual em Ajustes; análise somente leitura em `scripts/analise_calibracao.py`, após 6 a 8 semanas de uso diário.
- **Ajustes:** meta diária, metas de acerto nos temas (global ou por área), Minhas provas e incidências por instituição.
- **Importância das provas:** pesos exigem incidências individuais aplicáveis para todo o conjunto, mantendo as instituições selecionadas. A prévia mostra fontes, pesos, prioridades e mudanças no plano antes de aplicar. Uma tabela conjunta não permite inferir incidências individuais. [Regras e limites](docs/research/pesos-e-proximas-revisoes.md).
- **Erros:** anotação opcional após o bloco; consulta e resolução em Temas → Erros abertos, com histórico e exportação CSV. Erros críticos ou recorrentes acrescentam prioridade alta e bloqueiam redução de cartões.
- **Simulados:** registro curto, resultados opcionais por área ou tema e evolução separada dos blocos. Inéditas por tema podem ser convertidas explicitamente, sem duplicação. Dia feito por simulado dispensa a meta normal mediante prévia, com opção de desfazer.
- **Revisão final:** datas de prova e inscrição no calendário, importância vinculada às provas e programação temporária com descanso na véspera. Prévia → aplicar → desfazer. [Regras e limites do lote B](docs/research/lote-b-entrega.md).
- **Flashcards:** lista prática de redução seletiva, com aplicação manual.
- **Arquivos e ferramentas:** importação e backup; classificação A–D, planejador de suspensões, simulação, painel antigo e roteiro simples identificados como legado, separados do fluxo principal.

O plano usa sempre temas específicos. PDFs são contexto documental: sua data não vira contato de estudo, e percentual revisado não vira percentual de acerto. A meta de90% orienta a preparação; não representa previsão ou garantia de aprovação. As fórmulas de planejamento e seus limites estão na [documentação](docs/README.md).

## Instalar e abrir no Windows

Requer Python3.11 ou superior; o ambiente de validação usa Python3.13.

Com os atalhos instalados, **Osler** fica na Área de Trabalho e no menu Iniciar. O servidor é preparado automaticamente ao entrar no Windows, sem abrir o navegador ou mostrar um terminal. Abra o ícone Osler quando quiser estudar. **Encerrar Osler**, no menu Iniciar, encerra as sessões iniciadas pelo lançador. Os arquivos `.bat` continuam como alternativa.

Para instalar esses atalhos em outra cópia, execute uma vez `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install_local_shortcuts.ps1`. O script instala somente para o usuário atual e preserva atalhos existentes que apontem para outro aplicativo. Para desativar a partida automática, retire o atalho Osler da pasta que abre com `Win+R` → `shell:startup`.

1. Clone ou baixe este repositório.
2. Execute **instalar.bat** para criar o ambiente e instalar as dependências.
3. Execute **iniciar.bat**. O navegador abre quando o servidor estiver pronto e a janela do lançador fecha. Se o app já estiver aberto, o mesmo servidor é reutilizado.
4. Abra [http://127.0.0.1:8501](http://127.0.0.1:8501).

O servidor fica em segundo plano e atende somente neste computador. Para encerrá-lo, execute **encerrar.bat**. Esse atalho encerra apenas o processo iniciado pelo lançador desta pasta, verificando sua identidade; servidores iniciados manualmente devem ser encerrados com Ctrl+C no terminal original. Fechar a aba do navegador mantém o servidor disponível para a próxima abertura.

Se houver erro na abertura, a janela mostra o motivo. O log fica em `.osler-runtime/server.log`; esses arquivos locais não são enviados ao GitHub. Não é necessário reinstalar as dependências para abrir novamente o app.

### Instalação manual

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Em Linux/macOS, use `.venv/bin/python` no lugar de `.venv\Scripts\python.exe`. `requirements-lock.txt` registra as versões do ambiente validado; `requirements.txt` define os intervalos de instalação.

## Primeiro uso

### Atualizar Planner e flashcards de erros

Abra **Atualizar dados** na barra lateral. Há duas abas independentes:

- **Planner de questões:** envie o HTML/TXT da tabela ou cole o HTML, informe o dia da captura e clique em **Conferir atualização**. Veja questões distintas, convicção, contato e pendências antes de clicar em **Atualizar Planner** e confirmar. Capturas parciais mantêm os dados dos temas ausentes. O acumulado não vira novos blocos nem é somado às tentativas registradas no app.
- **Flashcards de erros:** envie a árvore HTML, informe o dia e diga se o arquivo contém somente pendentes, todo o inventário ou uma nova passagem. Confira o saldo antes/depois e confirme **Atualizar cards de erros**. Pais e filhos não entram duas vezes; estudos anteriores permanecem no histórico. Criações registradas depois da captura continuam na fila e aparecem separadas na prévia.

A data segue o dia de estudo da Osler: antes das04h ainda pertence ao dia anterior. Ela permite interpretar “Hoje” e “dias sem contato”; sem esse campo, não se inventa um último contato.

As incidências atuais são mantidas por padrão. Para atualizá-las junto do progresso, marque a opção correspondente e informe as instituições daquela consulta. Uma tabela parcial não pode substituir silenciosamente uma incidência mais completa já cadastrada; nesse caso, atualize só o progresso ou envie a consulta completa.

**Como copiar o HTML da Osler** fica recolhido nas duas abas, com os passos de exportação manual. O app lê apenas o arquivo recebido, sem acessar sua conta. Arquivos originais, capturas anteriores e registros são preservados. Reenviar a mesma atualização não repete as contagens. [Funcionamento e validações](docs/research/atualizacao-guiada-de-dados.md).

### Configuração inicial

1. Em **Arquivos e ferramentas → Dados e classificação → Importar relatórios**, importe os PDFs exportados manualmente.
2. Em **Meu estudo → Ajustes → Meta e rotina**, escolha a quantidade diária, a divisão novos/revisões e a meta de acerto nos temas. Metas por grande área são opcionais; áreas sem ajuste usam a global.
3. Em **Hoje**, faça um bloco e clique em **Registrar este bloco**. O tema e a quantidade já vêm preenchidos.
4. Registre quantas fez, quantas acertou e, quando souber, quantos acertos foram com convicção. Deixar convicção vazia significa desconhecida.
5. Use **Calendário** para consultar a programação. **Planejar pendências com antecedência** compara estratégias antes de aplicá-las.

Em **Ajustes → Minhas provas**, cadastre instituição, data e corte com a fonte consultada. Edição, inscrição e observações são opcionais. Você pode editar por nova versão ou desconsiderar sem apagar o histórico. A prova principal escolhida define a data usada pelo plano; no automático, vale a futura mais próxima (ou a passada mais recente se não houver futuras). Sem provas cadastradas, a data configurada anterior é preservada; o padrão continua30/11/2027.

**São duas referências diferentes:** a meta de temas orienta acerto com convicção em questões novas e amostra suficiente; o corte informado de uma prova é somente referência documental (`corte / nota máxima`). Nenhum deles é probabilidade de aprovação. As fórmulas de espaçamento, doses e alocação permanecem as anteriores; metas por área apenas resolvem o parâmetro de meta do tema. [Fonte, hipótese e limites](docs/research/meta-em-duas-camadas-v0.16.md).

Incidências podem ser importadas a qualquer momento em **Ajustes → Instituições e incidências**, em HTML, CSV ou TSV. O conjunto de instituições deve corresponder ao arquivo; incidência desconhecida não é tratada como baixa.

## Dados e privacidade

O histórico importado alimenta uma **fila inicial de prioridades**, distribuída dentro da sua carga. Ele não cria centenas de compromissos vencidos no primeiro dia. As revisões decorrentes de blocos realizados, retornos conhecidos e propostas realmente perdidas continuam identificadas. O calendário mostra riscos de falta de vaga para repetições previstas, sempre condicionais aos resultados e intervalos atuais. [Modelo, evidências e limites](docs/research/priorizacao-inicial-v0.17.md).

Retratos do Planner com definições confirmadas podem fornecer segurança acumulada, questões distintas e último contato sem criar sessões. Segurança recuperada nas revisões aparece separada do acerto em questões novas e não basta para declarar domínio. [Regras e limites](docs/research/seguranca-acumulada-osler-v0.16.1.md).

Em **Temas**, quando houver retrato importado, **Histórico da Osler** mostra de início questões realizadas e convicção acumulada. **Blocos registrados no app** mostra os resultados de dia, semana, mês ou todo o período. Acumulados não são somados a tentativas. Em **Ajustes → Meta e rotina**, a data de início do cronograma define o primeiro dia com metas; dias anteriores não geram cobrança ou propostas em falta. Contatos reais anteriores continuam orientando as prioridades. Perfis antigos, sem data de início, mantêm o funcionamento anterior. Para voltar ao código anterior a0.16.2, restaure também o backup anterior à configuração de início em outra pasta, preservando a atual.

O banco SQLite, os originais e os exports ficam na pasta local `data/`. Configurações e histórico pessoais não são fornecidos por este repositório. Use a função **Backup e restauração** do aplicativo para guardar seus dados separadamente.

O `.gitignore` exclui banco, PDFs, backups, exports, relatórios de execução, capturas, credenciais e arquivos temporários. O código pode ser atualizado sem incluir esses arquivos no GitHub. Não use `git add -f` para contornar essas exclusões com dados pessoais.

O servidor escuta somente em `127.0.0.1`: o endereço funciona no próprio computador. A adaptação da interface a telas estreitas não habilita acesso de outro aparelho pela rede.

Esta versão migra aditivamente o banco para schema12, com parâmetros e revisões semanais além das tabelas anteriores. Faça backup antes de atualizar. Para reverter ao código anterior, restaure também um backup anterior em outra pasta e preserve a pasta atual; código antigo não abre schema12. Nunca altere `user_version` manualmente para simular reversão.

## Desenvolvimento e testes

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Os testes geram relatórios e sessões de exemplo em pastas temporárias. Testes marcados `real` dependem de PDFs pessoais ausentes do repositório e são ignorados quando esses arquivos não estão disponíveis. Os cenários têm relógio de domínio fixo para serem reproduzíveis; o app usa a data real.

A interface foi verificada funcionalmente com AppTest e por análise estática. A validação visual em viewports e de toque em aparelhos físicos permanece pendente.

## Organização do projeto

- `app.py`: entrada do Streamlit.
- `osler/`: extração, armazenamento, planejamento, estatísticas e interface.
- `tests/`: testes automatizados e dados sintéticos.
- `.streamlit/config.toml`: configuração local do servidor e tema.
- `DESIGN.md` e `.impeccable/design.json`: sistema visual documentado.
- `docs/`: pesquisa, fórmulas, limites e atribuições.

A interface segue as referências Operate, Distill, Adapt e Craft Floor do Impeccable, combinadas com o Revenue-Centric Design de Richard ([@richardrx](https://x.com/richardrx)), na [curadoria heliocosta-dev](https://github.com/heliocosta-dev/revenue-centric-design). [Aplicação e atribuição](docs/design/revenue-centric-design-aplicado.md), [licença do material de design](docs/third-party/revenue-centric-design-LICENSE.txt).
