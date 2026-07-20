# Histórico de Iterações

Este arquivo é o registro obrigatório das evoluções do repositório. Ao encerrar cada nova interação de desenvolvimento, deve-se acrescentar uma entrada no topo com a versão, o objetivo, o prompt sanitizado, as alterações, os arquivos afetados, a validação executada e a referência do commit.

> **Segurança:** prompts e registros nunca devem incluir tokens, senhas, chaves de API ou outros segredos. Quando uma solicitação original os contiver, eles devem ser omitidos ou substituídos pela expressão `[DADO SENSÍVEL OMITIDO]`.

---

## Iteração 005 — Versão 0.4.0 — 20 de julho de 2026

### Objetivo

Implementar o envio de notificações por e-mail para cada ação realizada no painel do sistema.

### Prompt sanitizado

> cada ação no painel por parte do solicitante e dos atendentes precisa vir uma copia pro email pedreira.azulimperial@gramazini.com.br

### Alterações realizadas

| Categoria | Descrição |
|---|---|
| Funcionalidade | Criação da função `enviar_email_notificacao` utilizando `smtplib`. |
| Integração | Inserção do envio de e-mail nas ações de: Nova solicitação, Encaminhamento (Triagem), Retorno do Almoxarifado e Dados de Compra. |
| Configuração | Variáveis de ambiente `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` e `SMTP_PASSWORD` para configuração segura do servidor de e-mail. |
| Versionamento | Atualização da versão da aplicação para `0.4.0`. |

### Arquivos afetados

| Arquivo | Finalidade |
|---|---|
| `almox_app.py` | Adição da lógica de envio de e-mail e chamadas nos pontos de ação. |
| `docs/HISTORICO_DE_ITERACOES.md` | Registro detalhado da iteração e do prompt. |
| `CHANGELOG.md` | Resumo da nova versão publicada. |

### Validação prevista

A versão deve ser validada verificando se as chamadas à função `enviar_email_notificacao` estão corretamente posicionadas após as ações principais e se as importações necessárias estão presentes. A configuração do SMTP será feita via variáveis de ambiente no ambiente de produção (Streamlit Cloud).

### Commit

A versão será publicada na ramificação `main` com a tag anotada `v0.4.0`. O identificador do commit poderá ser consultado diretamente no histórico do repositório após o envio.

---

## Iteração 004 — Versão 0.3.0 — 20 de julho de 2026

### Objetivo

Remover a barra lateral da aplicação conforme solicitado.

### Prompt sanitizado

> essa lateral nao precisa ok
> *(imagem da barra lateral mostrando GRM, Fluxo da versão 0.1.0, Ambiente de demonstração e Versão da aplicação: 0.2.1)*

### Alterações realizadas

| Categoria | Descrição |
|---|---|
| Interface | Remoção da função `renderizar_barra_lateral` e sua chamada em `main()`. |
| Versionamento | Atualização da versão da aplicação para `0.3.0`. |

### Arquivos afetados

| Arquivo | Finalidade |
|---|---|
| `almox_app.py` | Remoção da barra lateral e atualização de versão. |
| `docs/HISTORICO_DE_ITERACOES.md` | Registro detalhado da iteração e do prompt. |
| `CHANGELOG.md` | Resumo da nova versão publicada. |

### Validação prevista

A versão deve ser validada visualmente para garantir que a barra lateral foi removida com sucesso e o layout principal não foi comprometido.

### Commit

A versão será publicada na ramificação `main` com a tag anotada `v0.3.0`. O identificador do commit poderá ser consultado diretamente no histórico do repositório após o envio.

---

## Iteração 003 — Versão 0.2.1 — 20 de julho de 2026

### Objetivo

Corrigir incompatibilidade de dependências na execução em produção no Streamlit Cloud.

### Prompt sanitizado

> ModuleNotFoundError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
> Traceback:
> File "/mount/src/grm/almox\\_app.py", line 15, in \<module\>
>     import pandas as pd
> File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/\*\*init\*\*.py", line 46, in \<module\>
> File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/api.py", line 27, in \<module\>
> File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/\*\*init\*\*.py", line 1, in \<module\>
> File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/arrow/\*\*init\*\*.py", line 5, in \<module\>
> File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/arrow/array.py", line 80, in \<module\>
> File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/string\\_.py", line 70, in \<module\>
> File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/numpy\\_.py", line 37, in \<module\>

### Alterações realizadas

| Categoria | Descrição |
|---|---|
| Dependências | Relaxed da versão do pandas para aceitar qualquer versão 2.3.3 ou superior, compatível com Python 3.14. |

### Arquivos afetados

| Arquivo | Finalidade |
|---|---|
| `requirements.txt` | Ajuste da faixa de versão do pandas. |
| `docs/HISTORICO_DE_ITERACOES.md` | Registro detalhado da iteração e do prompt. |
| `CHANGELOG.md` | Resumo da nova versão publicada. |

