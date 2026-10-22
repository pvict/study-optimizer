# Redesign da interface — outubro de 2026

Aplicação do prompt e da auditoria fornecidos pelo usuário, com prioridade explícita para abas visíveis, contraste entre seções e menos seletores nas tarefas frequentes. Direção Operate, orientada por Impeccable e Revenue-Centric Design: mostrar a tarefa principal antes dos ajustes. Sem fontes remotas, scripts externos ou dependências novas.

## Ajuste após a captura do usuário

O usuário rejeitou os painéis brancos e mostrou os quatro filtros de estado truncados. A largura proporcional das colunas nativas permanecia ativa dentro da grade CSS; as colunas agora recebem100% da célula, sem a segunda redução para25%. Os filtros têm largura inteira, texto sem reticências e indicador inferior, sem caixas brancas. A busca usa apenas um separador. Superfícies passam para #e8edf5 e apoio para #dfe7f1; tema, CSS e documentação foram sincronizados. Legendas têm a cor aplicada diretamente ao parágrafo, além do container, para não herdar o tom esmaecido nativo.

Contraste calculado atualizado: texto de apoio/superfície5,15:1; texto de apoio/painel4,85:1; borda de campo/superfície3,09:1. A tabela abaixo registra a medição da etapa inicial, anterior a esse ajuste. A captura do usuário é evidência do defeito anterior; não há captura posterior pelo agente.14testes de UI passaram após a correção.

## Arquivos e decisões

- `osler/study.css`, `.streamlit/config.toml`, `DESIGN.md`, `.impeccable/design.json`: mesma paleta, fundo neutro, superfícies em azul-cinza, apoio mais escuro, campos com borda e foco. A borda de campos usa #7d8796, mais escura que a borda decorativa #d9dde3; fundo da página #f3f4f6 para separar as superfícies.
- `osler/ui.py`, `osler/adaptive_ui.py`: navegação em abas por apresentação, mantendo os widgets radio, suas keys, callbacks e teclado. Streamlit1.66 permite tabs com seleção, mas AppTest não oferece clique nessa seleção; a troca de contrato foi evitada. As abas nativas da biblioteca continuam existentes. Ferramentas de apoio ficam recolhidas e backup tem atalho visível.
- `osler/study_day_ui.py`: resumo compacto e ação do primeiro bloco em destaque; demais botões têm menor peso.
- `osler/study_calendar_ui.py`: programação e detalhe do dia antes de recuperação, prevenção e capacidade. Retornos de telas históricas/início ainda permitem acessar a gestão.
- `osler/study_tables_ui.py`: busca/filtro principal, filtros secundários recolhidos, limpeza sem gravação; ausência de acerto exato aparece como “—”, nunca0%. Estado atual e resultados do período têm escopos explícitos.
- `osler/practical_reduction_ui.py`: recomendações antes dos ajustes; alternativa Lista para ler nomes completos. Cartões estudados, cartões para avaliar e revisões/dia mantêm significados diferentes.
- `osler/adaptive_ui.py`, `assessment_ui.py`, `exam_goals_ui.py`, `planner_ui.py`, `planning_ui.py`, `study_calendar_ui.py`, `study_evolution_ui.py`, `study_prevention_ui.py`, `study_replanning_ui.py`, `study_tables_ui.py`: formato visual de datas DD/MM/YYYY. Valores, limites de data e regras permanecem iguais.
- `README.md`: orientação para a interface atual.
- `tests/test_question_ui.py`: contrato deliberadamente atualizado de três métricas para texto compacto com a mesma meta. `tests/test_redesign_ui.py`: limpeza de filtros, erro preservando entrada/contexto e confirmação sem reenvio em rerun.

No registro, `study_saved` mostra recibo após sucesso e retira o formulário já enviado. “Voltar ao plano” e “Registrar outro estudo” são ações distintas. A gravação existente, o identificador de sessão e o versionamento permanecem no serviço; a interface não cria outra sessão ao renderizar o recibo. Erros mantêm os campos para correção.

## Contraste calculado

Razões WCAG calculadas pela luminância sRGB dos tokens, não por captura da cascata do navegador:

| Par | Razão |
|---|---:|
| Texto principal / branco |16,83:1|
| Texto secundário / branco |6,05:1|
| Texto secundário / página |5,50:1|
| Texto secundário / apoio |5,15:1|
| Branco / azul de ação |6,16:1|
| Azul profundo / seleção |7,46:1|
| Borda dos campos / branco |3,63:1|
| Sucesso / fundo semântico |6,81:1|
| Alerta / fundo semântico |6,88:1|
| Atraso / fundo semântico |7,60:1|

O CSS mantém alvos de44px, foco explícito, quebra de nomes longos, largura de formulário até720px e regras estreitas de composição. Padding superior4rem substitui o antigo2,2rem/1,2rem que não reservava altura suficiente para o cabeçalho fixo. Estes são critérios implementados; a posição final do título não foi medida no navegador.

## Evidência e limites

Baseline antes de modificar o checkout ativo:416testes passaram. Verificações direcionadas cobrem os fluxos alterados com AppTest em dados sintéticos; a validação com fontes importadas ocorre somente em cópia isolada por `OSLER_DATA_DIR`. Nenhum registro de teste é enviado ao banco ativo.

Resultado final no checkout ativo:419testes passaram, sem skips, em89,97s. O único aviso vem do teste deliberado de entrada ZIP duplicada. A cópia com arquivos importados percorreu Hoje/registro, Calendário, Temas, Ajustes, Evolução, Flashcards e Arquivos; comparação posterior confirmou23tabelas e101arquivos originais inalterados. O servidor local foi reiniciado com o tema atualizado.

Detector Impeccable executado uma vez. O aviso de borda em elemento arredondado atingiu o indicador inferior da aba, cujo raio é explicitamente0; os avisos de escala tipográfica foram reconciliados com os tamanhos reais no sistema documentado. A regra antiga de métrica1,55rem de Hoje permanece inócua porque esse componente não é emitido; ela não foi promovida a regra do sistema novo.

Revisão independente do diff e testes funcionais sem problema importante encontrado no escopo examinado. Os serviços, cálculos de revisão, distribuição, importação e armazenamento não foram alterados.

Não há capturas depois do redesign: a restrição de navegador/CDP/HTTP já registrada nesta sessão foi preservada. AppTest e análise de CSS não comprovam aparência, primeira dobra em1366×768, teclado real, zoom200%, toque ou ausência de overflow em390/768/1024/1440px. A inspeção visual dessas larguras permanece pendente; não se afirma conformidade WCAG completa. Rótulos internos de calendário e controles do Streamlit podem continuar em inglês, embora as datas do app usem DD/MM/YYYY.
