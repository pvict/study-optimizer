# Acesso online privado

> Execução: Superpowers executing-plans, com testes antes da implementação.

**Objetivo:** usar o mesmo app no celular com o PC desligado, sem cobrança e sem publicar dados no GitHub.

**Arquitetura:** Streamlit Community Cloud executa Python. Supabase guarda objetos comprimidos e um manifesto versionado de SQLite, originais e exportações. Um arrendamento de escrita e comparação de revisão impedem sobrescritas entre servidores. O app local continua independente.

**Restrições:** nenhum acesso automático à Osler; preservar histórico e originais; não mudar algoritmos de estudo; credenciais somente em secrets; acesso privado e senha adicional; falhar fechado quando o armazenamento não responder. A nuvem gratuita pode hibernar/pausar; não prometer disponibilidade contínua.

## Entregas

- [x] Persistência: testes de reinício, concorrência, gravação recusada, caminhos inseguros e integridade; conexão TLS validada, manifesto e SQL com RLS e papel restrito.
- [x] Interface: entrada cloud separada, senha, importação inicial de backup verificado, persistência antes do toast, proteção para fragments/dialogs e download de recuperação. Manter execução local sem rede.
- [ ] Publicação: backup local, fonte completa em branch de deploy, dependências/configuração Linux, projeto Supabase gratuito e app privado; migrar e verificar dados reais sem criar resultados fictícios.
- [ ] Verificação: testes locais e persistência real, revisão independente, URL no celular, instruções para backup e limites gratuitos.

## Riscos para revisão

- Confirmação em dialog roda fora da execução completa: precisa adquirir o mesmo bloqueio.
- Falha de rede depois de commit: reconhecer o manifesto já salvo sem repetir a alteração.
- Servidor antigo com estado pendente: não substituir dados remotos mais novos.
- Segredos e dados pessoais não podem aparecer no Git, mensagens de erro ou navegador sem autenticação.
- Restauração local em outra pasta não pode criar uma segunda base desconectada da nuvem.

## Registro

Inspeção: branch codex/attention-menu com mudanças anteriores preservadas; SQLite ~10 MiB, originais ~2 MiB, exportações ~46 MiB. Nenhum dado enviado antes de configurar privacidade. Usuário criou contas em ambos os serviços.

Decisão: usar conexão PostgreSQL via session pooler, com papel osler_cloud limitado às cinco funções. Evita hospedar a senha administrativa ou uma service_role abrangente. Certificado CA baixado da URL oficial exibida no painel; TLS verify-full verificado em conexão real. Permissões reais confirmadas: app sem acesso direto ao schema, anon/authenticated sem execução.

Revisão independente identificou falha de finalização de formulário após erro remoto e pendência marcada tarde demais quando snapshot falhava. Ambos corrigidos e cobertos por regressões. 44 testes de nuvem/UI afetada passaram; após as correções, 21 testes de nuvem, confirmação e importação local passaram, incluindo 14 testes cloud. Branch de deploy gerado com índice separado, compilação do artefato, overlays verificados e varredura sem credenciais. Publicado no GitHub em codex/cloud-mobile-20261109; checkout local preservado.
