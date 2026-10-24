# Product

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
Pessoa que se prepara para residência médica, estudando pelo computador e celular. Contexto confirmado na conversa do projeto.

## Product Purpose
Organizar uma rotina viável em questões por dia, usando estudo realizado, convicção, incidência nas instituições e tempo sem contato para orientar temas específicos e revisões.

## Operating Context
Aplicativo local em Python/Streamlit. Fontes: arquivos exportados manualmente e registros do usuário. Sem acesso ou automação da plataforma Osler. Suspensões e reativações são aplicadas manualmente pelo usuário.

## Capabilities and Constraints
Calendário, rotina fixa/adaptativa, questões novas/repetidas, lotes de erros com retorno de7dias, estatísticas e histórico imutável. Convicção recuperada da Osler não é acerto de primeira tentativa. Preservar originais e versões. A meta de90% não é probabilidade de aprovação. Projeções não registram estudo ou domínio e precisam de premissas identificadas.

## Brand Commitments
Português simples, ações claras, configurações avançadas recolhidas; usar Impeccable e Revenue-Centric Design. Evolução deve oferecer jornada elegante, marcos e conquistas discretas, preferência confirmada pelo usuário em20/10/2026. Sem urgência artificial, progresso ou dados pessoais fictícios.

## Evidence on Hand
Código e documentação dos modelos; PDFs e tabelas importados localmente. Séries reais de desempenho podem estar ausentes: a interface precisa comunicar insuficiência em vez de preencher curvas com exemplos pessoais.

## Product Principles
- A rotina precisa caber na carga escolhida.
- Separar evidência observada, interpretação e cenário futuro.
- Mostrar próximos passos, deixando detalhes acessíveis.
- Conquistas reconhecem realizações verificáveis.
- Manter a mesma função acessível em computador e celular.

## Planned Capabilities

Recuperação dos cards pessoais de erros implementada na v0.26: lote HTML hierárquico local, meta própria, primeira passagem por temas específicos, repetições registradas separadamente e cenário dos próximos dias. Isso não implementa a organização integral de horários descrita abaixo nem substitui o espaçamento individual da Osler. [Escopo e limites](docs/research/cards-erros-recuperacao.md).

**Organização integral da rotina — planejada, ainda não implementada.** Integrar
horários de sono, plantão variável, deslocamento, academia, refeições, descanso,
flashcards, questões, correção e simulados ao fluxo existente de Hoje e Calendário.
A carga deve partir dos dados locais e do planejador ativo, distinguir configurado,
proposto e realizado, explicitar tempos estimados e respeitar a disponibilidade
real. O modelo cobre 12 meses por cenários e se recalcula com dados novos, sem
inventar melhora ou garantir 90% de acerto. Solicitação confirmada em 21/10/2026;
nesta etapa, somente documentação e análise, sem mudanças no aplicativo ou banco.
[Requisito, fontes e critérios de aceitação](docs/research/organizacao-de-rotina-proposta.md).
