"""Aplicação Streamlit para o fluxo de requisições de materiais do GRM.

Versão da aplicação: 0.1.0
Os dados desta versão ficam na sessão do navegador, para demonstrar o fluxo
antes da integração com uma base de dados e autenticação corporativa.
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


APP_VERSION = "0.10.0"

# As senhas são lidas de segredos de implantação ou de variáveis de ambiente.
# Nenhuma credencial deve ser incluída no repositório.
USUARIOS_CONFIGURADOS: dict[str, dict[str, Any]] = {
    "suprimentos": {
        "rotulo": "Suprimentos",
        "chave_senha": "GRM_SUPRIMENTOS_PASSWORD",
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
        initial_sidebar_state="expanded",
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

            /* Sidebar Desktop */
            div[data-testid="stSidebar"] { background: #0F2538; }
            div[data-testid="stSidebar"] * { color: #F8FAFC; }
            div[data-testid="stSidebar"] .stCaption { color: #CBD5E1 !important; }

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
          <h1>Gestão de Requisições de Materiais</h1>
          <p>Registre, direcione e acompanhe solicitações entre o atendimento, o almoxarifado e as compras.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    total = len(st.session_state.solicitacoes)
    triagem = sum(item["status"] == "Aguardando triagem" for item in st.session_state.solicitacoes)
    almoxarifado = sum(item["status"] == "Em análise no almoxarifado" for item in st.session_state.solicitacoes)
    compras = sum(item["status"] in {"Em processo de compra", "Compra solicitada"} for item in st.session_state.solicitacoes)

    colunas = st.columns(4)
    dados = [
        ("Solicitações", total, "registradas nesta sessão"),
        ("Aguardando triagem", triagem, "pendentes de atendimento"),
        ("No almoxarifado", almoxarifado, "em verificação de estoque"),
        ("Em compras", compras, "em processo de aquisição"),
    ]
    for coluna, (rotulo, valor, legenda) in zip(colunas, dados):
        coluna.markdown(
            f'<div class="metric-card"><div class="label">{rotulo}</div>'
            f'<div class="value">{valor}</div><div class="caption">{legenda}</div></div>',
            unsafe_allow_html=True,
        )


def renderizar_fluxo() -> None:
    """Exibe a tradução resumida do fluxo que originou a tela."""
    with st.expander("Visualizar fluxo de atendimento", expanded=False):
        colunas = st.columns(5)
        etapas = [
            ("1", "Solicitante", "Seleciona a empresa e informa itens."),
            ("2", "Gravar", "Gera protocolo e aguarda triagem."),
            ("3", "Atendente", "Valida o acesso e direciona a demanda."),
            ("4", "Setor", "Almoxarifado consulta estoque ou compras registra aquisição."),
            ("5", "Acompanhar", "Solicitante consulta a evolução do protocolo."),
        ]
        for coluna, (numero, titulo, texto) in zip(colunas, etapas):
            coluna.markdown(
                f'<div class="flow-step"><span class="number">{numero}</span>'
                f'<strong>{titulo}</strong><span>{texto}</span></div>',
                unsafe_allow_html=True,
            )


def pagina_nova_solicitacao_simplificada() -> None:
    """Formulário extremamente simples e acessível para o solicitante."""
    st.write("Preencha as informações abaixo para solicitar os materiais.")

    # Inicializar lista de materiais no session_state fora do form
    if "lista_materiais" not in st.session_state:
        st.session_state.lista_materiais = [{"produto": "", "quantidade": 1}]

    with st.form("form_simples_solicitante", clear_on_submit=True):
        # Caminho 1: Grande e claro
        empresa = st.selectbox("Qual é a empresa?", EMPRESAS)

        st.write("---")
        solicitante = st.text_input("Qual é o seu nome?", placeholder="Digite seu nome")
        setor_solicitante = st.text_input("Qual é o seu setor? (opcional)", placeholder="Ex: Manutenção, Operador, etc")

        st.write("---")
        st.write("**Quais materiais você precisa?**")
        st.caption("Escreva o nome do material e a quantidade. Para adicionar mais materiais, preencha os campos abaixo.")

        for i, item in enumerate(st.session_state.lista_materiais):
            col1, col2 = st.columns([3, 1])
            with col1:
                item["produto"] = st.text_input(f"Material {i+1}", value=item["produto"], key=f"mat_prod_{i}", placeholder="Nome do material")
            with col2:
                item["quantidade"] = st.number_input(f"Qtd {i+1}", value=item["quantidade"], min_value=1, step=1, key=f"mat_qtd_{i}")

        # Botão de adicionar material fica logo abaixo do último material
        adicionar = st.form_submit_button("Adicionar outro material")

        st.write("---")
        observacao = st.text_area("Tem mais alguma informação importante? (opcional)", placeholder="Ex: Urgente, cor específica, etc.")

        gravar = st.form_submit_button("ENVIAR SOLICITAÇÃO", type="primary", width="stretch")

    if adicionar:
        st.session_state.lista_materiais.append({"produto": "", "quantidade": 1})
        st.rerun()

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
            "status": "Aguardando triagem",
            "criado_em": agora,
            "atualizado_em": agora,
            "destino": "",
            "triado_por": "",
            "estoque": [],
            "dados_compra": {},
        }
        db.salvar_solicitacao(solicitacao)
        st.session_state.solicitacoes.append(solicitacao)
        st.session_state.ultimo_protocolo = protocolo

        # Limpar a lista de materiais após o envio
        st.session_state.lista_materiais = [{"produto": "", "quantidade": 1}]

        st.balloons()
        st.success(f"Sua solicitação foi enviada com sucesso! Anote este código para acompanhar depois: **{protocolo}**")


def pagina_acompanhar_status() -> None:
    """Permite a consulta de uma solicitação pelo protocolo gerado."""
    st.subheader("Acompanhar status")
    st.write("Consulte a evolução de uma solicitação informando o protocolo gerado no momento do registro.")

    opcao_busca = st.radio(
        "Método de busca",
        ["Por protocolo", "Por empresa"],
        horizontal=True
    )

    if opcao_busca == "Por protocolo":
        protocolo_padrao = st.session_state.ultimo_protocolo
        protocolo = st.text_input("Protocolo da solicitação", value=protocolo_padrao, placeholder="Ex.: GRM-20260720-0001")
        consultar = st.button("Consultar status", type="primary")

        if consultar:
            solicitacao = localizar_solicitacao(protocolo.strip().upper())
            if not solicitacao:
                st.warning("Nenhuma solicitação foi encontrada com esse protocolo nesta sessão.")
                return

            exibir_detalhes_solicitacao(solicitacao)

    else:
        empresa_selecionada = st.selectbox("Selecione a empresa", EMPRESAS[1:])
        filtrar = st.button("Filtrar solicitações", type="primary")

        if filtrar:
            solicitacoes = [s for s in st.session_state.solicitacoes if s['empresa'] == empresa_selecionada]
            if not solicitacoes:
                st.warning(f"Nenhuma solicitação encontrada para {empresa_selecionada} nesta sessão.")
                return

            for solicitacao in solicitacoes:
                exibir_detalhes_solicitacao(solicitacao)
                st.markdown("---")


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
    """Obtém a senha de um usuário a partir de configuração segura."""
    dados_usuario = USUARIOS_CONFIGURADOS.get(usuario)
    if not dados_usuario:
        return None

    chave_senha = str(dados_usuario["chave_senha"])
    senha = os.getenv(chave_senha)
    if not senha:
        try:
            senha = st.secrets.get(chave_senha)
        except Exception:
            # Sem arquivo de segredos configurado, a variável de ambiente já foi testada.
            senha = None

    return str(senha).strip() if senha else None


def usuario_tem_permissao(usuario: str, permissao: str) -> bool:
    """Informa se o usuário possui a permissão necessária para uma área."""
    dados_usuario = USUARIOS_CONFIGURADOS.get(usuario)
    if not dados_usuario:
        return False
    return permissao in dados_usuario["permissoes"]


def autenticar_usuario(usuario: str) -> bool:
    """Valida a senha de um usuário configurado sem expor a credencial."""
    if st.session_state.usuario_autenticado == usuario:
        return True

    dados_usuario = USUARIOS_CONFIGURADOS.get(usuario)
    senha_esperada = obter_senha_configurada(usuario)
    if not dados_usuario or not senha_esperada:
        st.error("Acesso indisponível. Solicite ao administrador a configuração desta conta.")
        return False

    with st.form(f"formulario_login_{usuario}"):
        st.text_input("Usuário", value=usuario, disabled=True)
        senha_informada = st.text_input("Senha", type="password")
        acessar = st.form_submit_button("Entrar", type="primary")

    if acessar:
        if not hmac.compare_digest(senha_informada, senha_esperada):
            st.error("Senha inválida. Verifique os dados e tente novamente.")
        else:
            st.session_state.usuario_autenticado = usuario
            st.rerun()
    return False


def pagina_atendimento() -> None:
    """Apresenta a triagem que direciona solicitações ao setor responsável."""
    st.subheader("Atendimento e triagem")
    st.write("Após validar a senha, o atendente analisa a solicitação e encaminha para o almoxarifado ou para compras.")

    st.caption("Acesso exclusivo do usuário suprimentos.")

    pendentes = [item for item in st.session_state.solicitacoes if item["status"] == "Aguardando triagem"]
    if not pendentes:
        st.info("Não há solicitações aguardando triagem nesta sessão.")
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
        <p><strong>Usuário de suprimentos:</strong> {st.session_state.usuario_autenticado}</p>
        <h4>Itens:</h4>
        {itens_html}
        """
        enviar_email_notificacao(f"Encaminhamento: {solicitacao['protocolo']}", corpo_email)
        st.rerun()


