# Escopo final: Temas em atenção na lateral

O usuário retirou a integração da carga Osler e pediu a seção em página própria. Hoje e o planejamento foram restaurados. As capturas de rotina abaixo registram o protótipo anterior e não representam uma função disponível. A instalação Visant e o painel de atenção permanecem. Validação final: scripts/check_attention_menu.py; capturas em evidencias/atencao-menu.

# Rotina e atenção: composição de trabalho

Escopo de 29/10/2026: simplificar a leitura de Hoje e da rotina preservando a direção Apple, Streamlit, histórico e regras de estudo. A interface é de uso local; nenhuma conta Osler é acessada. A variável de produto é a clareza para escolher o próximo estudo, com menos leitura repetida.

## Classificação antes da alteração

| Rota / região | Surface | Business variable | Persuasão |
| --- | --- | --- | --- |
| Hoje / temas que merecem atenção | B — trabalho | Qualidade da decisão sobre o próximo estudo | Nenhuma; dados e amostras observadas |
| Ajustes / meta e rotina | B — trabalho | Clareza para conferir a configuração atual | Nenhuma; ritmo configurado, sem promessa de resultado |
| Rotina / salvar alterações | C — confiança | Correção e reversibilidade dos dados | Nenhuma; confirmação e retorno nativos existentes |

## Decisões

- A atenção usa tabela nativa com colunas alinhadas e rolagem própria. Mantém as medidas e suas amostras próximas; não transforma falta de dado em zero. O CSS não interfere no canvas nem nas células virtualizadas do Streamlit.
- A rotina e a atenção são seções discretas, sem nova moldura arredondada externa. Espaçamento e divisórias organizam o conteúdo; botões e campos continuam nativos.
- Azul fica nas ações e seleção reais. Não acrescentar ícones decorativos, kickers, microetapas ou cartões apenas para preencher espaço.
- Os tokens existentes de `osler/bento.css` e a seção Direção Apple de `DESIGN.md` prevalecem sobre receitas genéricas. Zero informado permanece zero, percentuais mantêm sua natureza e amostra; meta não vira previsão.
- Alvos de 44px, foco visível, fonte de sistema e movimento reduzido são herdados da base. Os novos seletores se restringem às seções desta tarefa.

Mecanismos aplicados: RCD, **remover informação abre espaço para direção** e **hierarquia de atenção**; Visant, **surface B**, **chrome budget**, **grouping by spacing** e **columns**. Acesso avançado, fontes, cálculos e confirmação de gravações permanecem sob os componentes existentes.

## Skills instaladas

Fonte: [pedrojaques99/visant-skills-public](https://github.com/pedrojaques99/visant-skills-public/tree/main), licença MIT declarada no repositório. Instalação pelo helper `install-skill-from-github.py`, sem instalar dependências ou componentes no projeto.

| Skill | Caminho local | Papel |
| --- | --- | --- |
| visant-killer | `C:/Users/Paulo/.codex/skills/visant-killer` | Auditoria de excesso e revisão adversarial |
| visant-frontend | `C:/Users/Paulo/.codex/skills/visant-frontend` | Classificar superfícies e justificar cada elemento |
| visant-refine | `C:/Users/Paulo/.codex/skills/visant-refine` | Valores com unidade, base e contexto |
| visant-copy | `C:/Users/Paulo/.codex/skills/visant-copy` | Português falado, conciso e sem tiques de IA |
| visant-motion | `C:/Users/Paulo/.codex/skills/visant-motion` | Movimento funcional, curto e reduzível |
| visant-preflight | `C:/Users/Paulo/.codex/skills/visant-preflight` | Checagem de premissas para futuros projetos grandes |
| visant-methodology | `C:/Users/Paulo/.codex/skills/visant-methodology` | Referência de estratégia de marca para uso futuro |

As duas últimas foram instaladas como referências; não impõem um novo processo de branding a este refinamento pontual. O conjunto usa a Revenue-Centric Design já instalada, que permanece intacta. As quatro skills de vídeo e conexão MCP não foram necessárias ao trabalho de interface.

## Verificação e limites

O `noise-scan` encontrou zero arquivos de interface compatíveis no código Python/Streamlit. Esse resultado não valida texto nem composição. O `motion-lint` executado sobre `bento.css` não trouxe achados; nenhum movimento novo é introduzido. A verificação visual no navegador deve registrar largura, estado e resultado antes de uma conclusão sobre o acabamento.

Fundação existente: `.venv/Scripts/python.exe -m pytest tests/test_bento_foundation.py -q`, seis testes aprovados. `git diff --check` sem erro. Os sete `SKILL.md` instalados foram encontrados no destino. O autoteste do `noise-scan` aprovou suas 24 regras e cinco aliases. O autoteste do `motion-lint` falhou em duas expectativas de apresentação de caminhos dentro de `scripts/__fixtures__` na instalação standalone; isso é um limite da ferramenta externa, não evidência de falha da interface. Não houve alteração nas skills para mascarar o resultado.

## Screen seen

| Rota | Largura | Estado dos dados | Resultado |
| --- | --- | --- | --- |
| Hoje, rotina e atenção | 1440px | Sintético: 40 temas, reserva externa75 | Tabela preenchida, seções sem moldura redundante e sem estouro do documento |
| Hoje, rotina e atenção | 768px | Mesmo cenário isolado | Controles preservados e rolagem da tabela interna |
| Hoje, rotina e atenção | 390px | Mesmo cenário isolado | Segmentos quebram linha, texto legível e ações acessíveis; sem estouro do documento |
| Prévia e confirmação | 1440/768/390px | Registro cumulativo externo10 | Cancelar preserva valores; confirmar grava e mostra toast |

QA reproduzível: `scripts/check_routine_attention.py`; capturas e resultado em `evidencias/rotina-integrada`. Base temporária removida ao concluir. Viewport emulado não é aparelho físico.

Detector Impeccable executado uma vez nos novos componentes e no CSS compartilhado: os avisos retornados pertencem a declarações legadas do CSS, incluindo Inter anterior ao override de fonte de sistema Apple, cores e medidas não documentadas no sidecar. Nenhum aviso nos novos módulos Python; isso não prova leitura completa dessa linguagem pelo scanner. Não se trocou globalmente fonte/tokens para satisfazer um detector. Inspeção visual e testes de interação são a prova desta entrega, sem alegar lint global limpo.

Revisão adversarial: próximo estudo acessível; motivo e fonte disponíveis; detalhes recolhidos; ausência não vira zero; sem números de preenchimento, marketing ou urgência. Parte do visual legado do restante do app foi preservada. Não atribuímos nota visual como se fosse uma medida validada.
