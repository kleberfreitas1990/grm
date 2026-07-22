"""Aplicação Streamlit para o fluxo de requisições de materiais do GRM.

Versão da aplicação: 1.1.0
Os dados são persistidos em TiDB Cloud (com fallback para SQLite local),
garantindo que as solicitações não se percam ao reiniciar a aplicação.
"""

from __future__ import annotations

import hmac
import os
import smtplib
import ssl
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import Any

import db
import pandas as pd
import streamlit as st


APP_VERSION = "1.6.1"

# Configuração de Fuso Horário (Brasília - GMT-3)
TZ_BRASILIA = timezone(timedelta(hours=-3))

def agora_br() -> datetime:
    """Retorna o horário atual no fuso de Brasília."""
    return datetime.now(TZ_BRASILIA)

# As senhas são lidas de segredos de implantação ou de variáveis de ambiente.
# Nenhuma credencial deve ser incluída no repositório.
USUARIOS_CONFIGURADOS: dict[str, dict[str, Any]] = {
    "compras": {
        "rotulo": "Compras",
        "chave_senha": "GRM_COMPRAS_PASSWORD",
        "permissoes": ("atendimento", "compras"),
    },
    "almoxarifado": {
        "rotulo": "Almoxarifado",
        "chave_senha": "GRM_ALMOXARIFADO_PASSWORD",
        "permissoes": ("almoxarifado",),
    },
}

def _ler_secret(chave: str, padrao: str = "") -> str:
    """Lê credencial do st.secrets (Streamlit Cloud) com fallback para variável de ambiente."""
    # O Streamlit Cloud às vezes converte as chaves para minúsculas internamente
    try:
        if chave in st.secrets:
            return str(st.secrets[chave])
        chave_lower = chave.lower()
        if chave_lower in st.secrets:
            return str(st.secrets[chave_lower])
    except Exception:
        pass
    return os.getenv(chave, padrao)


def _obter_config_smtp():
    """Retorna tupla (host, port, user, password, notification_email) lendo do st.secrets ou env."""
    # Fallback direto para garantir funcionamento no Streamlit Cloud
    host = _ler_secret("SMTP_HOST", "smtp.gmail.com")
    port = int(_ler_secret("SMTP_PORT", "587"))
    user = _ler_secret("SMTP_USER", "integracao@gramazini.com.br")
    password = _ler_secret("SMTP_PASSWORD", "qxxr qbst vfdb vwra")
    notification_email = _ler_secret("NOTIFICATION_EMAIL", "pedreira.info@gramazini.com.br")
    return host, port, user, password, notification_email


