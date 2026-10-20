# Osler Study Optimizer

Aplicativo local para organizar a preparação para residência médica: plano diário por quantidade de questões, acompanhamento de desempenho e revisões espaçadas por tema específico.

**Versão 0.14.0.** Interface em português, construída com Streamlit. Os resultados são informados pelo usuário ou importados de arquivos exportados manualmente; o aplicativo não acessa nem automatiza a plataforma Osler.

## O que o aplicativo oferece

- **Hoje:** blocos de questões priorizados por incidência, desempenho, incerteza e tempo sem contato; registro do resultado e revisões extras.
- **Calendário:** Agenda, Semana e Mês; atrasos, recuperação e prevenção de pendências com comparação antes/depois e opção de desfazer.
- **Temas:** filtros de situação, períodos de análise, tabela ou lista paginada e exportação dos resultados filtrados.
- **Registro:** acertos, convicção, questões novas/repetidas/mistas, importação de CSV/TSV e histórico de correções.
- **Ajustes:** meta diária, proporção de questões entre temas novos e revisões, data da prova e incidências por instituição.
- **Flashcards e ferramentas:** análise de relatórios, sugestões de redução seletiva, simulação, histórico e backup/restauração.

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
2. Em **Meu estudo → Ajustes**, escolha sua meta diária e a divisão entre questões em temas novos e revisões.
3. Em **Hoje**, faça um bloco e clique em **Registrar este bloco**. O tema e a quantidade já vêm preenchidos.
4. Registre quantas fez, quantas acertou e, quando souber, quantos acertos foram com convicção. Deixar convicção vazia significa desconhecida.
5. Use **Calendário** para consultar a programação. **Planejar pendências com antecedência** compara estratégias antes de aplicá-las.

Incidências podem ser importadas a qualquer momento em **Ajustes → Instituições e incidências**, em HTML, CSV ou TSV. O conjunto de instituições deve corresponder ao arquivo; incidência desconhecida não é tratada como baixa.

## Dados e privacidade

O banco SQLite, os originais e os exports ficam na pasta local `data/`. Configurações e histórico pessoais não são fornecidos por este repositório. Use a função **Backup e restauração** do aplicativo para guardar seus dados separadamente.

O `.gitignore` exclui banco, PDFs, backups, exports, relatórios de execução, capturas, credenciais e arquivos temporários. O código pode ser atualizado sem incluir esses arquivos no GitHub. Não use `git add -f` para contornar essas exclusões com dados pessoais.

O servidor escuta somente em `127.0.0.1`: o endereço funciona no próprio computador. A adaptação da interface a telas estreitas não habilita acesso de outro aparelho pela rede.

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
