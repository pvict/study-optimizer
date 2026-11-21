# Desempenho local — 02/11/2026

O app continua local, em Streamlit e SQLite. Não houve migração dos dados nem alteração da política de estudo. O código anterior das partes modificadas está em `evidencias/performance-local-2026-11-02/codigo-antes.zip`; arquivos novos podem ser retirados ao reverter. `topic_contacts.py` foi incluído no arquivo a partir da leitura prévia preservada, revertendo somente as edições desta tarefa. Nenhuma restauração foi aplicada à base ativa.

## Abertura

`iniciar.bat` chama um lançador leve da biblioteca padrão, espera saúde e identificação da pasta antes de abrir o navegador e reutiliza o servidor existente deste projeto. O servidor fica em segundo plano, ligado apenas em 127.0.0.1. Aberturas simultâneas são serializadas por uma trava nativa. Uma porta ocupada por outro serviço gera mensagem; nenhum processo desconhecido é encerrado.

`encerrar.bat` encerra as sessões iniciadas pelo novo lançador. A propriedade do processo é registrada atomicamente antes da espera de prontidão. O encerramento compara o PID e a data de criação nativa, mantendo o handle verificado aberto durante a operação. Um servidor iniciado manualmente continua sob controle do terminal original. Fechar o navegador mantém o app disponível; não foi configurada inicialização automática com o Windows.

Falhas de inicialização e timeout são informados e o processo criado naquela tentativa é encerrado. Logs ficam em `.osler-runtime/server.log`, com rotação antes de uma nova partida quando ultrapassam 1 MiB. Marcadores, identidade do processo e logs ficam fora do Git. Não há nova dependência.

## Cálculos e carregamento

- Bibliotecas de gráficos, extração de PDFs e ferramentas de outras telas passam a ser carregadas na rota responsável. O cache nativo de módulos do Python continua valendo nas visitas seguintes.
- O calendário tem um iterador por dia. A API existente continua devolvendo a lista completa. A consulta das próximas revisões interrompe o consumo quando encontrou a primeira data de todos os blocos, preservando o horizonte exibido e conferindo o token de atualização ao terminar.
- Se qualquer tema ainda não tiver data, a consulta percorre todo o horizonte. Não se inventam vagas nem se eliminam temas da cobertura.
- A dose só é preparada depois da verificação de elegibilidade do dia. Estados sem lotes pendentes não são copiados de novo apenas para calcular capacidade. A preparação continua contando todos os compromissos futuros.

## Medições e provas

Comparação sobre uma única cópia SQLite e das exportações, removida ao terminar:

| Operação | Antes | Depois |
|---|---:|---:|
| Importação inicial dos módulos de interface, mediana de 3 processos novos | 2,67 s | 1,62 s |
| Consulta de primeiras revisões para 1.163 blocos | 4,66 s | 2,99 s |
| Calendário de 60 dias, próximos contatos | 1,86 s | 1,50 s |
| Calendário de 60 dias, intervalos mantidos | 1,90 s | 1,65 s |
| Calendário de 60 dias, cenário progressivo | 1,93 s | 1,68 s |

Todas as primeiras datas e os três calendários completos, incluindo doses e diagnósticos, foram iguais aos resultados da implementação anterior. Esses números são observações locais; não são garantia de latência em todas as execuções. A mediana de importação mede módulos, não toda a abertura no navegador.

Uma passagem do navegador em cópia dos dados percorreu nove rotas e uma busca, sem exceções visíveis. Temas abriu em 5,21 s e Hoje em 5,02 s nessa passagem. Hoje, Temas, Registro e Calendário também foram conferidos em 390 px sem transbordamento horizontal da página. A medição anterior de Temas era 8,54 s, mas ocorreu em uma base ligeiramente diferente e não constitui comparação controlada.

Dez testes do lançador passaram, incluindo servidores Streamlit reais em portas isoladas, concorrência, conflito com outro projeto, serviço HTTP sem identidade, falha, timeout, navegador após prontidão, encerramento de processo próprio, recusa de PID reutilizado e gravação de propriedade antes da prontidão. Testes adicionais cobrem imports adiados, interrupção de primeiras datas, preservação do horizonte e temas sem encaixe. A revisão independente encontrou dois ajustes no ciclo de vida do processo; ambos foram corrigidos e a nova revisão não apontou pendências nesses ajustes.

Suíte completa: **1.080 passaram, um foi pulado e houve um aviso**, em 375,45 s. O teste pulado depende de links simbólicos indisponíveis no ambiente Windows; o aviso é esperado no teste de ZIP com entrada duplicada. O processo pytest concluiu com esse resumo. O invólucro de leitura do log tentou UTF-8 enquanto o filho havia emitido cp1252; essa leitura falhou após os testes. O log foi conferido diretamente e normalizado para UTF-8, sem repetir a suíte. O resultado está em `evidencias/performance-local-2026-11-02/suite-final.log`.

Um teste adicional de ciclo de vida confirmou que o processo lançador termina com código zero, o servidor continua atendendo após a saída do pai e o encerramento fecha a porta. A reutilização do servidor ativo em 8501 também foi verificada, sem reiniciá-lo ou tomar propriedade de um processo iniciado manualmente.

Evidências de navegação e comparação ficam na mesma pasta. Testes e medições usam pastas temporárias exclusivas, removidas ao concluir; o banco ativo não é usado como base de testes.

## Acesso sem arquivos BAT

Após o pedido de acesso mais simples, foram instalados atalhos nativos para o usuário atual: Osler na Área de Trabalho e no menu Iniciar; Encerrar Osler no menu Iniciar; Osler em Startup, executando `pythonw -m osler.local_launcher --background`. Esse modo prepara o servidor sem abrir o navegador. Não há serviço administrativo ou mudança de política permanente do PowerShell.

O modo sem console registra falhas em `.osler-runtime/launcher.log`; aberturas manuais sem console exibem mensagem nativa se falharem. O instalador `scripts/install_local_shortcuts.ps1` confere todos os destinos antes de escrever e recusa sobrescrever atalhos desconhecidos.

Validação desta extensão: 12 testes do lançador passaram; partida fria com pythonw em pasta e porta temporárias, sobrevivência do servidor e encerramento confirmados; o atalho de Startup instalado foi executado com código zero e reutilizou o servidor ativo. Não foi simulado um novo login do Windows. A inicialização automática pode ser desfeita retirando o atalho Osler de `shell:startup`.
