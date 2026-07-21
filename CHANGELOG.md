# Changelog

Todas as alterações relevantes deste projeto são registradas neste arquivo. O detalhamento da solicitação e o prompt sanitizado de cada ciclo ficam em [`docs/HISTORICO_DE_ITERACOES.md`](docs/HISTORICO_DE_ITERACOES.md).

## [1.1.0] — 2026-07-21

### Adicionado

- Persistência via TiDB Cloud para que as solicitações não se percam em deploys ou hibernações.
- Fallback automático para SQLite em ambiente de desenvolvimento local.
- Classes abstratas `SQLiteEngine` e `TiDBEngine` unificadas por `_DBManager`.

### Alterado

- `db.py` completamente reescrito com suporte dual ao banco de dados.
- `requirements.txt` com dependências SQL (SQLAlchemy, PyMySQL, mysqlclient).
- `.streamlit/secrets.toml.example` com template de conexão TiDB Cloud.

[1.1.0]: https://github.com/kleberfreitas1990/GRM/releases/tag/v1.1.0

## [1.0.3] — 2026-07-21

### Adicionado

- Grade visual de requisições no painel do Almoxarifado com cards e expanders para cada solicitação.
- Marcação de disponibilidade por item (Disponível / Parcial / Indisponível) em cada solicitação.
- Encaminhamento automático para Compras quando algum item estiver indisponível ou parcial.
- Botão "Deixar pendente" para adiar a decisão de atendimento.

### Alterado

- Painel do Almoxarifado reescrito: cards visuais substituem o selectbox anterior.

[1.0.3]: https://github.com/kleberfreitas1990/GRM/releases/tag/v1.0.3

## [1.0.2] — 2026-07-21

### Adicionado

- Tabela `usuarios` no banco de dados SQLite com os usuários `compras` e `almoxarifado`.
- Inserção automática das credenciais (senha `Grm@2026`) no banco ao inicializar a aplicação.
- Autenticação agora busca a senha diretamente no banco de dados, sem depender de variáveis de ambiente ou secrets do Streamlit Cloud.

### Alterado

- Funções `obter_senha_configurada()` e `usuario_tem_permissao()` simplificadas para usar o banco.
- Testes atualizados para validar a leitura da senha do banco.

[1.0.2]: https://github.com/kleberfreitas1990/GRM/releases/tag/v1.0.2

## [1.0.1] — 2026-07-21

### Adicionado

- Grade visual de solicitações na área "Acompanhar status" com cards mostrando protocolo, empresa, resumo dos itens e chip de status colorido.
- Expander "Ver detalhes completos" em cada card para exibir dados, itens, retorno do almoxarifado e dados de compra.
- Nova opção "Todas as solicitações" no método de busca da área de acompanhamento.

[1.0.1]: https://github.com/kleberfreitas1990/GRM/releases/tag/v1.0.1

## [1.0.0] — 2026-07-21

### Adicionado

- Tela inicial redesenhada com apenas dois botões: **SOLICITANTE** e **ATENDENTE**.
- Nova função `tela_login_atendente()`: o Atendente seleciona seu perfil (Almoxarifado ou Compras) e digita a senha antes de acessar qualquer painel.
- Painel do Almoxarifado com resumo visual de solicitações pendentes agrupadas por empresa.
- Controle de modo de visualização no painel do Almoxarifado: "Por empresa" ou "Todas as solicitações".

### Alterado

- Fluxo de acesso do Atendente unificado: login único com seleção de perfil, em vez de botões separados por setor na tela inicial.
- Testes atualizados para refletir a nova estrutura de navegação.

[1.0.0]: https://github.com/kleberfreitas1990/GRM/releases/tag/v1.0.0

## [0.11.0] — 2026-07-21

### Alterado

- O usuário **suprimentos** foi renomeado para **compras**.
- A senha padrão para os usuários **compras** e **almoxarifado** foi alterada para `Grm@2026`.

[0.11.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.11.0

## [0.10.0] — 2026-07-21

### Adicionado

- Novos acessos internos **suprimentos** e **almoxarifado** na tela inicial.
- Permissões separadas: suprimentos atende e registra compras; almoxarifado registra exclusivamente o retorno de estoque.
- Modelo `.streamlit/secrets.toml.example` para configuração segura das credenciais de implantação.
- Testes das contas setoriais, das permissões e da leitura da senha por variável de ambiente.

### Segurança

- Senhas lidas exclusivamente de segredos da implantação Streamlit ou de variáveis de ambiente; nenhuma credencial é versionada.
- Comparação de senha com `hmac.compare_digest`.

[0.10.0]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.10.0

## [0.9.4] — 2026-07-20

### Corrigido

- Substituído o botão "Adicionar outro material" por `st.form_submit_button` para corrigir erro de API do Streamlit.

[0.9.4]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.9.4

## [0.9.3] — 2026-07-20

### Modificado

- Movido o botão "Adicionar outro material" para aparecer logo abaixo do último material cadastrado no formulário.

[0.9.3]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.9.3

## [0.9.2] — 2026-07-20

### Corrigido

- Removido o botão "Adicionar outro material" de dentro do formulário para corrigir erro de API do Streamlit.

[0.9.2]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.9.2

## [0.9.1] — 2026-07-20

### Adicionado

- Substituição da tabela editável por campos individuais para a inserção de materiais, melhorando a responsividade em telas pequenas (celulares).
- Adicionado botão para adicionar novos campos de materiais dinamicamente.

### Modificado

- Removida a obrigatoriedade do nome completo no campo "Qual é o seu nome?".

[0.9.1]: https://github.com/kleberfreitas1990/grm/releases/tag/v0.9.1

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
