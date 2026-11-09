# Correção de erros em subtemas agrupados — 02/11/2026

A anotação de um erro usa o tema específico do catálogo. A distribuição da correção usava apenas planning_states, onde o agrupamento pode substituir esse tema por seu pai. Isso produzia “Um tema saiu do catálogo” mesmo quando o subtema e seus dados individuais continuavam presentes.

A correção agora seleciona os estados individuais dos temas praticáveis do catálogo atual. Estados de grupos e agregados históricos não são somados a essa base. A incidência específica da instituição, quando disponível, também é recalculada sobre essa base individual. Ao aplicar a reserva, a proteção existente contra sobreposição de grupos e agendamentos individuais permanece responsável pelo calendário.

As duas mensagens de falha foram diferenciadas: tema realmente ausente no acervo versus ausência de dados individuais para o cálculo. Ambas identificam o caminho completo, preservam os erros anotados e indicam como tentar novamente ou corrigir a seleção na própria tela. Ausência real orienta selecionar o tema atual em Adicionar um tema errado e, se necessário, atualizar o PDF do acervo.

Reprodução em cópia temporária do banco: o treino SUS-SP · Clínica Cirúrgica continha Neoplasias Císticas do Pâncreas dentro de Pâncreas. O código anterior reproduziu a mensagem genérica; o corrigido gerou cinco blocos, sem temas sem vaga, com limite de30questões por dia e início em05/11/2026. Nada foi aplicado ao banco ativo.

Verificação:60testes direcionados passaram em40,21s, incluindo modos equilibrado/personalizado, simulados completos/treinos por área, identidade do subtema após aplicação, capacidade diária, preservação de resultados e comparação de pesos/doses com o modo individual, com incidência específica e conjunta. Compilação e diff-check também passaram. Não foi repetida a suíte completa nesta correção pequena. Código anterior e evidências ficam em evidencias/correcao-erros-agrupados-2026-11-02. As cópias descartáveis foram removidas.