def enviar_email_notificacao(assunto: str, corpo: str) -> bool:
    smtp_host, smtp_port, smtp_user, smtp_password, notification_email = _obter_config_smtp()

    if not smtp_user or not smtp_password:
        # Silenciar aviso automático para não poluir a interface
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_user
        msg["To"] = notification_email
        msg["Subject"] = f"[GRM] {assunto}"
        msg.attach(MIMEText(corpo, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

EMPRESAS = [
    "Selecione uma empresa",
    "214 - Ankara - tunas, Paraná",
    "215 - Dover - Castro, Paraná",
    "216 - Brazilian black - São Rafael, ES",
    "217 - Dallas - Itaperuna, ES",
    "218 - Azurite - Araçuaí, MG",
    "219 - Valhalla - Governador Valadares, MG",
    "220 - Magma - São Geraldo baixio, MG",
    "221 - Polaris- livramento, Bahia",
    "222 - Excalibur - rio do Pires, Bahia",
    "223 - Azul Macaúbas - Boquira, Bahia",
    "224 - Velvet - livramento, Bahia",
    "225 - Jade - Jaguarari, Bahia",
    "226 - Nacarado/ Sky pearl/ Montebello - Massapê, CE",
]

STATUS_META = {
    "Aguardando triagem": ("#F59E0B", "Solicitação registrada e aguardando atendimento."),
    "Em análise no almoxarifado": ("#2563EB", "O almoxarifado está verificando o estoque."),
    "Em processo de compra": ("#7C3AED", "A solicitação está em tratamento pelo setor de compras."),
    "Em processo de autorização": ("#9333EA", "A compra aguarda a autorização necessária."),
    "Compra solicitada": ("#DB2777", "Os dados de compra foram registrados."),
    "Aguardando recebimento no almoxarifado": ("#EA580C", "A compra foi concluída e aguarda chegada ao almoxarifado."),
    "Aguardando envio ao solicitante": ("#0891B2", "O material está disponível para separação e envio."),
    "Produto enviado ao solicitante": ("#059669", "O almoxarifado registrou o envio ao solicitante."),
    "Atendido pelo almoxarifado": ("#059669", "Registro legado concluído pelo almoxarifado."),
}

STATUS_CONCLUIDOS = {"Produto enviado ao solicitante", "Atendido pelo almoxarifado"}
STATUS_COMPRAS = {"Em processo de compra", "Em processo de autorização", "Compra solicitada"}
STATUS_RECEBIMENTO = {"Aguardando recebimento no almoxarifado"}
STATUS_ENVIO = {"Aguardando envio ao solicitante"}


def configurar_pagina() -> None:
    """Configura a identidade visual e o cabeçalho da aplicação."""
    st.set_page_config(
        page_title="GRM | Gestão de Requisições de Materiais",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
            /* Estilos Globais e Responsivos */
            .stApp { background: #F7F9FC; }
            [data-testid="stHeader"] { background: rgba(0, 0, 0, 0); }

            /* Ajuste para Mobile (Solicitantes) */
            @media (max-width: 768px) {
                .grm-hero { padding: 1.2rem 1rem; margin-bottom: 1rem; }
                .grm-hero h1 { font-size: 1.4rem; }
                .metric-card { min-height: auto; padding: 0.8rem; }
                .metric-card .value { font-size: 1.4rem; }
                .flow-step { min-height: auto; padding: 0.8rem; margin-bottom: 10px; }
                .btn-perfil-container { flex-direction: column !important; }
            }

            /* Estilos para Desktop e Tablets */
            .grm-hero {
                border-radius: 18px;
                padding: 1.8rem 2rem;
                color: white;
                background: linear-gradient(120deg, #0F3D62 0%, #126E82 52%, #14B8A6 100%);
                box-shadow: 0 12px 30px rgba(15, 61, 98, .18);
                margin-bottom: 1.2rem;
            }
            .grm-hero h1 { margin: 0; font-size: 2rem; }
            .grm-hero p { margin: .45rem 0 0; opacity: .92; font-size: 1rem; }

            .metric-card {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
                padding: 1rem 1.15rem;
                min-height: 106px;
                box-shadow: 0 4px 16px rgba(15, 23, 42, .04);
            }
            .metric-card .label { color: #64748B; font-size: .82rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
            .metric-card .value { color: #0F172A; font-size: 1.8rem; font-weight: 800; margin-top: .15rem; }
            .metric-card .caption { color: #64748B; font-size: .82rem; }

            .status-chip {
                border-radius: 999px;
                color: white;
                display: inline-block;
                font-size: .78rem;
                font-weight: 800;
                letter-spacing: .015em;
                margin: .1rem 0;
                padding: .35rem .7rem;
            }

            .flow-step {
                background: #FFFFFF;
                border: 1px solid #DCE5EF;
                border-radius: 12px;
                color: #1E293B;
                min-height: 100px;
                padding: 1rem;
                text-align: center;
            }
            .flow-step .number {
                align-items: center;
                background: #E0F2FE;
                border-radius: 50%;
                color: #0369A1;
                display: inline-flex;
                font-size: .82rem;
                font-weight: 800;
                height: 26px;
                justify-content: center;
                width: 26px;
            }
            .flow-step strong { display: block; margin: .42rem 0 .2rem; }
            .flow-step span { color: #64748B; font-size: .78rem; }
            .flow-step.done { background: #ECFDF5; border-color: #6EE7B7; }
            .flow-step.done .number { background: #D1FAE5; color: #047857; }
            .flow-step.active { background: #EFF6FF; border-color: #60A5FA; box-shadow: 0 0 0 2px rgba(37, 99, 235, .10); }
            .flow-step.active .number { background: #DBEAFE; color: #1D4ED8; }
            .legend-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: .8rem 1rem; min-height: 96px; }
            .legend-card .legend-value { color: #0F172A; font-size: 1.55rem; font-weight: 800; }
            .legend-card .legend-label { color: #475569; font-size: .8rem; font-weight: 700; }
            .legend-card .legend-detail { color: #64748B; font-size: .74rem; }
            .small-note { color: #64748B; font-size: .83rem; }

            /* Resumo de pendências por empresa */
            .empresa-card {
                background: white;
                border: 1px solid #E2E8F0;
                border-left: 5px solid #2563EB;
                border-radius: 10px;
                padding: 0.8rem 1rem;
                margin-bottom: 0.6rem;
                box-shadow: 0 2px 8px rgba(15, 23, 42, .04);
            }
            .empresa-card .empresa-nome { font-weight: 700; color: #0F172A; font-size: 1rem; }
            .empresa-card .empresa-qtd { color: #2563EB; font-weight: 800; font-size: 1.2rem; }
            .empresa-card .empresa-label { color: #64748B; font-size: .8rem; }

            /* Melhoria nos Formulários Mobile */
            @media (max-width: 768px) {
                [data-testid="stForm"] > div {
                    flex-direction: column !important;
                }
                [data-testid="stForm"] > div > div {
                    width: 100% !important;
                    padding: 0 !important;
                    margin-bottom: 10px !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inicializar_estado() -> None:
    """Inicializa somente os dados que precisam sobreviver às interações da sessão."""
    st.session_state.setdefault("solicitacoes", db.carregar_todas())
    st.session_state.setdefault("sequencia_protocolo", db.obter_sequencia_protocolo())
    st.session_state.setdefault("usuario_autenticado", "")
    st.session_state.setdefault("ultimo_protocolo", "")


def gerar_protocolo() -> str:
    """Gera um identificador legível para acompanhamento da solicitação."""
    sequencia = db.obter_sequencia_protocolo()
    return f"GRM-{agora_br():%Y%m%d}-{sequencia:04d}"


def normalizar_itens(dados: pd.DataFrame) -> list[dict[str, Any]]:
    """Remove linhas incompletas e padroniza itens inseridos pelo solicitante."""
    itens = dados.copy()
    if itens.empty:
        return []

    # Padronizar nomes das colunas para Capitalizado (Produto, Quantidade)
    itens.columns = [str(c).capitalize() for c in itens.columns]

    if "Produto" not in itens.columns:
        return []

    itens["Produto"] = itens["Produto"].fillna("").astype(str).str.strip()
    
    qtd_col = "Quantidade" if "Quantidade" in itens.columns else itens.columns[1] if len(itens.columns) > 1 else ""
    if qtd_col:
        itens["Quantidade"] = pd.to_numeric(itens[qtd_col], errors="coerce").fillna(0)
        itens = itens[(itens["Produto"] != "") & (itens["Quantidade"] > 0)]
        itens["Quantidade"] = itens["Quantidade"].astype(int)
    else:
        itens = itens[itens["Produto"] != ""]
        
    return itens.to_dict(orient="records")


def localizar_solicitacao(protocolo: str) -> dict[str, Any] | None:
    """Localiza uma solicitação pelo protocolo no banco de dados."""
    return db.carregar_por_protocolo(protocolo)


def atualizar_status(
    solicitacao: dict[str, Any],
    novo_status: str,
    responsavel: str = "",
    observacao: str = "",
) -> None:
    """Atualiza o status e registra uma movimentação consultável pelo solicitante."""
    agora = datetime.now()
    status_anterior = solicitacao.get("status", "")
    solicitacao["status"] = novo_status
    solicitacao["atualizado_em"] = agora
    historico = solicitacao.setdefault("historico_status", [])
    if not historico or status_anterior != novo_status:
        historico.append(
            {
                "status": novo_status,
                "ocorrido_em": agora.isoformat(),
                "responsavel": responsavel or "Sistema",
                "observacao": observacao.strip(),
            }
        )
    db.salvar_solicitacao(solicitacao)


def renderizar_chip_status(status: str) -> None:
    """Renderiza um selo visual para o status de uma requisição."""
    cor, _ = STATUS_META.get(status, ("#475569", ""))
    st.markdown(
        f'<span class="status-chip" style="background:{cor}">{escape(status)}</span>',
        unsafe_allow_html=True,
    )


def renderizar_cabecalho() -> None:
    st.markdown(
        """
        <section class="grm-hero">
          <h1>📦 Gestão de Requisições de Materiais</h1>
          <p>Registre, direcione e acompanhe solicitações entre o atendimento, o almoxarifado e as compras.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # Recarregar solicitações do banco para ter dados atualizados
    solicitacoes = db.carregar_todas()
    st.session_state.solicitacoes = solicitacoes

    total = len(solicitacoes)
    almoxarifado = sum(item["status"] == "Em análise no almoxarifado" for item in solicitacoes)
    compras = sum(item["status"] in STATUS_COMPRAS for item in solicitacoes)
    finalizados = sum(item["status"] in STATUS_CONCLUIDOS for item in solicitacoes)

    colunas = st.columns(4)
    dados = [
        ("Solicitações", total, "total no sistema"),
        ("No almoxarifado", almoxarifado, "em verificação de estoque"),
        ("Em compras", compras, "em processo de aquisição"),
        ("Concluídos", finalizados, "materiais enviados"),
    ]
    for coluna, (rotulo, valor, legenda) in zip(colunas, dados):
        coluna.markdown(
            f'<div class="metric-card"><div class="label">{rotulo}</div>'
            f'<div class="value">{valor}</div><div class="caption">{legenda}</div></div>',
            unsafe_allow_html=True,
        )


def pagina_nova_solicitacao_simplificada() -> None:
    """Formulário extremamente simples e acessível para o solicitante."""
    st.write("Preencha as informações abaixo para solicitar os materiais.")

    # Inicializar lista de materiais no session_state fora do form
    if "lista_materiais" not in st.session_state:
        st.session_state.lista_materiais = [{"produto": "", "quantidade": 1}]

    # Campos fixos fora do formulário para manter o estado ao adicionar materiais
    empresa = st.selectbox("**Qual é a empresa?**", EMPRESAS, key="form_empresa")
    solicitante = st.text_input("**Qual é o seu nome?**", placeholder="Digite seu nome", key="form_solicitante")
    setor_solicitante = st.text_input("**Qual é o seu setor? (opcional)**", placeholder="Ex: Manutenção, Operador, etc", key="form_setor")

    st.write("---")
    st.write("**Quais materiais você precisa?**")
    st.caption("Escreva o nome do material e a quantidade. Para adicionar mais materiais, clique no botão abaixo.")

    # Renderizar campos de materiais fora do formulário para não zerar ao clicar em botões
    for i, item in enumerate(st.session_state.lista_materiais):
        col1, col2 = st.columns([3, 1])
        with col1:
            item["produto"] = st.text_input(f"**Material {i+1}**", value=item["produto"], key=f"mat_prod_{i}", placeholder="Nome do material")
        with col2:
            item["quantidade"] = st.number_input(f"**Qtd {i+1}**", value=item["quantidade"], min_value=1, step=1, key=f"mat_qtd_{i}")

    if st.button("➕ Adicionar outro material"):
        st.session_state.lista_materiais.append({"produto": "", "quantidade": 1})
        st.rerun()

    st.write("---")
    observacao = st.text_area("**Tem mais alguma informação importante? (opcional)**", placeholder="Ex: Urgente, cor específica, etc.", key="form_obs")

    # Botão de envio
    if st.button("✅ ENVIAR SOLICITAÇÃO", type="primary", use_container_width=True):
        gravar = True
    else:
        gravar = False

    if gravar:
        # Filtrar materiais preenchidos
        itens = []
        for item in st.session_state.lista_materiais:
            if item["produto"].strip() and item["quantidade"] > 0:
                itens.append({"Produto": item["produto"].strip(), "Quantidade": item["quantidade"]})

        erros = []
        if empresa == EMPRESAS[0]:
            erros.append("Por favor, selecione a empresa.")
        if not solicitante.strip():
            erros.append("Por favor, escreva o seu nome.")
        if not itens:
            erros.append("Por favor, adicione pelo menos um material na lista.")

        if erros:
            for erro in erros:
                st.error(erro)
            return

        protocolo = gerar_protocolo()
        agora = agora_br()
        solicitacao = {
            "protocolo": protocolo,
            "empresa": empresa,
            "solicitante": solicitante.strip(),
            "setor": setor_solicitante.strip(),
            "prioridade": "Normal",
            "itens": itens,
            "observacao": observacao.strip(),
            "status": "Em análise no almoxarifado",
            "criado_em": agora,
            "atualizado_em": agora,
            "destino": "Almoxarifado",
            "triado_por": "",
            "estoque": [],
            "dados_compra": {},
            "dados_logistica": {},
            "historico_status": [
                {
                    "status": "Em análise no almoxarifado",
                    "ocorrido_em": agora.isoformat(),
                    "responsavel": solicitante.strip(),
                    "observacao": "Solicitação registrada pelo solicitante.",
                }
            ],
        }
        db.salvar_solicitacao(solicitacao)
        st.session_state.solicitacoes = db.carregar_todas()
        st.session_state.ultimo_protocolo = protocolo

        # Limpar a lista de materiais após o envio
        st.session_state.lista_materiais = [{"produto": "", "quantidade": 1}]

        # Notificar por e-mail sobre nova solicitação
        itens_html = "<ul>" + "".join([f"<li>{escape(item['Produto'])} - Qtd: {item['Quantidade']}</li>" for item in itens]) + "</ul>"
        corpo_nova = f"""
        <h3 style="color:#2563EB;">&#128230; Nova Solicitação de Materiais</h3>
        <p><strong>Protocolo:</strong> {escape(protocolo)}</p>
        <p><strong>Empresa:</strong> {escape(empresa)}</p>
        <p><strong>Solicitante:</strong> {escape(solicitante.strip())}</p>
        <p><strong>Setor:</strong> {escape(setor_solicitante.strip() or 'Não informado')}</p>
        <p><strong>Data/Hora:</strong> {agora.strftime('%d/%m/%Y às %H:%M')}</p>
        <p><strong>Status Inicial:</strong> <span style="color:#EA580C;font-weight:bold;">Aguardando Almoxarifado</span></p>
        <h4>Itens solicitados:</h4>
        {itens_html}
        <p><strong>Observação:</strong> {escape(observacao.strip() or 'Nenhuma')}</p>
        <hr/><p style="color:#64748B;font-size:.85em;">Mensagem automática do sistema GRM.</p>
        """
        enviar_email_notificacao(f"Nova solicitação: {protocolo}", corpo_nova)

        st.balloons()
        st.success(f"Sua solicitação foi enviada com sucesso! Anote este código para acompanhar depois: **{protocolo}**")


def _formatar_data_hora(valor: Any) -> str:
    """Apresenta datas do histórico em formato uniforme e legível."""
    if not valor:
        return "Não informado"
    if isinstance(valor, datetime):
        data_hora = valor
    else:
        try:
            data_hora = datetime.fromisoformat(str(valor))
        except ValueError:
            return str(valor)
    return data_hora.strftime("%d/%m/%Y às %H:%M")


def _categoria_status(status: str) -> str:
    if status in {"Aguardando triagem", "Em análise no almoxarifado"}:
        return "Estoque"
    if status in STATUS_COMPRAS:
        return "Compras"
    if status in STATUS_RECEBIMENTO:
        return "Recebimento"
    if status in STATUS_ENVIO:
        return "Envio"
    return "Concluído"


def renderizar_resumo_andamento(solicitacoes: list[dict[str, Any]]) -> None:
    """Mostra legenda e volume de solicitações em andamento ao solicitante."""
    em_andamento = [item for item in solicitacoes if item.get("status") not in STATUS_CONCLUIDOS]
    categorias = [
        ("Em andamento", len(em_andamento), "solicitações ainda não concluídas", "#0F3D62"),
        ("Estoque", sum(_categoria_status(item.get("status", "")) == "Estoque" for item in em_andamento), "em verificação no almoxarifado", "#2563EB"),
        ("Compras", sum(_categoria_status(item.get("status", "")) == "Compras" for item in em_andamento), "em compra ou autorização", "#7C3AED"),
        ("Recebimento", sum(_categoria_status(item.get("status", "")) == "Recebimento" for item in em_andamento), "aguardando chegada ao almoxarifado", "#EA580C"),
        ("Envio", sum(_categoria_status(item.get("status", "")) == "Envio" for item in em_andamento), "prontas para o solicitante", "#0891B2"),
    ]
    colunas = st.columns(len(categorias))
    for coluna, (rotulo, quantidade, detalhe, cor) in zip(colunas, categorias):
        coluna.markdown(
            f'<div class="legend-card" style="border-top:4px solid {cor}">'
            f'<div class="legend-value">{quantidade}</div>'
            f'<div class="legend-label">{rotulo}</div>'
            f'<div class="legend-detail">{detalhe}</div></div>',
            unsafe_allow_html=True,
        )

    st.caption("Legenda do fluxo: azul = estoque, roxo = compras, laranja = recebimento, azul-petróleo = envio e verde = concluído.")


def renderizar_fluxo_solicitacao(solicitacao: dict[str, Any]) -> None:
    """Exibe uma linha do tempo visual de acordo com o status atual."""
    status = solicitacao.get("status", "")
    etapas = [
        ("Solicitação", "Pedido registrado", True, status == "Aguardando triagem"),
        ("Estoque", "Verificação pelo almoxarifado", status not in {"Aguardando triagem"}, status == "Em análise no almoxarifado"),
        ("Compras", "Aquisição e autorização", status in STATUS_RECEBIMENTO | STATUS_ENVIO | STATUS_CONCLUIDOS, status in STATUS_COMPRAS),
        ("Recebimento", "Chegada ao almoxarifado", status in STATUS_ENVIO | STATUS_CONCLUIDOS, status in STATUS_RECEBIMENTO),
        ("Envio", "Despacho ao solicitante", status in STATUS_CONCLUIDOS, status in STATUS_ENVIO),
    ]
    colunas = st.columns(len(etapas))
    for indice, (titulo, descricao, concluida, ativa) in enumerate(etapas, start=1):
        classe = "done" if concluida else "active" if ativa else ""
        colunas[indice - 1].markdown(
            f'<div class="flow-step {classe}"><span class="number">{indice}</span>'
            f'<strong>{escape(titulo)}</strong><span>{escape(descricao)}</span></div>',
            unsafe_allow_html=True,
        )


def renderizar_dados_logistica(solicitacao: dict[str, Any]) -> None:
    """Apresenta os registros de recebimento e de envio do almoxarifado."""
    dados = solicitacao.get("dados_logistica") or {}
    recebimento = dados.get("recebimento") or {}
    envio = dados.get("envio") or {}
    if recebimento:
        st.markdown("#### Recebimento no almoxarifado")
        st.write(f"**Recebido por:** {recebimento.get('recebido_por', 'Não informado')}")
        st.write(f"**Data e hora:** {_formatar_data_hora(recebimento.get('data_hora'))}")
        st.write(f"**Documento de referência:** {recebimento.get('documento', 'Não informado')}")
        if recebimento.get("observacao"):
            st.write(f"**Observação:** {recebimento['observacao']}")
    if envio:
        st.markdown("#### Envio ao solicitante")
        st.success(
            f"Produto enviado por **{envio.get('enviado_por', 'Não informado')}** "
            f"para **{envio.get('destinatario', solicitacao.get('solicitante', 'Não informado'))}** "
            f"em {_formatar_data_hora(envio.get('data_hora'))}."
        )
        st.write(f"**Modalidade de entrega:** {envio.get('modalidade', 'Não informada')}")
        if envio.get("observacao"):
            st.write(f"**Observação do almoxarifado:** {envio['observacao']}")


def renderizar_historico_status(solicitacao: dict[str, Any]) -> None:
    historico = solicitacao.get("historico_status") or []
    if not historico:
        return
    st.markdown("#### Histórico de movimentações")
    linhas = [
        {
            "Data e hora": _formatar_data_hora(item.get("ocorrido_em")),
            "Status": item.get("status", "Não informado"),
            "Responsável": item.get("responsavel", "Não informado"),
            "Observação": item.get("observacao", ""),
        }
        for item in reversed(historico)
    ]
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")


def renderizar_card_solicitacao(solicitacao: dict) -> None:
    """Renderiza um card compacto para a grade de acompanhamento."""
    cor, _ = STATUS_META.get(solicitacao["status"], ("#475569", ""))
    empresa_curta = solicitacao["empresa"].split(" - ")[0] if " - " in solicitacao["empresa"] else solicitacao["empresa"][:25]
    itens_resumo = ", ".join(f"{item['Produto']} (x{item['Quantidade']})" for item in solicitacao["itens"][:3])
    if len(solicitacao["itens"]) > 3:
        itens_resumo += f" (+{len(solicitacao['itens']) - 3} mais)"
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-left:5px solid {cor};border-radius:10px;padding:.8rem 1rem;margin-bottom:.6rem;box-shadow:0 2px 8px rgba(15,23,42,.04);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;"><div>'
        f'<span style="font-size:.75rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">{escape(solicitacao["protocolo"])}</span>'
        f'<div style="font-size:.95rem;color:#0F172A;font-weight:700;margin:.15rem 0;">{escape(empresa_curta)}</div>'
        f'<span style="font-size:.78rem;color:#64748B;">{escape(itens_resumo)}</span></div>'
        f'<span class="status-chip" style="background:{cor};">{escape(solicitacao["status"])}</span></div></div>',
        unsafe_allow_html=True,
    )


def renderizar_grade_acompanhamento(solicitacoes: list[dict]) -> None:
    """Renderiza cards de acompanhamento com o fluxo e os dados operacionais."""
    if not solicitacoes:
        st.info("Nenhuma solicitação encontrada.")
        return
    st.caption(f"**{len(solicitacoes)}** solicitação(ões) encontrada(s)")
    for solicitacao in solicitacoes:
        renderizar_card_solicitacao(solicitacao)
        with st.expander("Ver detalhes completos", expanded=False):
            renderizar_fluxo_solicitacao(solicitacao)
            detalhes, itens_coluna = st.columns([1, 1.2])
            with detalhes:
                st.markdown("#### Dados da solicitação")
                st.write(f"**Empresa:** {solicitacao['empresa']}")
                st.write(f"**Solicitante:** {solicitacao['solicitante']}")
                st.write(f"**Prioridade:** {solicitacao['prioridade']}")
                if solicitacao.get("destino"):
                    st.write(f"**Encaminhamento:** {solicitacao['destino']}")
                st.write(f"**Última atualização:** {_formatar_data_hora(solicitacao.get('atualizado_em'))}")
            with itens_coluna:
                st.markdown("#### Itens solicitados")
                st.dataframe(pd.DataFrame(solicitacao["itens"]), hide_index=True, width="stretch")
            if solicitacao.get("estoque"):
                st.markdown("#### Conferência do almoxarifado")
                st.dataframe(pd.DataFrame(solicitacao["estoque"]), hide_index=True, width="stretch")
                if solicitacao.get("observacao_almoxarifado"):
                    st.info(f"**Obs. Almoxarifado:** {solicitacao['observacao_almoxarifado']}")
            if solicitacao.get("dados_compra"):
                dados = solicitacao["dados_compra"]
                st.markdown("#### Dados registrados para compras")
                st.write(f"**Status da compra:** {dados.get('status_compra', 'Não informado')}")
                st.write(f"**Fornecedor:** {dados.get('fornecedor', 'Não informado')}")
                st.write(f"**Previsão de entrega:** {dados.get('previsao', 'Não informada')}")
                st.write(f"**Responsável:** {dados.get('responsavel', 'Não informado')}")
                if dados.get("observacao"):
                    st.write(f"**Observação:** {dados['observacao']}")
            renderizar_dados_logistica(solicitacao)
            renderizar_historico_status(solicitacao)
        st.markdown("")


def pagina_acompanhar_status() -> None:
    """Permite que o solicitante acompanhe volumes, legenda e detalhes do fluxo."""
    st.subheader("Acompanhar status")
    st.write("Consulte a evolução das suas solicitações e a distribuição dos atendimentos em andamento.")
    solicitacoes = db.carregar_todas()
    renderizar_resumo_andamento(solicitacoes)
    st.markdown("---")
    opcao_busca = st.radio(
        "Método de busca",
        ["Todas as solicitações", "Por protocolo", "Por empresa"],
        horizontal=True,
    )
    if opcao_busca == "Todas as solicitações":
        renderizar_grade_acompanhamento(solicitacoes)
    elif opcao_busca == "Por protocolo":
        protocolo = st.text_input(
            "Protocolo da solicitação",
            value=st.session_state.ultimo_protocolo,
            placeholder="Ex.: GRM-20260720-0001",
        )
        if st.button("Consultar status", type="primary"):
            solicitacao = localizar_solicitacao(protocolo.strip().upper())
            if not solicitacao:
                st.warning("Nenhuma solicitação foi encontrada com esse protocolo.")
                return
            renderizar_grade_acompanhamento([solicitacao])
    else:
        empresa_selecionada = st.selectbox("Selecione a empresa", EMPRESAS[1:])
        if st.button("Filtrar solicitações", type="primary"):
            filtradas = [item for item in solicitacoes if item["empresa"] == empresa_selecionada]
            if not filtradas:
                st.warning(f"Nenhuma solicitação encontrada para {empresa_selecionada}.")
                return
            renderizar_grade_acompanhamento(filtradas)



def exibir_detalhes_solicitacao(solicitacao: dict) -> None:
    cor, descricao = STATUS_META.get(solicitacao["status"], ("#475569", "Status atualizado."))
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border-left:7px solid {cor};border-radius:10px;padding:1.1rem 1.2rem;margin:1rem 0;border-top:1px solid #E2E8F0;border-right:1px solid #E2E8F0;border-bottom:1px solid #E2E8F0;">
            <div style="font-size:.8rem;color:#64748B;font-weight:700;text-transform:uppercase;">{escape(solicitacao['protocolo'])}</div>
            <div style="font-size:1.35rem;color:#0F172A;font-weight:800;margin:.18rem 0;">{escape(solicitacao['status'])}</div>
            <div style="color:#475569;">{escape(descricao)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    detalhes, itens_coluna = st.columns([1, 1.2])
    with detalhes:
        st.markdown("#### Dados da solicitação")
        st.write(f"**Empresa:** {solicitacao['empresa']}")
        st.write(f"**Solicitante:** {solicitacao['solicitante']}")
        st.write(f"**Prioridade:** {solicitacao['prioridade']}")
        if solicitacao["destino"]:
            st.write(f"**Encaminhamento:** {solicitacao['destino']}")
        st.write(f"**Última atualização:** {solicitacao['atualizado_em'].strftime('%d/%m/%Y às %H:%M')}")
    with itens_coluna:
        st.markdown("#### Itens solicitados")
        st.dataframe(pd.DataFrame(solicitacao["itens"]), hide_index=True, width="stretch")

    if solicitacao.get("estoque"):
        st.markdown("#### Retorno do almoxarifado")
        st.dataframe(pd.DataFrame(solicitacao["estoque"]), hide_index=True, width="stretch")
    if solicitacao.get("dados_compra"):
        dados = solicitacao["dados_compra"]
        st.markdown("#### Dados registrados para compras")
        st.write(f"**Fornecedor sugerido:** {dados.get('fornecedor', 'Não informado')}")
        st.write(f"**Previsão de entrega:** {dados.get('previsao', 'Não informada')}")
        if dados.get("observacao"):
            st.write(f"**Observação:** {dados['observacao']}")


def obter_senha_configurada(usuario: str) -> str | None:
    """Obtém a senha de um usuário a partir do banco de dados."""
    return db.obter_senha_usuario(usuario)


def usuario_tem_permissao(usuario: str, permissao: str) -> bool:
    """Informa se o usuário possui a permissão necessária para uma área."""
    permissoes = db.obter_permissoes_usuario(usuario)
    return permissao in permissoes


def tela_login_atendente() -> bool:
    """
    Exibe a tela de login unificada para o Atendente.
    O usuário escolhe seu perfil (Compras ou Almoxarifado) e digita a senha.
    Retorna True se autenticado com sucesso.
    """
    if st.session_state.usuario_autenticado in ("compras", "almoxarifado"):
        return True

    st.markdown(
        """
        <section class="grm-hero">
          <h1>🔐 Acesso do Atendente</h1>
          <p>Selecione seu perfil e informe a senha para acessar o painel.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.form("formulario_login_atendente"):
        perfil_login = st.selectbox(
            "Qual é o seu perfil?",
            ["Selecione...", "Almoxarifado", "Compras"],
        )
        senha_informada = st.text_input("Senha", type="password", placeholder="Digite a senha de acesso")
        acessar = st.form_submit_button("Entrar", type="primary", width="stretch")

    if acessar:
        if perfil_login == "Selecione...":
            st.error("Por favor, selecione o seu perfil antes de continuar.")
            return False

        usuario_chave = perfil_login.lower()
        senha_esperada = obter_senha_configurada(usuario_chave)

        if not senha_esperada:
            st.error("Acesso indisponível. Solicite ao administrador a configuração desta conta.")
            return False

        if not hmac.compare_digest(senha_informada, senha_esperada):
            st.error("Senha inválida. Verifique os dados e tente novamente.")
            return False

        st.session_state.usuario_autenticado = usuario_chave
        st.rerun()

    st.markdown("---")
    if st.button("← Voltar para a tela inicial"):
        st.session_state.perfil = ""
        st.rerun()

    return False


def pagina_atendimento() -> None:
    """Apresenta a triagem que direciona solicitações ao setor responsável."""
    st.subheader("Atendimento e triagem")
    st.write("Analise a solicitação e encaminhe para o almoxarifado ou para compras.")

    # Recarregar solicitações do banco
    st.session_state.solicitacoes = db.carregar_todas()
    pendentes = [item for item in st.session_state.solicitacoes if item["status"] == "Aguardando triagem"]
    if not pendentes:
        st.info("Não há solicitações aguardando triagem no momento.")
        return

    opcoes = {
        f"{item['protocolo']} — {item['empresa']} — {item['solicitante']}": item["protocolo"]
        for item in pendentes
    }
    selecao = st.selectbox("Solicitação aguardando atendimento", list(opcoes))
    solicitacao = localizar_solicitacao(opcoes[selecao])
    assert solicitacao is not None

    esquerda, direita = st.columns([1.1, 1])
    with esquerda:
        st.markdown("#### Itens para análise")
        st.dataframe(pd.DataFrame(solicitacao["itens"]), hide_index=True, width="stretch")
        if solicitacao["observacao"]:
            st.caption(f"Observação do solicitante: {solicitacao['observacao']}")
    with direita:
        st.markdown("#### Definir encaminhamento")
        destino = st.radio(
            "Setor responsável",
            ["Almoxarifado", "Compras"],
            horizontal=True,
            help="Selecione almoxarifado quando a disponibilidade de estoque deve ser verificada; selecione compras quando a aquisição deve seguir diretamente para cotação ou compra.",
        )
        justificativa = st.text_area("Justificativa do encaminhamento", placeholder="Registre uma observação para o setor responsável.")
        encaminhar = st.button(f"Encaminhar para {destino}", type="primary", width="stretch")

    if encaminhar:
        novo_status = "Em análise no almoxarifado" if destino == "Almoxarifado" else "Em processo de compra"
        solicitacao["destino"] = destino
        solicitacao["triado_por"] = st.session_state.usuario_autenticado
        solicitacao["observacao_triagem"] = justificativa.strip()
        atualizar_status(
            solicitacao,
            novo_status,
            st.session_state.usuario_autenticado,
            justificativa.strip(),
        )
        st.success(f"{solicitacao['protocolo']} encaminhada para {destino.lower()}.")

        itens_html = "<ul>" + "".join([f"<li>{escape(str(_obter_valor_item(item, 'produto')))} - Qtd: {_obter_valor_item(item, 'quantidade', 1)}</li>" for item in solicitacao['itens']]) + "</ul>"
        corpo_email = f"""
        <h3 style="color:#EA580C;">&#128260; Solicitação Encaminhada para {escape(destino)}</h3>
        <p><strong>Protocolo:</strong> {escape(solicitacao['protocolo'])}</p>
        <p><strong>Empresa:</strong> {escape(solicitacao['empresa'])}</p>
        <p><strong>Solicitante:</strong> {escape(solicitacao['solicitante'])}</p>
        <p><strong>Setor Destino:</strong> {escape(destino)}</p>
        <p><strong>Triado por:</strong> {escape(st.session_state.usuario_autenticado)}</p>
        <p><strong>Justificativa:</strong> {escape(justificativa.strip() or 'Não informada')}</p>
        <h4>Itens:</h4>
        {itens_html}
        <hr/><p style="color:#64748B;font-size:.85em;">Mensagem automática do sistema GRM.</p>
        """
        enviar_email_notificacao(f"Encaminhamento: {solicitacao['protocolo']}", corpo_email)
        st.rerun()


def _obter_valor_item(item: dict[str, Any], chave: str, padrao: Any = "") -> Any:
    """Extrai valor do item tratando chaves em maiúsculo ou minúsculo (ex: Produto/produto)."""
    for k in (chave.capitalize(), chave.lower()):
        if k in item:
            return item[k]
    return padrao


def _renderizar_cartao_operacional(solicitacao: dict[str, Any]) -> None:
    cor, _ = STATUS_META.get(solicitacao["status"], ("#475569", ""))
    itens_resumo = ", ".join(
        f"{escape(str(_obter_valor_item(item, 'produto')))} (x{_obter_valor_item(item, 'quantidade', 1)})"
        for item in solicitacao["itens"][:3]
    )
    if len(solicitacao["itens"]) > 3:
        itens_resumo += f" (+{len(solicitacao['itens']) - 3} mais)"
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-left:5px solid {cor};border-radius:10px;padding:.8rem 1rem;margin-bottom:.5rem;box-shadow:0 2px 8px rgba(15,23,42,.04);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;"><div>'
        f'<span style="font-size:.75rem;color:#64748B;font-weight:700;text-transform:uppercase;">{escape(solicitacao["protocolo"])}</span>'
        f'<div style="font-size:.95rem;color:#0F172A;font-weight:700;margin:.15rem 0;">{escape(solicitacao["empresa"])}</div>'
        f'<span style="font-size:.78rem;color:#64748B;">Solicitante: {escape(solicitacao["solicitante"])} · {escape(itens_resumo)}</span></div>'
        f'<span class="status-chip" style="background:{cor};">{escape(solicitacao["status"])}</span></div></div>',
        unsafe_allow_html=True,
    )


def _combinar_data_hora(data_evento: date, hora_evento) -> str:
    return datetime.combine(data_evento, hora_evento).isoformat()


def pagina_almoxarifado() -> None:
    """Orquestra conferência, recebimento físico e envio ao solicitante."""
    st.subheader("Painel do almoxarifado")
    st.write("Conferir estoque, registrar a chegada das compras e formalizar o envio ao solicitante.")
    solicitacoes = db.carregar_todas()
    st.session_state.solicitacoes = solicitacoes
    em_analise = [item for item in solicitacoes if item["status"] in {"Em análise no almoxarifado", "Aguardando triagem"}]
    aguardando_recebimento = [item for item in solicitacoes if item["status"] in STATUS_RECEBIMENTO]
    aguardando_envio = [item for item in solicitacoes if item["status"] in STATUS_ENVIO]

    resumo = [
        ("Conferir estoque", len(em_analise), "solicitações em análise", "#2563EB"),
        ("Receber compras", len(aguardando_recebimento), "compras aguardando chegada", "#EA580C"),
        ("Enviar materiais", len(aguardando_envio), "prontos para o solicitante", "#0891B2"),
    ]
    colunas_resumo = st.columns(3)
    for coluna, (rotulo, quantidade, detalhe, cor) in zip(colunas_resumo, resumo):
        coluna.markdown(
            f'<div class="legend-card" style="border-top:4px solid {cor}"><div class="legend-value">{quantidade}</div>'
            f'<div class="legend-label">{rotulo}</div><div class="legend-detail">{detalhe}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 1. Conferir estoque")
    if not em_analise:
        st.info("Não há solicitações aguardando conferência de estoque.")
    else:
        for solicitacao in em_analise:
            _renderizar_cartao_operacional(solicitacao)
            with st.expander("Conferir itens e definir encaminhamento", expanded=False):
                if solicitacao.get("observacao_triagem"):
                    st.info(f"Observação da triagem: {solicitacao['observacao_triagem']}")
                itens_conferidos = []
                cabecalho = st.columns([0.7, 2.2, 1, 1])
                cabecalho[0].markdown("**Disponível**")
                cabecalho[1].markdown("**Produto**")
                cabecalho[2].markdown("**Qtd. solicitada**")
                cabecalho[3].markdown("**Qtd. disponível**")
                for indice, item in enumerate(solicitacao["itens"]):
                    produto = _obter_valor_item(item, "produto")
                    quantidade_solicitada = int(_obter_valor_item(item, "quantidade", 1))
                    linha = st.columns([0.7, 2.2, 1, 1])
                    disponivel = linha[0].checkbox(
                        "Disponível",
                        key=f"estoque_disponivel_{solicitacao['protocolo']}_{indice}",
                        label_visibility="collapsed",
                    )
                    linha[1].markdown(f"**{escape(produto)}**")
                    linha[2].write(quantidade_solicitada)
                    quantidade_disponivel = linha[3].number_input(
                        "Quantidade disponível",
                        min_value=0,
                        max_value=quantidade_solicitada,
                        value=quantidade_solicitada if disponivel else 0,
                        disabled=not disponivel,
                        key=f"estoque_quantidade_{solicitacao['protocolo']}_{indice}",
                        label_visibility="collapsed",
                    )
                    situacao = "Disponível" if disponivel and quantidade_disponivel >= quantidade_solicitada else ("Parcial" if disponivel else "Indisponível")
                    itens_conferidos.append(
                        {
                            "Produto": produto,
                            "Qtd. solicitada": quantidade_solicitada,
                            "Qtd. disponível": quantidade_disponivel,
                            "Situação": situacao,
                        }
                    )
                observacao = st.text_area(
                    "Observação do almoxarifado",
                    key=f"observacao_estoque_{solicitacao['protocolo']}",
                    placeholder="Informe detalhes sobre disponibilidade, separação ou reposição.",
                )
                if st.button("Confirmar conferência", type="primary", width="stretch", key=f"confirmar_estoque_{solicitacao['protocolo']}"):
                    tem_falta = any(item["Qtd. disponível"] < item["Qtd. solicitada"] for item in itens_conferidos)
                    solicitacao["estoque"] = itens_conferidos
                    solicitacao["observacao_almoxarifado"] = observacao.strip()
                    itens_estoque_html = "<table border='1' cellpadding='4' style='border-collapse:collapse;'><tr><th>Produto</th><th>Solicitado</th><th>Disponível</th><th>Situação</th></tr>" + "".join([f"<tr><td>{escape(str(_obter_valor_item(it, 'produto')))}</td><td>{_obter_valor_item(it, 'qtd. solicitada')}</td><td>{_obter_valor_item(it, 'qtd. disponível')}</td><td>{escape(str(_obter_valor_item(it, 'situação')))}</td></tr>" for it in itens_conferidos]) + "</table>"
                    if tem_falta:
                        solicitacao["destino"] = "Compras"
                        atualizar_status(
                            solicitacao,
                            "Em processo de compra",
                            st.session_state.usuario_autenticado,
                            observacao or "Item indisponível ou parcial; encaminhado para compras.",
                        )
                        st.success(f"{solicitacao['protocolo']} foi encaminhada para Compras.")
                        corpo_estoque = f"""
                        <h3 style="color:#EA580C;">&#128230; Conferência de Estoque — Encaminhado para Compras</h3>
                        <p><strong>Protocolo:</strong> {escape(solicitacao['protocolo'])}</p>
                        <p><strong>Empresa:</strong> {escape(solicitacao['empresa'])}</p>
                        <p><strong>Solicitante:</strong> {escape(solicitacao['solicitante'])}</p>
                        <p><strong>Conferido por:</strong> {escape(st.session_state.usuario_autenticado)}</p>
                        <p><strong>Observação:</strong> {escape(observacao or 'Não informada')}</p>
                        <h4>Resultado da conferência:</h4>
                        {itens_estoque_html}
                        <hr/><p style="color:#64748B;font-size:.85em;">Mensagem automática do sistema GRM.</p>
                        """
                        enviar_email_notificacao(f"Estoque: {solicitacao['protocolo']} → Compras", corpo_estoque)
                    else:
                        solicitacao["destino"] = "Almoxarifado"
                        atualizar_status(
                            solicitacao,
                            "Aguardando envio ao solicitante",
                            st.session_state.usuario_autenticado,
                            observacao or "Todos os itens estão disponíveis para envio.",
                        )
                        st.success(f"{solicitacao['protocolo']} está pronta para envio ao solicitante.")
                        corpo_estoque = f"""
                        <h3 style="color:#16A34A;">&#9989; Conferência de Estoque — Itens Disponíveis</h3>
                        <p><strong>Protocolo:</strong> {escape(solicitacao['protocolo'])}</p>
                        <p><strong>Empresa:</strong> {escape(solicitacao['empresa'])}</p>
                        <p><strong>Solicitante:</strong> {escape(solicitacao['solicitante'])}</p>
                        <p><strong>Conferido por:</strong> {escape(st.session_state.usuario_autenticado)}</p>
                        <p><strong>Observação:</strong> {escape(observacao or 'Não informada')}</p>
                        <h4>Resultado da conferência:</h4>
                        {itens_estoque_html}
                        <hr/><p style="color:#64748B;font-size:.85em;">Mensagem automática do sistema GRM.</p>
                        """
                        enviar_email_notificacao(f"Estoque: {solicitacao['protocolo']} → Pronto para envio", corpo_estoque)
                    st.rerun()

    st.markdown("---")
    st.markdown("### 2. Receber compras")
    if not aguardando_recebimento:
        st.info("Não há compras aguardando recebimento físico no almoxarifado.")
    else:
        for solicitacao in aguardando_recebimento:
            _renderizar_cartao_operacional(solicitacao)
            with st.expander("Registrar recebimento", expanded=False):
                dados_compra = solicitacao.get("dados_compra") or {}
                st.write(f"**Fornecedor:** {dados_compra.get('fornecedor', 'Não informado')}")
                st.write(f"**Previsão registrada:** {dados_compra.get('previsao', 'Não informada')}")
                with st.form(f"recebimento_{solicitacao['protocolo']}"):
                    recebido_por = st.text_input("Recebido por", value="almoxarifado")
                    col_data, col_hora = st.columns(2)
                    data_recebimento = col_data.date_input("Data de recebimento", value=date.today())
                    hora_recebimento = col_hora.time_input("Hora de recebimento", value=agora_br().time().replace(second=0, microsecond=0))
                    documento = st.text_input("Documento de referência", placeholder="Ex.: NF, romaneio ou pedido")
                    observacao = st.text_area("Observação do recebimento", placeholder="Registre a conferência física ou alguma divergência.")
                    registrar = st.form_submit_button("Confirmar recebimento", type="primary", width="stretch")
                if registrar:
                    if not recebido_por.strip():
                        st.error("Informe quem recebeu o material.")
                    else:
                        logistica = solicitacao.setdefault("dados_logistica", {})
                        logistica["recebimento"] = {
                            "recebido_por": recebido_por.strip(),
                            "data_hora": _combinar_data_hora(data_recebimento, hora_recebimento),
                            "documento": documento.strip() or "Não informado",
                            "observacao": observacao.strip(),
                        }
                        solicitacao["destino"] = "Almoxarifado"
                        atualizar_status(
                            solicitacao,
                            "Aguardando envio ao solicitante",
                            recebido_por.strip(),
                            observacao or "Compra recebida fisicamente no almoxarifado.",
                        )
                        st.success(f"Recebimento de {solicitacao['protocolo']} registrado. Material disponível para envio.")
                        corpo_recebimento = f"""
                        <h3 style="color:#0891B2;">&#128230; Material Recebido no Almoxarifado</h3>
                        <p><strong>Protocolo:</strong> {escape(solicitacao['protocolo'])}</p>
                        <p><strong>Empresa:</strong> {escape(solicitacao['empresa'])}</p>
                        <p><strong>Solicitante:</strong> {escape(solicitacao['solicitante'])}</p>
                        <p><strong>Recebido por:</strong> {escape(recebido_por.strip())}</p>
                        <p><strong>Data/Hora:</strong> {escape(_combinar_data_hora(data_recebimento, hora_recebimento))}</p>
                        <p><strong>Documento:</strong> {escape(documento.strip() or 'Não informado')}</p>
                        <p><strong>Observação:</strong> {escape(observacao or 'Não informada')}</p>
                        <hr/><p style="color:#64748B;font-size:.85em;">Mensagem automática do sistema GRM.</p>
                        """
                        enviar_email_notificacao(f"Recebimento: {solicitacao['protocolo']}", corpo_recebimento)
                        st.rerun()

    st.markdown("---")
    st.markdown("### 3. Enviar materiais ao solicitante")
    if not aguardando_envio:
        st.info("Não há materiais aguardando envio ao solicitante.")
    else:
        for solicitacao in aguardando_envio:
            _renderizar_cartao_operacional(solicitacao)
            with st.expander("Registrar envio ao solicitante", expanded=False):
                with st.form(f"envio_{solicitacao['protocolo']}"):
                    enviado_por = st.text_input("Produto enviado por", value="almoxarifado")
                    destinatario = st.text_input("Destinatário", value=solicitacao["solicitante"])
                    col_data, col_hora = st.columns(2)
                    data_envio = col_data.date_input("Data de envio", value=date.today())
                    hora_envio = col_hora.time_input("Hora de envio", value=agora_br().time().replace(second=0, microsecond=0))
                    modalidade = st.selectbox("Modalidade de entrega", ["Entrega interna", "Retirada pelo solicitante", "Transportadora", "Outro"])
                    observacao = st.text_area("Observação do envio", placeholder="Registre local de entrega, comprovante ou outra informação útil.")
                    registrar = st.form_submit_button("Confirmar envio ao solicitante", type="primary", width="stretch")
                if registrar:
                    if not enviado_por.strip() or not destinatario.strip():
                        st.error("Informe quem enviou e quem recebeu o material.")
                    else:
                        logistica = solicitacao.setdefault("dados_logistica", {})
                        logistica["envio"] = {
                            "enviado_por": enviado_por.strip(),
                            "destinatario": destinatario.strip(),
                            "data_hora": _combinar_data_hora(data_envio, hora_envio),
                            "modalidade": modalidade,
                            "observacao": observacao.strip(),
                        }
                        solicitacao["destino"] = destinatario.strip()
                        atualizar_status(
                            solicitacao,
                            "Produto enviado ao solicitante",
                            enviado_por.strip(),
                            observacao or f"Material enviado para {destinatario.strip()}.",
                        )
                        st.success(f"Envio de {solicitacao['protocolo']} registrado com sucesso.")
                        itens_html_envio = "<ul>" + "".join([f"<li>{escape(str(_obter_valor_item(item, 'produto')))} - Qtd: {_obter_valor_item(item, 'quantidade', 1)}</li>" for item in solicitacao['itens']]) + "</ul>"
                        corpo_envio = f"""
                        <h3 style="color:#16A34A;">&#9989; Material Enviado ao Solicitante</h3>
                        <p><strong>Protocolo:</strong> {escape(solicitacao['protocolo'])}</p>
                        <p><strong>Empresa:</strong> {escape(solicitacao['empresa'])}</p>
                        <p><strong>Solicitante / Destinatário:</strong> {escape(destinatario.strip())}</p>
                        <p><strong>Enviado por:</strong> {escape(enviado_por.strip())}</p>
                        <p><strong>Data/Hora:</strong> {escape(_combinar_data_hora(data_envio, hora_envio))}</p>
                        <p><strong>Modalidade:</strong> {escape(modalidade)}</p>
                        <p><strong>Observação:</strong> {escape(observacao or 'Não informada')}</p>
                        <h4>Itens entregues:</h4>
                        {itens_html_envio}
                        <hr/><p style="color:#64748B;font-size:.85em;">Mensagem automática do sistema GRM.</p>
                        """
                        enviar_email_notificacao(f"Envio concluído: {solicitacao['protocolo']}", corpo_envio)
                        st.rerun()



def pagina_compras() -> None:
    """Registra o andamento da compra e devolve materiais comprados ao almoxarifado."""
    st.subheader("Painel de compras")
    st.write("Registre a autorização ou a conclusão da compra para encaminhar o recebimento ao almoxarifado.")
    solicitacoes = [item for item in db.carregar_todas() if item["status"] in STATUS_COMPRAS]
    if not solicitacoes:
        st.info("Não há solicitações aguardando tratamento pelo setor de compras no momento.")
        return
    opcoes = {
        f"{item['protocolo']} — {item['empresa']} — {item['status']}": item["protocolo"]
        for item in solicitacoes
    }
    selecao = st.selectbox("Solicitação encaminhada a compras", list(opcoes), key="selecionar_compras")
    solicitacao = localizar_solicitacao(opcoes[selecao])
    assert solicitacao is not None
    st.markdown("#### Itens para compra")
    st.dataframe(pd.DataFrame(solicitacao["itens"]), hide_index=True, width="stretch")
    dados_anteriores = solicitacao.get("dados_compra") or {}
    opcoes_status = ["Em processo de autorização", "Comprado"]
    indice_status = 1 if dados_anteriores.get("status_compra") == "Comprado" else 0
    with st.form(f"formulario_compras_{solicitacao['protocolo']}"):
        st.markdown("#### Status da compra")
        status_compra = st.radio("Qual é o status da compra?", opcoes_status, index=indice_status, horizontal=True)
        esquerda, direita = st.columns(2)
        with esquerda:
            fornecedor = st.text_input("Fornecedor", value=dados_anteriores.get("fornecedor", ""), placeholder="Ex.: Fornecedor ABC")
            previsao = st.date_input("Previsão de entrega", value=date.today())
        with direita:
            responsavel = st.text_input("Responsável pela compra", value=dados_anteriores.get("responsavel", "compras"), placeholder="Ex.: Ana Souza")
            centro_custo = st.text_input("Centro de custo", value=dados_anteriores.get("centro_custo", ""), placeholder="Ex.: CC-1001")
        observacao = st.text_area("Observação para compras", value=dados_anteriores.get("observacao", ""), placeholder="Inclua condições, urgência ou referências de cotação.")
        registrar = st.form_submit_button("Registrar andamento da compra", type="primary", width="stretch")
    if registrar:
        solicitacao["dados_compra"] = {
            "status_compra": status_compra,
            "fornecedor": fornecedor.strip() or "Não informado",
            "previsao": previsao.strftime("%d/%m/%Y"),
            "responsavel": responsavel.strip() or "Não informado",
            "centro_custo": centro_custo.strip() or "Não informado",
            "observacao": observacao.strip(),
        }
        if status_compra == "Comprado":
            solicitacao["destino"] = "Almoxarifado"
            proximo_status = "Aguardando recebimento no almoxarifado"
            mensagem = "Compra registrada. O almoxarifado foi acionado para receber o material."
        else:
            solicitacao["destino"] = "Compras"
            proximo_status = "Em processo de autorização"
            mensagem = "A compra permanece em processo de autorização."
        atualizar_status(solicitacao, proximo_status, responsavel.strip() or "compras", observacao)
        st.success(f"{solicitacao['protocolo']}: {mensagem}")
        itens_html_compra = "<ul>" + "".join([f"<li>{escape(str(_obter_valor_item(item, 'produto')))} - Qtd: {_obter_valor_item(item, 'quantidade', 1)}</li>" for item in solicitacao['itens']]) + "</ul>"
        cor_compra = "#16A34A" if status_compra == "Comprado" else "#EA580C"
        icone_compra = "&#9989;" if status_compra == "Comprado" else "&#128203;"
        corpo_compra = f"""
        <h3 style="color:{cor_compra};">{icone_compra} Compra: {escape(status_compra)} — {escape(solicitacao['protocolo'])}</h3>
        <p><strong>Protocolo:</strong> {escape(solicitacao['protocolo'])}</p>
        <p><strong>Empresa:</strong> {escape(solicitacao['empresa'])}</p>
        <p><strong>Solicitante:</strong> {escape(solicitacao['solicitante'])}</p>
        <p><strong>Status da compra:</strong> {escape(status_compra)}</p>
        <p><strong>Fornecedor:</strong> {escape(fornecedor.strip() or 'Não informado')}</p>
        <p><strong>Responsável:</strong> {escape(responsavel.strip() or 'Não informado')}</p>
        <p><strong>Previsão de entrega:</strong> {escape(previsao.strftime('%d/%m/%Y'))}</p>
        <p><strong>Centro de custo:</strong> {escape(centro_custo.strip() or 'Não informado')}</p>
        <p><strong>Observação:</strong> {escape(observacao or 'Não informada')}</p>
        <h4>Itens:</h4>
        {itens_html_compra}
        <hr/><p style="color:#64748B;font-size:.85em;">Mensagem automática do sistema GRM.</p>
        """
        enviar_email_notificacao(f"Compra {status_compra}: {solicitacao['protocolo']}", corpo_compra)
        st.rerun()



def main() -> None:
    configurar_pagina()
    
    try:
        inicializar_estado()
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        st.info("Por favor, atualize a página em alguns instantes.")
        return

    st.session_state.setdefault("perfil", "")

    # ─── TELA INICIAL: apenas SOLICITANTE e ATENDENTE ────────────────────────
    if st.session_state.perfil == "":
        st.markdown(
            """
            <section class="grm-hero">
              <h1>📦 GRM — Gestão de Requisições de Materiais</h1>
              <p>Selecione o seu acesso para continuar.</p>
            </section>
            """,
            unsafe_allow_html=True,
        )

        col_solicitante, col_atendente = st.columns(2)

        with col_solicitante:
            if st.button("👤  SOLICITANTE", type="primary", width="stretch"):
                st.session_state.perfil = "solicitante"
                st.rerun()
            st.caption("Faça uma nova solicitação ou acompanhe o status de uma existente.")

        with col_atendente:
            if st.button("🔐  ATENDENTE", type="secondary", width="stretch"):
                st.session_state.perfil = "atendente"
                st.rerun()
            st.caption("Acesse o painel de triagem, almoxarifado ou compras.")

        st.markdown("---")
        st.caption("Versão da aplicação: " + APP_VERSION)
        return

    # ─── PERFIL: SOLICITANTE ─────────────────────────────────────────────────
    if st.session_state.perfil == "solicitante":
        st.session_state.setdefault("modo_solicitante", "form")

        if st.session_state.modo_solicitante == "form":
            st.subheader("Nova solicitação de materiais")
            pagina_nova_solicitacao_simplificada()
            st.markdown("---")
            if st.button("🔍 Verificar o status das minhas solicitações"):
                st.session_state.modo_solicitante = "status"
                st.rerun()

            if st.button("← Voltar para a tela inicial"):
                st.session_state.perfil = ""
                st.session_state.modo_solicitante = "form"
                st.rerun()

        else:
            st.subheader("Acompanhar status")
            pagina_acompanhar_status()
            st.markdown("---")
            if st.button("← Voltar para Nova solicitação"):
                st.session_state.modo_solicitante = "form"
                st.rerun()
            if st.button("← Voltar para a tela inicial"):
                st.session_state.perfil = ""
                st.session_state.modo_solicitante = "form"
                st.rerun()

    # ─── PERFIL: ATENDENTE (login unificado) ─────────────────────────────────
    elif st.session_state.perfil == "atendente":
        # Exige login antes de qualquer painel
        if not tela_login_atendente():
            return

        # Após autenticação, exibe o painel correspondente ao perfil logado
        usuario = st.session_state.usuario_autenticado
        renderizar_cabecalho()

        if usuario == "compras":
            pagina_compras()
        elif usuario == "almoxarifado":
            pagina_almoxarifado()

        st.markdown("---")
        if st.button("🚪 Sair", width="stretch"):
            st.session_state.perfil = ""
            st.session_state.usuario_autenticado = ""
            st.rerun()


if __name__ == "__main__":
    main()
