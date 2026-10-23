# Osler Study Optimizer

Aplicativo local para organizar a preparação para residência médica: plano diário por quantidade de questões, acompanhamento de desempenho e revisões espaçadas por tema específico.

O **dia de estudo vira às 04h, no horário de Brasília**: 22/10 inclui o período
de 22/10 às 04h até antes de 23/10 às 04h. Plano, registro padrão, calendário,
estatísticas e trocas usam esse mesmo dia. Datas já declaradas/importadas e horários
de auditoria permanecem intactos.

**Versão 0.19.0.** Interface em português, construída com Streamlit. Os resultados são informados pelo usuário ou importados de arquivos exportados manualmente; o aplicativo não acessa nem automatiza a plataforma Osler ou a FluidMed.

A interface usa navegação visível em abas, campos com contorno e separação por linhas e tons de azul-cinza entre conteúdo e apoio. Hoje tem resumo compacto; Calendário mostra a programação antes das ferramentas de recuperação; Temas reúne filtros secundários em “Mais filtros”. Após salvar um resultado, a confirmação oferece retorno ao plano ou um novo registro. [Decisões e limites da verificação do redesign](docs/design/redesign-ui.md).

## O que o aplicativo oferece

- **Hoje:** abas Para fazer e Feito hoje, com blocos priorizados, resultados do dia e acesso à correção dos lançamentos. Após salvar, veja seu desempenho e os próximos passos do tema. [Fluxo e critérios](docs/research/atividade-diaria-e-feedback.md).
- **Trocar tema:** escolha manual ou sugestão do mesmo tipo e prioridade semelhante; a prévia mostra a data reservada para o tema retirado, com opção de desfazer. [Funcionamento](docs/research/troca-de-temas.md).
- **Calendário:** Agenda, Semana e Mês; próximos contatos por tema, retornos conhecidos e revisões seguintes a recalcular após seus resultados. Recuperação e prevenção de pendências com comparação antes/depois e opção de desfazer. [Como interpretar a previsão](docs/research/calendario-proximos-contatos.md).
- **Rotina adaptativa:** referência de novos/revisões com ajuste à demanda e à capacidade de repetir nos próximos14dias; comparação com divisão fixa, custo em cobertura e riscos residuais visíveis. Doses não são infladas para preencher a meta. O modo fixo continua disponível.
- **Evolução:** jornada por semanas, meses e fim da preparação, com respostas, cobertura e pontos de atenção. Compare intervalos atuais com avanço condicional das revisões ao atingir a meta; cada cenário respeita a carga e fica separado dos resultados reais. [Hipóteses e limites](docs/research/evolucao-espacamento-condicional.md).
- **Temas:** resultados registrados no app ao lado do histórico importado, com fontes separadas; filtros de situação e período, tabela ou lista paginada e exportação. [Entenda as contagens](docs/research/temas-historico-e-blocos.md).
- **Revisões por tema:** dose do próximo bloco ajustada aos resultados reais; manutenção menor após bons encontros espaçados, reforço após dificuldades e revisões seguintes a recalcular. [Critérios e limites](docs/research/dose-adaptativa-por-tema.md).
- **Registro:** acertos, convicção, questões novas/repetidas/mistas, importação de CSV/TSV e histórico de correções.
- **Ajustes:** meta diária, metas de acerto nos temas (global ou por área), Minhas provas e incidências por instituição.
- **Erros:** anotação opcional após o bloco; consulta e resolução em Temas → Erros abertos, com histórico e exportação CSV. Erros críticos ou recorrentes acrescentam prioridade alta e bloqueiam redução de cartões.
- **Simulados:** registro curto, resultados opcionais por área ou tema e evolução separada dos blocos. Inéditas por tema podem ser convertidas explicitamente, sem duplicação. Dia feito por simulado dispensa a meta normal mediante prévia, com opção de desfazer.
- **Revisão final:** datas de prova e inscrição no calendário, importância vinculada às provas e programação temporária com descanso na véspera. Prévia → aplicar → desfazer. [Regras e limites do lote B](docs/research/lote-b-entrega.md).
- **Flashcards:** lista prática de redução seletiva, com aplicação manual.
- **Arquivos e ferramentas:** importação e backup; classificação A–D, planejador de suspensões, simulação, painel antigo e roteiro simples identificados como legado, separados do fluxo principal.

O plano usa sempre temas específicos. PDFs são contexto documental: sua data não vira contato de estudo, e percentual revisado não vira percentual de acerto. A meta de90% orienta a preparação; não representa previsão ou garantia de aprovação. As fórmulas de planejamento e seus limites estão na [documentação](docs/README.md).

## Instalar e abrir no Windows

Requer Python3.11 ou superior; o ambiente de validação usa Python3.13.

1. Clone ou baixe este repositório.
2. Execute **instalar.bat** para criar o ambiente e instalar as dependências.
3. Execute **iniciar.bat** e mantenha a janela em execução enquanto usa o app.
4. Abra [http://127.0.0.1:8501](http://127.0.0.1:8501).

Para encerrar o servidor, use Ctrl+C na janela em que ele foi iniciado.

### Instalação manual

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Em Linux/macOS, use `.venv/bin/python` no lugar de `.venv\Scripts\python.exe`. `requirements-lock.txt` registra as versões do ambiente validado; `requirements.txt` define os intervalos de instalação.

## Primeiro uso

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

Esta versão migra aditivamente o banco para schema11, com histórico de provas, erros e simulados. Faça backup antes de atualizar. Para reverter ao código anterior, restaure também um backup anterior em outra pasta e preserve a pasta atual; código antigo não abre schema11. Nunca altere `user_version` manualmente para simular reversão.

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
