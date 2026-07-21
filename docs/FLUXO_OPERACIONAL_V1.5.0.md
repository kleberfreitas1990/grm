# Fluxo Operacional de Solicitações — Versão 1.5.0

## Objetivo

Este documento define o fluxo operacional da evolução **Compras → Almoxarifado → Solicitante**. A finalidade é tornar visível, para o solicitante, a quantidade e a situação das solicitações em andamento e garantir que o almoxarifado registre o recebimento de compras e o envio do material ao destinatário.

> O fluxo foi especificado a partir do requisito textual desta iteração. Quando o anexo visual for disponibilizado, seus elementos de apresentação poderão ser refinados sem alterar as regras de negócio definidas neste documento.

## Estados da solicitação

| Ordem | Status exibido | Responsável pela próxima ação | Interpretação para o solicitante |
| --- | --- | --- | --- |
| 1 | **Em análise no almoxarifado** | Almoxarifado | O estoque está sendo verificado. |
| 2 | **Em processo de compra** | Compras | Há item indisponível ou parcial e a aquisição está em tratamento. |
| 3 | **Em processo de autorização** | Compras | A aquisição aguarda aprovação interna. |
| 4 | **Aguardando recebimento no almoxarifado** | Almoxarifado | A compra foi concluída e o material aguarda chegada e conferência. |
| 5 | **Aguardando envio ao solicitante** | Almoxarifado | O material está disponível para separação e despacho ao solicitante. |
| 6 | **Produto enviado ao solicitante** | Concluído | O almoxarifado registrou o envio e o responsável pelo despacho. |

Os estados legados **Aguardando triagem**, **Compra solicitada** e **Atendido pelo almoxarifado** continuarão sendo exibidos e tratados pela aplicação para não invalidar registros anteriores.

## Regras de transição

| Evento | Origem | Destino | Registro obrigatório |
| --- | --- | --- | --- |
| Conferência com item parcial ou indisponível | Em análise no almoxarifado | Em processo de compra | Conferência de estoque e observação do almoxarifado. |
| Conferência com todos os itens disponíveis | Em análise no almoxarifado | Aguardando envio ao solicitante | Conferência de estoque e observação do almoxarifado. |
| Compra ainda não aprovada | Em processo de compra | Em processo de autorização | Dados da compra, responsável e observação. |
| Compra concluída | Em processo de compra ou Em processo de autorização | Aguardando recebimento no almoxarifado | Fornecedor, responsável, previsão e observação da compra. |
| Recebimento físico da compra | Aguardando recebimento no almoxarifado | Aguardando envio ao solicitante | Recebido por, data/hora, documento de referência e observação. |
| Despacho ao solicitante | Aguardando envio ao solicitante | Produto enviado ao solicitante | Enviado por, destinatário, data/hora, modalidade de entrega e observação. |

## Visão do solicitante

A tela de acompanhamento apresentará um resumo visual antes da lista de solicitações. O resumo mostrará o total **Em andamento** e a distribuição entre análise de estoque, compras, recebimento e envio. Uma legenda explicará a cor e o significado de cada estado.

Cada solicitação exibirá uma linha do tempo resumida. Quando o material for enviado, os detalhes de despacho informarão claramente **quem enviou**, quando ocorreu o envio, para quem foi destinado e as observações registradas pelo almoxarifado.

## Dados operacionais persistidos

| Grupo de dados | Campos |
| --- | --- |
| Compra | Status da compra, fornecedor, previsão, responsável, centro de custo e observação. |
| Recebimento no almoxarifado | Recebido por, data/hora de recebimento, documento de referência e observação. |
| Envio ao solicitante | Enviado por, destinatário, data/hora de envio, modalidade de entrega e observação. |
| Histórico de status | Status, data/hora, responsável e observação de cada movimentação. |

## Critério de conclusão

A solicitação será considerada concluída para os indicadores da tela do solicitante somente no status **Produto enviado ao solicitante**. Registros legados com status **Atendido pelo almoxarifado** permanecerão contabilizados como concluídos para preservar o histórico anterior.