def pagina_almoxarifado() -> None:
    """Permite verificar os itens encaminhados ao almoxarifado."""
    st.subheader("Painel do almoxarifado")
    st.write("Registre a disponibilidade dos produtos e conclua o retorno para a solicitação encaminhada.")

    solicitacoes = [item for item in st.session_state.solicitacoes if item["status"] == "Em análise no almoxarifado"]
    if not solicitacoes:
        st.info("Não há solicitações em análise no almoxarifado nesta sessão.")
        return

    opcoes = {
        f"{item['protocolo']} — {item['empresa']} — prioridade {item['prioridade']}": item["protocolo"]
        for item in solicitacoes
    }
    selecao = st.selectbox("Solicitação encaminhada ao almoxarifado", list(opcoes), key="selecionar_almoxarifado")
    solicitacao = localizar_solicitacao(opcoes[selecao])
    assert solicitacao is not None

    st.caption(f"Solicitante: {solicitacao['solicitante']} | Triagem: {solicitacao.get('triado_por', 'Não registrada')}")
    estoque_inicial = pd.DataFrame(
        [
            {
                "Produto": item["Produto"],
                "Qtd. solicitada": item["Quantidade"],
                "Qtd. disponível": item["Quantidade"],
                "Situação": "Disponível",
            }
            for item in solicitacao["itens"]
        ]
    )
    disponibilidade = st.data_editor(
        estoque_inicial,
        column_config={
            "Produto": st.column_config.TextColumn(disabled=True),
            "Qtd. solicitada": st.column_config.NumberColumn(disabled=True),
            "Qtd. disponível": st.column_config.NumberColumn(min_value=0, step=1),
            "Situação": st.column_config.SelectboxColumn("Situação", options=["Disponível", "Parcial", "Indisponível"]),
        },
        hide_index=True,
        width="stretch",
        key=f"estoque_{solicitacao['protocolo']}",
    )
    observacao = st.text_area("Observação do almoxarifado", key=f"obs_estoque_{solicitacao['protocolo']}")
    acao, _ = st.columns([1, 2])
    if acao.button("Confirmar retorno de estoque", type="primary", width="stretch"):
        solicitacao["estoque"] = disponibilidade.to_dict(orient="records")
        solicitacao["observacao_almoxarifado"] = observacao.strip()
        atualizar_status(solicitacao, "Atendido pelo almoxarifado")
        st.success(f"Disponibilidade registrada para {solicitacao['protocolo']}.")

        itens_html = "<ul>" + "".join([f"<li>{item['Produto']} - Qtd. solicitada: {item['Qtd. solicitada']} - Qtd. disponível: {item['Qtd. disponível']} ({item['Situação']})</li>" for item in disponibilidade.to_dict(orient='records')]) + "</ul>"
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


