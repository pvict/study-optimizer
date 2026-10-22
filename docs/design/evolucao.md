# Evolução — surface brief

Mode: Operate. Expansão da identidade de DESIGN.md: azul, superfícies claras, geometria precisa, controles nativos. Code-first por ser tela de aplicativo. Sem troca de paleta ou fontes externas.

Objetivo confirmado: enxergar evolução real e projeções de semanas, meses e fim da preparação; questões, cobertura e possíveis fragilidades. Preferência: jornada elegante com marcos/conquistas discretas. O primeiro olhar precisa mostrar o período e o que ele significa.

Composição: seletor de horizonte; faixa editorial de jornada com trilha temporal e estado observado/previsto; gráfico de volume/cobertura com linhas e legendas distintas; rendimento observado e cenário condicional quando sustentado; oportunidades de reforço por tema específico; conquistas compactas derivadas de fatos. Sem grade de cartões idênticos como estrutura, sem anel de progresso ou XP fictício. Marcos futuros nunca têm o estado conquistado.

Dados e interação: novo destino Evolução. Períodos14/30/90/180dias, referência da preparação e data livre. Cache por estado/data/carga simulada. Simulação de outra meta não grava preferências. Ver detalhes/critério em expanders; ações para estudar tema e voltar ao plano.

Responsividade: trilha horizontal no desktop e vertical em telas estreitas, conteúdo em uma coluna no celular, gráficos fluidos com tooltips e alternativa tabular; foco/contraste/redução de movimento preservados. Sem largura mínima forçada no documento.

Conceito de gamificação: pequenos marcos verificáveis, com data de previsão quando couber; conquistas reais por registros, dias de prática e cobertura documentada. Reconhecer histórico importado explicitamente. A jornada não equipara cobertura a domínio.

Validação: testes dos dados/estados, AppTest interativo, critérios CSS responsivos e inspeção dos artefatos visuais permitidos. Restrição de automação do navegador desta sessão permanece; não contornar por CDP/HTTP.

## Direction contract

THESIS: tornar o caminho da preparação legível, preservando a diferença entre construção real e futuro condicional. A tela não é um placar de aprovação nem uma parede de alertas.

OWN-WORLD: superfícies claras e azul do sistema existente, trilha geométrica nítida e controles nativos. Círculos pequenos marcam encontros; texto informa estado, data, respostas e cobertura.

STORY: escolher um horizonte, reconhecer o ponto de partida, explorar o cenário e abrir o tema que merece atenção. Conquistas discretas reconhecem fatos; datas futuras permanecem previstas.

FIRST VIEWPORT: período acima da trilha e resumo compacto abaixo. Gráfico ocupa a largura útil; no celular a trilha resume hoje, data escolhida e fim para reduzir rolagem. Premissas e tabelas ficam recolhidas.

FORM: jornada editorial dentro da identidade existente, escolhida explicitamente pelo usuário; construção direta em código por ser superfície de aplicativo. Sem novo mundo visual, fontes externas ou imagens decorativas.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Finish review

Componentes SVG de produção da trilha inspecionados em390/1024px; os gráficos Vega foram renderizados nativamente em larguras de280/900px e inspecionados com os dados reais da cópia local. O ajuste final separou respostas/cobertura em linhas e condensou a trilha móvel para evitar cortes e excesso de altura. Não há raster no aplicativo: os PNGs de conferência ficam emtmp, fora da distribuição.

Navegação, mudança de período/data/carga, estados vazios e cache testados por AppTest. Houve revisão independente do código, com correções de recência, duração real e acumulados. Veredito: componentes e comportamento aprovados dentro da validação permitida; não se afirma inspeção visual de uma página de navegador nem medição da cascade final do Streamlit.
