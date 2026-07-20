# Changelog

Todas as alterações relevantes deste projeto são registradas neste arquivo. O detalhamento da solicitação e o prompt sanitizado de cada ciclo ficam em [`docs/HISTORICO_DE_ITERACOES.md`](docs/HISTORICO_DE_ITERACOES.md).

## [0.4.0] — 2026-07-20

### Adicionado

- Envio automático de notificações por e-mail para `pedreira.azulimperial@gramazini.com.br` em todas as ações principais do painel (Nova solicitação, Encaminhamento, Retorno do Almoxarifado e Dados de Compra).
- Configuração via variáveis de ambiente (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`).

[0.4.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.4.0

## [0.3.0] — 2026-07-20

### Removido

- Barra lateral (sidebar) que exibia informações de contexto da versão.

[0.3.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.3.0

## [0.2.1] — 2026-07-20

### Corrigido

- Compatibilidade de dependências com Python 3.14 no Streamlit Cloud.

[0.2.1]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.2.1

## [0.2.0] — 2026-07-20

### Atualizado

- Lista de empresas selecionáveis na nova solicitação de materiais, conforme cadastro oficial.

[0.2.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.2.0

## [0.1.0] — 2026-07-20

### Adicionado

- Tela Streamlit para criação de solicitações de materiais vinculadas a empresas.
- Inclusão, edição e remoção de itens com produto e quantidade.
- Geração de protocolo e acompanhamento de status.
- Triagem de solicitações entre almoxarifado e compras mediante acesso de atendimento.
- Painel de disponibilidade para almoxarifado e painel de dados de compra.
- Documentação funcional, histórico de iterações e orientação de segurança para a senha de atendimento.

[0.1.0]: https://github.com/kleberfreitas1990/GRM/releases/tag/v0.1.0
