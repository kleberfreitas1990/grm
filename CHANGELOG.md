# Changelog

Todas as alterações relevantes deste projeto são registradas neste arquivo. O detalhamento da solicitação e o prompt sanitizado de cada ciclo ficam em [`docs/HISTORICO_DE_ITERACOES.md`](docs/HISTORICO_DE_ITERACOES.md).

## [0.9.0] — 2026-07-20

### Adicionado

- Redesenho completo do fluxo do solicitante para ser extremamente intuitivo e acessível.
- Remoção das abas na tela do solicitante; o formulário de "Nova solicitação" agora ocupa a tela inteira por padrão.
- Textos de ajuda simplificados e diretos no formulário para facilitar o preenchimento por pessoas com dificuldades tecnológicas.
- Adicionada animação de sucesso (`st.balloons()`) e mensagem clara com o código de acompanhamento após o envio.

[0.9.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.9.0

## [0.8.1] — 2026-07-20

### Corrigido

- Removido o parâmetro `height` não suportado dos botões da tela inicial, corrigindo o `TypeError` que quebrava a aplicação ao carregar.

[0.8.1]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.8.1

## [0.8.0] — 2026-07-20

### Adicionado

- Tela inicial simplificada com menu direto para escolha de perfil (Solicitante ou Atendente).
- Fluxo de Solicitante direciona imediatamente para as abas de Nova Solicitação e Acompanhar Status.
- Fluxo de Atendente direciona imediatamente para as abas de Atendimento, Almoxarifado e Compras.

[0.8.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.8.0

## [0.7.2] — 2026-07-20

### Corrigido

- Tema da aplicação alterado para modo claro (fundo branco), corrigindo o visual escuro que ocorria em dispositivos móveis.

[0.7.2]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.7.2

## [0.7.1] — 2026-07-20

### Corrigido

- Layout da página de "Nova solicitação" agora é renderizado sequencialmente em dispositivos móveis, evitando quebra de colunas e garantindo que todos os campos e botões fiquem visíveis.

[0.7.1]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.7.1

## [0.7.0] — 2026-07-20

### Adicionado

- Persistência de dados utilizando banco de dados SQLite (`db.py`).
- As solicitações agora são salvas permanentemente e não se perdem ao fechar o navegador ou reiniciar a aplicação.

[0.7.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.7.0

## [0.6.0] — 2026-07-20

### Alterado

- Layout da aplicação agora é responsivo. Formulários e cards se ajustam melhor para uso em celulares (solicitantes) e mantém o design otimizado para desktops (atendentes).

[0.6.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.6.0

## [0.5.0] — 2026-07-20

### Adicionado

- Opção de consulta por empresa na aba de acompanhamento de status, listando todas as solicitações de uma empresa selecionada.

[0.5.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.5.0

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
