# Prioridade dos temas novos ou com pouca prática

Esclarecimento do usuário: Diálise pode manter prioridade como reforço de erro de simulado. Não alterar essas reservas nem sua precedência; a prioridade solicitada se refere à seleção ordinária de temas não vistos ou com poucas questões e alta incidência institucional.

Diagnóstico: reservas de correção explicam o bloco de Diálise. Na seleção ordinária havia duas falhas: o acervo importado de uma questão reduzia o bloco indicado a uma questão mesmo quando o modelo já recomendava complemento; e o otimizador por cotas podia trocar um piso viável de temas novos por mais volume de revisões.

Correção: capacidade de prática dos temas novos separada do tamanho documental do acervo pequeno (somente balanced_v2, sem expandir lotes vinculados ou correções de simulados). Quantidades originais permanecem explícitas; UI informa buscar complemento no banco completo. O complemento não é classificado como repetição nem como disponibilidade comprovada, e aparece separadamente no JSON e no CSV. Otimização atende primeiro o piso adaptativo protegido quando viável, depois o volume total. Demais ordenações por incidência, evidência, tempo sem contato e cotas existentes permanecem.

Revisão independente encontrou dois casos corrigidos: complemento classificado indevidamente como repetição e bloco preservado/reagendado voltando a uma questão. Regressões comprovam ambos. As reservas reais de correção continuam precedendo a seleção ordinária conforme o esclarecimento do usuário.

Backup: evidencias/prioridade-reforcos-2026-11-08/antes.sqlite3 e codigo-antes.zip. Nenhuma incidência, convicção, data de contato ou registro de questões foi transcrito do print ou substituído. A correção inicialmente investigada das reservas automáticas foi descartada após o esclarecimento do usuário.
