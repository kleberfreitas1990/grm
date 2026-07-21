# Validação Visual — Versão 1.5.0

## Prévia local isolada

A prévia local da aplicação foi aberta em ambiente SQLite isolado em 21 de julho de 2026. A tela inicial carregou sem exceções visíveis e apresentou a identidade visual esperada, os acessos **SOLICITANTE** e **ATENDENTE** e a indicação da versão **1.5.0**.

| Item verificado | Resultado |
| --- | --- |
| Carregamento da aplicação | Aprovado |
| Cabeçalho e identidade visual | Aprovado |
| Acesso Solicitante | Visível |
| Acesso Atendente | Visível |
| Versão exibida | 1.5.0 |

As verificações seguintes cobrirão os indicadores de solicitações em andamento, a legenda do fluxo e os painéis de recebimento e envio do almoxarifado.

## Jornada do solicitante

A entrada pela opção **SOLICITANTE** carregou corretamente o formulário de nova solicitação. A tela apresentou os campos de empresa, nome, setor, itens e quantidade, além do acesso direto **Verificar o status das minhas solicitações**. Não foram observadas exceções durante essa navegação.

| Item verificado | Resultado |
| --- | --- |
| Formulário de nova solicitação | Aprovado |
| Inclusão de múltiplos materiais | Visível |
| Acesso ao acompanhamento de status | Visível |
| Erros de renderização | Não identificados |

## Acompanhamento do solicitante

A tela de acompanhamento carregou com dados temporários locais e exibiu corretamente o resumo de solicitações em andamento. Foram confirmados os blocos visuais de **Em andamento**, **Estoque**, **Compras**, **Recebimento** e **Envio**, bem como a legenda textual de cores. A lista apresentou os cartões por solicitação, os chips de status e a abertura de detalhes.

A expansão de uma solicitação confirmou a linha do tempo em cinco etapas — Solicitação, Estoque, Compras, Recebimento e Envio — e o histórico de movimentações com data/hora, status, responsável e observação. Também foram observados os detalhes operacionais de recebimento e envio nos registros temporários correspondentes.

| Item verificado | Resultado |
| --- | --- |
| Indicador de solicitações em andamento | Aprovado |
| Distribuição por estoque, compras, recebimento e envio | Aprovado |
| Legenda visual do fluxo | Aprovado |
| Linha do tempo da solicitação | Aprovado |
| Histórico de movimentações | Aprovado |
| Exibição de quem enviou o produto | Aprovado |

## Entrada operacional

A jornada de atendente abriu corretamente o formulário de acesso, com seleção de perfil, campo de senha e ação de entrada. A validação dos painéis será feita com o perfil Almoxarifado na prévia local isolada.

> Observação técnica: o seletor de perfil utiliza um componente de lista acessível; a prévia permanece funcional e a seleção será validada pelo mecanismo próprio do componente.

A seleção do perfil **Almoxarifado** foi confirmada na prévia por preenchimento do seletor acessível. Nenhuma alteração de dados foi efetuada nesta etapa.

## Painel do almoxarifado

O acesso do perfil **Almoxarifado** foi validado na prévia local. O painel carregou os indicadores operacionais e as três etapas implementadas: **Conferir estoque**, **Receber compras** e **Enviar materiais**. As solicitações temporárias foram distribuídas corretamente por etapa.

Os formulários exibiram os campos previstos para registro do recebimento — responsável, data/hora, documento e observação — e para registro do envio — responsável, destinatário, data/hora, modalidade e observação. A validação foi apenas visual; nenhuma confirmação de recebimento ou envio foi submetida durante a prévia.

| Item verificado | Resultado |
| --- | --- |
| Indicadores operacionais do almoxarifado | Aprovado |
| Painel de conferência de estoque | Aprovado |
| Formulário de recebimento físico | Aprovado |
| Formulário de envio ao solicitante | Aprovado |
| Ausência de gravações nos dados de demonstração | Confirmada |
