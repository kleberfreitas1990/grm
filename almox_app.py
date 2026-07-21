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
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import Any

import db
import pandas as pd
import streamlit as st


APP_VERSION = "1.2.1"

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

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
NOTIFICATION_EMAIL = "pedreira.azulimperial@gramazini.com.br"

def enviar_email_notificacao(assunto: str, corpo: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        st.error("Credenciais SMTP não configuradas. O e-mail não será enviado.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = f"[GRM] {assunto}"
        msg.attach(MIMEText(corpo, 'html'))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
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
    "Em análise no almoxarifado": ("#2563EB", "Estoque em verificação pelo almoxarifado."),
    "Em processo de compra": ("#7C3AED", "Solicitação encaminhada para o setor de compras."),
    "Atendido pelo almoxarifado": ("#059669", "Estoque confirmado pelo almoxarifado."),
    "Compra solicitada": ("#DB2777", "Dados da compra registrados para prosseguimento."),
}


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
    return f"GRM-{datetime.now():%Y%m%d}-{sequencia:04d}"


def normalizar_itens(dados: pd.DataFrame) -> list[dict[str, Any]]:
    """Remove linhas incompletas e padroniza itens inseridos pelo solicitante."""
    itens = dados.copy()
    if itens.empty:
        return []

    itens["Produto"] = itens["Produto"].fillna("").astype(str).str.strip()
    itens["Quantidade"] = pd.to_numeric(itens["Quantidade"], errors="coerce").fillna(0)
    itens = itens[(itens["Produto"] != "") & (itens["Quantidade"] > 0)]
    itens["Quantidade"] = itens["Quantidade"].astype(int)
    return itens.to_dict(orient="records")


def localizar_solicitacao(protocolo: str) -> dict[str, Any] | None:
    """Localiza uma solicitação pelo protocolo no banco de dados."""
    return db.carregar_por_protocolo(protocolo)


def atualizar_status(solicitacao: dict[str, Any], novo_status: str) -> None:
    """Atualiza status e preserva a data/hora da última movimentação."""
    solicitacao["status"] = novo_status
    solicitacao["atualizado_em"] = datetime.now()
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
    compras = sum(item["status"] in {"Em processo de compra", "Compra solicitada", "Comprado", "Em processo de autorização"} for item in solicitacoes)
    finalizados = sum(item["status"] == "Atendido pelo almoxarifado" for item in solicitacoes)

    colunas = st.columns(4)
    dados = [
        ("Solicitações", total, "total no sistema"),
        ("No almoxarifado", almoxarifado, "em verificação de estoque"),
        ("Em compras", compras, "em processo de aquisição"),
        ("Finalizados", finalizados, "atendidos"),
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
    empresa = st.selectbox("Qual é a empresa?", EMPRESAS, key="form_empresa")
    solicitante = st.text_input("Qual é o seu nome?", placeholder="Digite seu nome", key="form_solicitante")
    setor_solicitante = st.text_input("Qual é o seu setor? (opcional)", placeholder="Ex: Manutenção, Operador, etc", key="form_setor")

    st.write("---")
    st.write("**Quais materiais você precisa?**")
    st.caption("Escreva o nome do material e a quantidade. Para adicionar mais materiais, clique no botão abaixo.")

    # Renderizar campos de materiais fora do formulário para não zerar ao clicar em botões
    for i, item in enumerate(st.session_state.lista_materiais):
        col1, col2 = st.columns([3, 1])
        with col1:
            item["produto"] = st.text_input(f"Material {i+1}", value=item["produto"], key=f"mat_prod_{i}", placeholder="Nome do material")
        with col2:
            item["quantidade"] = st.number_input(f"Qtd {i+1}", value=item["quantidade"], min_value=1, step=1, key=f"mat_qtd_{i}")

    if st.button("➕ Adicionar outro material"):
        st.session_state.lista_materiais.append({"produto": "", "quantidade": 1})
        st.rerun()

    st.write("---")
    observacao = st.text_area("Tem mais alguma informação importante? (opcional)", placeholder="Ex: Urgente, cor específica, etc.", key="form_obs")

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
        agora = datetime.now()
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
            "destino": "",
            "triado_por": "",
            "estoque": [],
            "dados_compra": {},
        }
        db.salvar_solicitacao(solicitacao)
        st.session_state.solicitacoes = db.carregar_todas()
        st.session_state.ultimo_protocolo = protocolo

        # Limpar a lista de materiais após o envio
        st.session_state.lista_materiais = [{"produto": "", "quantidade": 1}]

        st.balloons()
        st.success(f"Sua solicitação foi enviada com sucesso! Anote este código para acompanhar depois: **{protocolo}**")


def renderizar_card_solicitacao(solicitacao: dict) -> None:
    """Renderiza um card compacto para a grade de acompanhamento com expander."""
    cor, descricao = STATUS_META.get(solicitacao["status"], ("#475569", "Status atualizado."))

    # Resumo no card
    empresa_curta = solicitacao["empresa"].split(" - ")[0] if " - " in solicitacao["empresa"] else solicitacao["empresa"][:25]
    itens_resumo = ", ".join(
        [f"{i['Produto']} (x{i['Quantidade']})" for i in solicitacao["itens"][:3]]
    )
    if len(solicitacao["itens"]) > 3:
        itens_resumo += f" (+{len(solicitacao['itens']) - 3} mais)"

    card_html = f"""
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-left:5px solid {cor};border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.6rem;box-shadow:0 2px 8px rgba(15,23,42,.04);">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
            <div>
                <span style="font-size:.75rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">{escape(solicitacao['protocolo'])}</span>
                <div style="font-size:.95rem;color:#0F172A;font-weight:700;margin:.15rem 0;">{escape(empresa_curta)}</div>
                <span style="font-size:.78rem;color:#64748B;">{itens_resumo}</span>
            </div>
            <span class="status-chip" style="background:{cor};">{escape(solicitacao['status'])}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def renderizar_grade_acompanhamento(solicitacoes: list[dict]) -> None:
    """Renderiza a grade de solicitações com expander para detalhes."""
    if not solicitacoes:
        st.info("Nenhuma solicitação encontrada.")
        return

    st.caption(f"**{len(solicitacoes)}** solicitação(ões) encontrada(s)")

    for solicitacao in solicitacoes:
        cor, descricao = STATUS_META.get(solicitacao["status"], ("#475569", "Status atualizado."))
        empresa_curta = solicitacao["empresa"].split(" - ")[0] if " - " in solicitacao["empresa"] else solicitacao["empresa"][:25]
        itens_resumo = ", ".join(
            [f"{i['Produto']} (x{i['Quantidade']})" for i in solicitacao["itens"][:3]]
        )
        if len(solicitacao["itens"]) > 3:
            itens_resumo += f" (+{len(solicitacao['itens']) - 3} mais)"

        card_html = f"""
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-left:5px solid {cor};border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.5rem;box-shadow:0 2px 8px rgba(15,23,42,.04);">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                <div>
                    <span style="font-size:.75rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">{escape(solicitacao['protocolo'])}</span>
                    <div style="font-size:.95rem;color:#0F172A;font-weight:700;margin:.15rem 0;">{escape(empresa_curta)}</div>
                    <span style="font-size:.78rem;color:#64748B;">{itens_resumo}</span>
                </div>
                <span class="status-chip" style="background:{cor};">{escape(solicitacao['status'])}</span>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        with st.expander("Ver detalhes completos", expanded=False):
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

        st.markdown("")


def pagina_acompanhar_status() -> None:
    """Permite a consulta de solicitações por protocolo ou por empresa em formato de grade."""
    st.subheader("Acompanhar status")
    st.write("Consulte a evolução das suas solicitações abaixo.")

    opcao_busca = st.radio(
        "Método de busca",
        ["Todas as solicitações", "Por protocolo", "Por empresa"],
        horizontal=True
    )

    # Recarregar do banco para garantir dados atualizados
    solicitacoes = db.carregar_todas()

    if opcao_busca == "Todas as solicitações":
        renderizar_grade_acompanhamento(solicitacoes)

    elif opcao_busca == "Por protocolo":
        protocolo_padrao = st.session_state.ultimo_protocolo
        protocolo = st.text_input("Protocolo da solicitação", value=protocolo_padrao, placeholder="Ex.: GRM-20260720-0001")
        consultar = st.button("Consultar status", type="primary")

        if consultar:
            solicitacao = localizar_solicitacao(protocolo.strip().upper())
            if not solicitacao:
                st.warning("Nenhuma solicitação foi encontrada com esse protocolo.")
                return
            renderizar_grade_acompanhamento([solicitacao])

    else:
        empresa_selecionada = st.selectbox("Selecione a empresa", EMPRESAS[1:])
        filtrar = st.button("Filtrar solicitações", type="primary")

        if filtrar:
            solicitacoes_filtradas = [s for s in solicitacoes if s['empresa'] == empresa_selecionada]
            if not solicitacoes_filtradas:
                st.warning(f"Nenhuma solicitação encontrada para {empresa_selecionada}.")
                return
            renderizar_grade_acompanhamento(solicitacoes_filtradas)


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
        atualizar_status(solicitacao, novo_status)
        st.success(f"{solicitacao['protocolo']} encaminhada para {destino.lower()}.")

        itens_html = "<ul>" + "".join([f"<li>{item['Produto']} - Qtd: {item['Quantidade']}</li>" for item in solicitacao['itens']]) + "</ul>"
        corpo_email = f"""
        <h3>Solicitação Encaminhada</h3>
        <p><strong>Protocolo:</strong> {solicitacao['protocolo']}</p>
        <p><strong>Empresa:</strong> {solicitacao['empresa']}</p>
        <p><strong>Solicitante:</strong> {solicitacao['solicitante']}</p>
        <p><strong>Setor Destino:</strong> {destino}</p>
        <p><strong>Usuário:</strong> {st.session_state.usuario_autenticado}</p>
        <h4>Itens:</h4>
        {itens_html}
        """
        enviar_email_notificacao(f"Encaminhamento: {solicitacao['protocolo']}", corpo_email)
        st.rerun()


def pagina_almoxarifado() -> None:
    """Painel do almoxarifado com grade de requisições, conferência via checkboxes e encaminhamento automático para compras."""

    # Recarregar solicitações do banco
    st.session_state.solicitacoes = db.carregar_todas()
    solicitacoes_pendentes = [
        item for item in st.session_state.solicitacoes
        if item["status"] == "Em análise no almoxarifado"
    ]

    # --- RESUMO DE PENDÊNCIAS POR EMPRESA ---
    st.markdown("### 📊 Resumo de solicitações pendentes")
    if not solicitacoes_pendentes:
        st.info("Não há solicitações em análise no almoxarifado no momento.")
    else:
        contagem_por_empresa: dict[str, int] = {}
        for s in solicitacoes_pendentes:
            empresa = s["empresa"]
            contagem_por_empresa[empresa] = contagem_por_empresa.get(empresa, 0) + 1

        st.caption(f"Total de solicitações pendentes: **{len(solicitacoes_pendentes)}** em **{len(contagem_por_empresa)}** empresa(s)")

        cols = st.columns(min(len(contagem_por_empresa), 3))
        for idx, (empresa, qtd) in enumerate(sorted(contagem_por_empresa.items())):
            col = cols[idx % len(cols)]
            with col:
                st.markdown(
                    f"""
                    <div class="empresa-card">
                        <div class="empresa-nome">{escape(empresa)}</div>
                        <div class="empresa-qtd">{qtd}</div>
                        <div class="empresa-label">solicitação(ões) pendente(s)</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # --- PAINEL DE ATENDIMENTO COM GRADE ---
    st.markdown("### 🔍 Verificar e atender solicitações")

    if not solicitacoes_pendentes:
        return

    # Modo de visualização
    modo_visualizacao = st.radio(
        "Modo de visualização",
        ["Todas as solicitações", "Por empresa"],
        horizontal=True,
        key="modo_viz_almox",
    )

    if modo_visualizacao == "Por empresa":
        empresas_com_pendencia = sorted(set(s["empresa"] for s in solicitacoes_pendentes))
        empresa_filtro = st.selectbox(
            "Selecione a empresa para ver as solicitações",
            empresas_com_pendencia,
            key="empresa_filtro_almox",
        )
        solicitacoes_filtradas = [s for s in solicitacoes_pendentes if s["empresa"] == empresa_filtro]
    else:
        solicitacoes_filtradas = solicitacoes_pendentes

    if not solicitacoes_filtradas:
        st.info("Nenhuma solicitação encontrada para o filtro selecionado.")
        return

    st.caption(f"**{len(solicitacoes_filtradas)}** solicitação(ões) para atender")

    # --- GRADE DE SOLICITAÇÕES COM EXPANDER ---
    for solicitacao in solicitacoes_filtradas:
        # Card compacto com resumo
        itens_resumo = ", ".join(
            [f"{i['Produto']} (x{i['Quantidade']})" for i in solicitacao["itens"][:3]]
        )
        if len(solicitacao["itens"]) > 3:
            itens_resumo += f" (+{len(solicitacao['itens']) - 3} mais)"

        card_html = f"""
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-left:5px solid #F59E0B;border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.5rem;box-shadow:0 2px 8px rgba(15,23,42,.04);">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                <div>
                    <span style="font-size:.75rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">{escape(solicitacao['protocolo'])}</span>
                    <div style="font-size:.95rem;color:#0F172A;font-weight:700;margin:.15rem 0;">{escape(solicitacao['empresa'])}</div>
                    <span style="font-size:.78rem;color:#64748B;">Solicitante: {escape(solicitacao['solicitante'])}</span>
                    <span style="font-size:.78rem;color:#64748B;margin-left:.8rem;">{itens_resumo}</span>
                </div>
                <span class="status-chip" style="background:#F59E0B;">Em análise</span>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # Expander para verificar estoque com checkboxes
        with st.expander("📋 Ver detalhes e conferir itens", expanded=False):
            if solicitacao.get("observacao_triagem"):
                st.info(f"Observação da triagem: {solicitacao['observacao_triagem']}")

            st.markdown("#### Itens solicitados")
            
            # Inicializar estado de checkboxes se não existir
            checkbox_key_prefix = f"checkbox_{solicitacao['protocolo']}"
            if checkbox_key_prefix not in st.session_state:
                st.session_state[checkbox_key_prefix] = {}
                for item in solicitacao["itens"]:
                    st.session_state[checkbox_key_prefix][item["Produto"]] = True
            
            # Exibir checkboxes para cada item
            itens_conferidos = {}
            for item in solicitacao["itens"]:
                produto = item["Produto"]
                qtd = item["Quantidade"]
                
                col1, col2, col3 = st.columns([0.5, 2, 1])
                with col1:
                    tem_produto = st.checkbox(
                        "✓",
                        value=st.session_state[checkbox_key_prefix].get(produto, True),
                        key=f"{checkbox_key_prefix}_{produto}",
                        label_visibility="collapsed"
                    )
                    itens_conferidos[produto] = tem_produto
                with col2:
                    st.write(f"**{produto}**")
                with col3:
                    st.write(f"Qtd: {qtd}")
            
            # Atualizar estado da sessão
            st.session_state[checkbox_key_prefix] = itens_conferidos
            
            observacao = st.text_area(
                "Observação do almoxarifado (opcional)",
                key=f"obs_estoque_{solicitacao['protocolo']}",
                placeholder="Informe detalhes sobre a disponibilidade ou prazo de reposição.",
            )

            # Botão de ação
            acao_col1, acao_col2 = st.columns([1, 1])
            if acao_col1.button("✅ Confirmar conferência", type="primary", width="stretch", key=f"confirmar_estoque_{solicitacao['protocolo']}"):
                # Verificar se todos os itens foram marcados como disponíveis
                tem_indisponivel = any(not v for v in itens_conferidos.values())
                
                # Salvar dados de conferência
                solicitacao["estoque"] = [
                    {
                        "Produto": item["Produto"],
                        "Qtd. solicitada": item["Quantidade"],
                        "Qtd. disponível": item["Quantidade"] if itens_conferidos.get(item["Produto"], False) else 0,
                        "Situação": "Disponível" if itens_conferidos.get(item["Produto"], False) else "Indisponível",
                    }
                    for item in solicitacao["itens"]
                ]
                solicitacao["observacao_almoxarifado"] = observacao.strip()
                
                itens_html = "<ul>" + "".join(
                    [
                        f"<li>{item['Produto']} - Qtd: {item['Qtd. solicitada']} - {item['Situação']}</li>"
                        for item in solicitacao["estoque"]
                    ]
                ) + "</ul>"

                if tem_indisponivel:
                    # Encaminhar automaticamente para compras
                    novo_status = "Em processo de compra"
                    solicitacao["destino"] = "Compras"
                    solicitacao["triado_por"] = st.session_state.usuario_autenticado
                    atualizar_status(solicitacao, novo_status)
                    st.success(f"Itens indisponíveis em {solicitacao['protocolo']}. Encaminhada automaticamente para Compras.")

                    corpo_email = f"""
                    <h3>Retorno do Almoxarifado — Encaminhada para Compras</h3>
                    <p><strong>Protocolo:</strong> {solicitacao['protocolo']}</p>
                    <p><strong>Empresa:</strong> {solicitacao['empresa']}</p>
                    <p><strong>Solicitante:</strong> {solicitacao['solicitante']}</p>
                    <p><strong>Status:</strong> Em processo de compra (itens indisponíveis)</p>
                    <h4>Itens:</h4>
                    {itens_html}
                    """
                    enviar_email_notificacao(f"Almox → Compras: {solicitacao['protocolo']}", corpo_email)
                else:
                    # Todos disponíveis, atender pelo almoxarifado
                    atualizar_status(solicitacao, "Atendido pelo almoxarifado")
                    st.success(f"Todos os itens confirmados para {solicitacao['protocolo']}.")

                    corpo_email = f"""
                    <h3>Retorno do Almoxarifado</h3>
                    <p><strong>Protocolo:</strong> {solicitacao['protocolo']}</p>
                    <p><strong>Empresa:</strong> {solicitacao['empresa']}</p>
                    <p><strong>Solicitante:</strong> {solicitacao['solicitante']}</p>
                    <p><strong>Status Final:</strong> Atendido pelo almoxarifado</p>
                    <h4>Itens:</h4>
                    {itens_html}
                    """
                    enviar_email_notificacao(f"Retorno Almoxarifado: {solicitacao['protocolo']}", corpo_email)

                st.rerun()

            if acao_col2.button("⏸️ Deixar pendente", width="stretch", key=f"pendente_{solicitacao['protocolo']}"):
                st.info(f"{solicitacao['protocolo']} permanecerá em análise.")


def pagina_compras() -> None:
    """Registra dados de compra: status (Comprado ou Em processo de autorização)."""
    st.subheader("Painel de compras")
    st.write("Registre o status da compra dos itens solicitados.")

    # Recarregar solicitações do banco
    st.session_state.solicitacoes = db.carregar_todas()
    solicitacoes = [item for item in st.session_state.solicitacoes if item["status"] == "Em processo de compra"]
    if not solicitacoes:
        st.info("Não há solicitações aguardando tratamento pelo setor de compras no momento.")
        return

    opcoes = {
        f"{item['protocolo']} — {item['empresa']} — prioridade {item['prioridade']}": item["protocolo"]
        for item in solicitacoes
    }
    selecao = st.selectbox("Solicitação encaminhada a compras", list(opcoes), key="selecionar_compras")
    solicitacao = localizar_solicitacao(opcoes[selecao])
    assert solicitacao is not None

    st.markdown("#### Itens para compra")
    st.dataframe(pd.DataFrame(solicitacao["itens"]), hide_index=True, width="stretch")
    
    with st.form(f"formulario_compras_{solicitacao['protocolo']}"):
        st.markdown("#### Status da compra")
        status_compra = st.radio(
            "Qual é o status da compra?",
            ["Comprado", "Em processo de autorização"],
            horizontal=True,
            help="Selecione se a compra já foi realizada ou se ainda está em processo de autorização."
        )
        
        esquerda, direita = st.columns(2)
        with esquerda:
            fornecedor = st.text_input("Fornecedor", placeholder="Ex.: Fornecedor ABC")
            previsao = st.date_input("Previsão de entrega", value=date.today())
        with direita:
            responsavel = st.text_input("Responsável pela compra", value="compras", placeholder="Ex.: Ana Souza")
            centro_custo = st.text_input("Centro de custo", placeholder="Ex.: CC-1001")
        
        observacao = st.text_area("Observação para compras", placeholder="Inclua condições, urgência ou referências de cotação.")
        registrar = st.form_submit_button("Registrar dados de compra", type="primary", width="stretch")

    if registrar:
        solicitacao["dados_compra"] = {
            "status_compra": status_compra,
            "fornecedor": fornecedor.strip() or "Não informado",
            "previsao": previsao.strftime("%d/%m/%Y"),
            "responsavel": responsavel.strip() or "Não informado",
            "centro_custo": centro_custo.strip() or "Não informado",
            "observacao": observacao.strip(),
        }
        atualizar_status(solicitacao, "Compra solicitada")
        st.success(f"Dados de compra registrados para {solicitacao['protocolo']}.")

        itens_html = "<ul>" + "".join([f"<li>{item['Produto']} - Qtd: {item['Quantidade']}</li>" for item in solicitacao['itens']]) + "</ul>"
        corpo_email = f"""
        <h3>Dados de Compra Registrados</h3>
        <p><strong>Protocolo:</strong> {solicitacao['protocolo']}</p>
        <p><strong>Empresa:</strong> {solicitacao['empresa']}</p>
        <p><strong>Solicitante:</strong> {solicitacao['solicitante']}</p>
        <p><strong>Status da Compra:</strong> {status_compra}</p>
        <p><strong>Fornecedor:</strong> {solicitacao['dados_compra']['fornecedor']}</p>
        <p><strong>Previsão:</strong> {solicitacao['dados_compra']['previsao']}</p>
        <p><strong>Responsável:</strong> {solicitacao['dados_compra']['responsavel']}</p>
        <h4>Itens:</h4>
        {itens_html}
        """
        enviar_email_notificacao(f"Dados de Compra: {solicitacao['protocolo']}", corpo_email)
        st.rerun()


def main() -> None:
    configurar_pagina()
    inicializar_estado()

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