### Validação prevista

A versão deve ser validada pela ausência de `ModuleNotFoundError` ao rodar no Streamlit Cloud, que utiliza Python 3.14.

### Commit

A versão será publicada na ramificação `main` com a tag anotada `v0.2.1`. O identificador do commit poderá ser consultado diretamente no histórico do repositório após o envio.

---

## Iteração 002 — Versão 0.2.0 — 20 de julho de 2026

### Objetivo

Atualizar a lista de empresas disponíveis para seleção na nova solicitação de materiais.

### Prompt sanitizado

> Na parte das empresas precisa constar essa lista:
> 214 - Ankara - tunas, Paraná
> 215 - Dover - Castro, Paraná
> 216 - Brazilian black - São Rafael, ES
> 217 - Dallas - Itaperuna, ES
> 218 - Azurite - Araçuaí, MG
> 219 - Valhalla - Governador Valadares, MG
> 220 - Magma - São Geraldo baixio, MG
> 221 - Polaris- livramento, Bahia
> 222 - Excalibur - rio do Pires, Bahia
> 223 - Azul Macaúbas - Boquira, Bahia
> 224 - Velvet - livramento, Bahia
> 225 - Jade - Jaguarari, Bahia
> 226 - Nacarado/ Sky pearl/ Montebello - Massapê, CE

### Alterações realizadas

| Categoria | Descrição |
|---|---|
| Cadastro | Substituição das empresas fictícias pela lista oficial fornecida. |
| Versionamento | Atualização da versão da aplicação para `0.2.0`. |

### Arquivos afetados

| Arquivo | Finalidade |
|---|---|
| `almox_app.py` | Inclusão da nova lista de empresas. |
| `docs/HISTORICO_DE_ITERACOES.md` | Registro detalhado da iteração e do prompt. |
| `CHANGELOG.md` | Resumo da nova versão publicada. |

### Validação prevista

A versão deve ser validada por compilação do código Python e inicialização do Streamlit para garantir que a nova lista é exibida corretamente.

### Commit

A versão será publicada na ramificação `main` com a tag anotada `v0.2.0`. O identificador do commit poderá ser consultado diretamente no histórico do repositório após o envio.

---

## Iteração 001 — Versão 0.1.0 — 20 de julho de 2026

### Objetivo

Criar a primeira tela Streamlit do projeto GRM conforme o fluxo de requisição de materiais fornecido.

### Prompt sanitizado

> No repositório **GRM**, criar uma tela Streamlit baseada no fluxo anexo: o solicitante escolhe uma empresa, inclui produtos e quantidades com possibilidade de edição, grava a solicitação e acompanha seu status. O atendente acessa uma área protegida por senha, direciona a solicitação ao almoxarifado ou às compras, e cada setor dispõe de um painel próprio. Registrar em cada alteração a versão e o prompt utilizado. `[DADO SENSÍVEL OMITIDO]`

### Alterações realizadas

| Categoria | Descrição |
|---|---|
| Interface | Implementação da tela única de requisições, com abas para solicitação, acompanhamento, atendimento, almoxarifado e compras. |
| Fluxo | Inclusão da triagem entre almoxarifado e compras e atualização de status da solicitação. |
| Segurança | Senha do atendimento configurável por variável de ambiente, sem inclusão de segredo no código. |
| Documentação | Criação da arquitetura da tela, changelog e histórico de iterações. |

### Arquivos afetados

| Arquivo | Finalidade |
|---|---|
| `almox_app.py` | Aplicação Streamlit. |
| `requirements.txt` | Dependências necessárias para execução. |
| `.gitignore` | Proteção contra inclusão acidental de arquivos sensíveis e temporários. |
| `docs/ARQUITETURA_DA_TELA.md` | Interpretação e regras do fluxo. |
| `CHANGELOG.md` | Resumo de versões publicadas. |
| `docs/HISTORICO_DE_ITERACOES.md` | Registro detalhado da iteração e do prompt. |
| `docs/VALIDACAO.md` | Evidências e resultados da validação local. |
| `tests/test_almox_app.py` | Testes das regras de itens e estados. |
| `tests/test_interface_streamlit.py` | Teste de carregamento dos componentes principais da tela. |

### Validação prevista

A versão foi validada por compilação do código Python, inicialização local do Streamlit, inspeção visual da tela inicial, verificação do diff e quatro testes automatizados aprovados. As limitações da automação sobre a edição em grade estão registradas em `docs/VALIDACAO.md`.

### Commit

A versão será publicada na ramificação `main` com a tag anotada `v0.1.0`. O identificador do commit poderá ser consultado diretamente no histórico do repositório após o envio.
