# Arquitetura da Tela de Requisições

**Versão do documento:** 0.1.0
**Data:** 20 de julho de 2026
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
| Atendente → inserir senha | Aba **Atendimento**, com validação de senha configurável | O acesso às rotinas internas é separado da solicitação. |
| Decisão entre almoxarifado e compras | Escolha de encaminhamento após o acesso do atendente | A solicitação é direcionada ao setor responsável. |
| Painel do almoxarifado | Tabela com produto, quantidade e disponibilidade | A equipe registra disponibilidade e atualiza o status. |
| Painel de compras | Formulário com campos de compra e priorização | A equipe registra os dados necessários para a cotação ou compra. |

## Regras da versão inicial

A versão 0.1.0 mantém os dados em memória durante a sessão do navegador. Assim, ela demonstra integralmente o fluxo de tela, mas não substitui uma base de dados, autenticação corporativa ou trilha de auditoria persistente.

A senha do atendimento deve ser configurada pela variável de ambiente `GRM_ATTENDANT_PASSWORD`. Caso ela não esteja definida, a aplicação sinalizará explicitamente que está em modo de demonstração; esse comportamento não deve ser utilizado como controle de acesso em produção.

## Estados previstos para uma solicitação

| Status | Significado | Próxima responsabilidade |
|---|---|---|
| Aguardando triagem | Solicitação gravada e aguardando análise inicial. | Atendente |
| Em análise no almoxarifado | Solicitação encaminhada para verificação de estoque. | Almoxarifado |
| Em processo de compra | Solicitação encaminhada para aquisição. | Compras |
| Atendido pelo almoxarifado | Estoque confirmado e atendimento concluído. | Solicitante |
| Compra solicitada | Dados de compra registrados para prosseguimento. | Compras |

## Evoluções recomendadas

A próxima etapa técnica deve substituir os dados de sessão por armazenamento persistente, autenticação por usuário e perfis de acesso, cadastro real de empresas e produtos, notificação de mudanças de status e histórico por requisição.