def pagina_compras() -> None:
    """Registra os dados iniciais de compra para solicitações encaminhadas ao setor."""
    st.subheader("Painel de compras")
    st.write("Registre os dados que apoiarão a cotação ou a aquisição dos itens solicitados.")

    solicitacoes = [item for item in st.session_state.solicitacoes if item["status"] == "Em processo de compra"]
    if not solicitacoes:
        st.info("Não há solicitações aguardando tratamento pelo setor de compras nesta sessão.")
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
        esquerda, direita = st.columns(2)
        with esquerda:
            fornecedor = st.text_input("Fornecedor sugerido", placeholder="Ex.: Fornecedor ABC")
            previsao = st.date_input("Previsão de entrega", value=date.today())
        with direita:
            responsavel = st.text_input("Responsável pela compra", value="suprimentos", placeholder="Ex.: Ana Souza")
            centro_custo = st.text_input("Centro de custo", placeholder="Ex.: CC-1001")
        observacao = st.text_area("Observação para compras", placeholder="Inclua condições, urgência ou referências de cotação.")
        registrar = st.form_submit_button("Registrar dados de compra", type="primary", width="stretch")

    if registrar:
        solicitacao["dados_compra"] = {
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

    if st.session_state.perfil == "":
        st.title("Gestão de Requisições de Materiais")
        st.write("Selecione seu acesso para continuar:")

        col_solicitante, col_suprimentos, col_almoxarifado = st.columns(3)

        with col_solicitante:
            if st.button("SOLICITANTE", type="primary", width="stretch"):
                st.session_state.perfil = "solicitante"
                st.rerun()

        with col_suprimentos:
            if st.button("SUPRIMENTOS", type="secondary", width="stretch"):
                st.session_state.perfil = "suprimentos"
                st.rerun()

        with col_almoxarifado:
            if st.button("ALMOXARIFADO", type="secondary", width="stretch"):
                st.session_state.perfil = "almoxarifado"
                st.rerun()

        st.markdown("---")
        st.caption("Versão da aplicação: " + APP_VERSION)
        return

    if st.session_state.perfil == "solicitante":
        st.session_state.setdefault("modo_solicitante", "form")

        if st.session_state.modo_solicitante == "form":
            st.subheader("Nova solicitação de materiais")
            pagina_nova_solicitacao_simplificada()
            if st.button("Verificar o status das minhas solicitações"):
                st.session_state.modo_solicitante = "status"
                st.rerun()

            if st.button("Voltar para a tela inicial"):
                st.session_state.perfil = ""
                st.session_state.modo_solicitante = "form"
                st.rerun()

        else:
            st.subheader("Acompanhar status")
            pagina_acompanhar_status()
            if st.button("Voltar para Nova solicitação"):
                st.session_state.modo_solicitante = "form"
                st.rerun()
            if st.button("Voltar para a tela inicial"):
                st.session_state.perfil = ""
                st.session_state.modo_solicitante = "form"
                st.rerun()

    elif st.session_state.perfil == "suprimentos":
        if not autenticar_usuario("suprimentos"):
            return

        renderizar_cabecalho()
        aba_atendimento, aba_compras = st.tabs(["Atendimento", "Compras"])
        with aba_atendimento:
            pagina_atendimento()
        with aba_compras:
            pagina_compras()

        if st.button("Sair", width="stretch"):
            st.session_state.perfil = ""
            st.session_state.usuario_autenticado = ""
            st.rerun()

    elif st.session_state.perfil == "almoxarifado":
        if not autenticar_usuario("almoxarifado"):
            return

        renderizar_cabecalho()
        pagina_almoxarifado()

        if st.button("Sair", width="stretch"):
            st.session_state.perfil = ""
            st.session_state.usuario_autenticado = ""
            st.rerun()


if __name__ == "__main__":
    main()
