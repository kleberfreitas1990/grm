# Arquitetura da Tela de Requisições

**Versão do documento:** 0.10.0
**Data:** 21 de julho de 2026
**Responsável:** Manus AI

## Objetivo

Esta primeira entrega transforma o fluxo fornecido em uma interface única de gestão de requisições de materiais. A solução foi planejada como um protótipo funcional em Streamlit, priorizando a navegação entre o solicitante, o atendimento, o almoxarifado, as compras e o acompanhamento de status.

## Mapeamento do fluxo para a interface

| Etapa do fluxo recebido | Componente proposto | Resultado esperado |
|---|---|---|
| Solicitante → lista de empresas | Seleção de empresa na aba **Nova solicitação** | A requisição fica vinculada à empresa escolhida. |
| Inserir produto e quantidade, com opção de editar | Formulário de inclusão e tabela editável de itens | O solicitante pode criar, conferir e ajustar os itens antes de gravar. |
| Gravar | Botão de envio com geração de protocolo | A solicitação é criada com status inicial **Aguardando triagem**. |
| Acompanhar status | Aba **Acompanhar status** | O solicitante consulta o andamento pelo protocolo. |
| Suprimentos → usuário e senha | Acesso identificado como **suprimentos**, com senha configurável | Permite triagem e registro de compras. |
| Decisão entre almoxarifado e compras | Escolha de encaminhamento após o acesso de suprimentos | A solicitação é direcionada ao setor responsável. |
| Almoxarifado → usuário e senha | Acesso identificado como **almoxarifado**, com senha configurável | Permite exclusivamente o retorno de disponibilidade. |
| Painel do almoxarifado | Tabela com produto, quantidade e disponibilidade | A equipe registra disponibilidade e atualiza o status. |
| Painel de compras | Formulário com campos de compra e priorização | A equipe de suprimentos registra os dados necessários para a cotação ou compra. |

## Regras de acesso

A aplicação mantém as solicitações em banco SQLite local e usa dois acessos internos com permissões separadas. O usuário **suprimentos** visualiza somente as áreas de atendimento e compras; o usuário **almoxarifado** visualiza somente o painel de estoque.

As senhas devem ser definidas por `GRM_SUPRIMENTOS_PASSWORD` e `GRM_ALMOXARIFADO_PASSWORD`, por variável de ambiente ou por segredos da implantação Streamlit. O arquivo `.streamlit/secrets.toml` real é ignorado pelo Git, e o modelo versionado `.streamlit/secrets.toml.example` não contém credenciais. Senhas não devem ser colocadas no código, na documentação ou em commits.

## Estados previstos para uma solicitação

| Status | Significado | Próxima responsabilidade |
|---|---|---|
| Aguardando triagem | Solicitação gravada e aguardando análise inicial. | Atendente |
| Em análise no almoxarifado | Solicitação encaminhada para verificação de estoque. | Almoxarifado |
| Em processo de compra | Solicitação encaminhada para aquisição. | Compras |
| Atendido pelo almoxarifado | Estoque confirmado e atendimento concluído. | Solicitante |
| Compra solicitada | Dados de compra registrados para prosseguimento. | Compras |

## Evoluções recomendadas

As próximas evoluções recomendadas incluem autenticação corporativa com gerenciamento centralizado de usuários, expiração de sessão, recuperação de senha, trilha de auditoria por ação e cadastro real de empresas e produtos.
