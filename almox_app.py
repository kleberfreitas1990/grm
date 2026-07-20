"""Aplicação Streamlit para o fluxo de requisições de materiais do GRM.

Versão da aplicação: 0.1.0
Os dados desta versão ficam na sessão do navegador, para demonstrar o fluxo
antes da integração com uma base de dados e autenticação corporativa.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from html import escape
from typing import Any

import pandas as pd
import streamlit as st


APP_VERSION = "0.1.0"
EMPRESAS = [
    "Selecione uma empresa",
    "Empresa Matriz",
    "Unidade Industrial",
    "Unidade Comercial",
    "Filial Regional",
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
            .stApp { background: #F7F9FC; }
            [data-testid="stHeader"] { background: rgba(0, 0, 0, 0); }
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
            div[data-testid="stSidebar"] { background: #0F2538; }
            div[data-testid="stSidebar"] * { color: #F8FAFC; }
            div[data-testid="stSidebar"] .stCaption { color: #CBD5E1 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inicializar_estado() -> None:
    """Inicializa somente os dados que precisam sobreviver às interações da sessão."""
    st.session_state.setdefault("solicitacoes", [])
    st.session_state.setdefault("sequencia_protocolo", 1)
    st.session_state.setdefault("atendente_autenticado", False)
    st.session_state.setdefault("atendente_nome", "")
    st.session_state.setdefault("ultimo_protocolo", "")


def gerar_protocolo() -> str:
    """Gera um identificador legível para acompanhamento da solicitação."""
    sequencia = st.session_state.sequencia_protocolo
    st.session_state.sequencia_protocolo += 1
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
    """Localiza uma solicitação pelo protocolo na sessão atual."""
    for solicitacao in st.session_state.solicitacoes:
        if solicitacao["protocolo"] == protocolo:
            return solicitacao
    return None


def atualizar_status(solicitacao: dict[str, Any], novo_status: str) -> None:
    """Atualiza status e preserva a data/hora da última movimentação."""
    solicitacao["status"] = novo_status
    solicitacao["atualizado_em"] = datetime.now()


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


def pagina_nova_solicitacao() -> None:
    """Permite ao solicitante incluir e gravar uma requisição de materiais."""
    st.subheader("Nova solicitação")
    st.write("Informe a empresa, os dados do solicitante e os materiais necessários. Os itens podem ser ajustados antes do envio.")

    with st.form("formulario_nova_solicitacao", clear_on_submit=True):
        esquerda, direita = st.columns(2)
        with esquerda:
            empresa = st.selectbox("Empresa solicitante *", EMPRESAS)
            solicitante = st.text_input("Nome do solicitante *", placeholder="Ex.: Maria da Silva")
        with direita:
            setor_solicitante = st.text_input("Setor solicitante", placeholder="Ex.: Manutenção")
            prioridade = st.selectbox("Prioridade", ["Normal", "Alta", "Urgente"])

        st.markdown("#### Produtos e quantidades")
        st.caption("Inclua uma linha para cada produto. Para editar, clique diretamente na célula correspondente.")
        itens_editados = st.data_editor(
            pd.DataFrame(
                [
                    {"Produto": "", "Quantidade": 1},
                    {"Produto": "", "Quantidade": 1},
                ]
            ),
            column_config={
                "Produto": st.column_config.TextColumn("Produto *", width="large", required=True),
                "Quantidade": st.column_config.NumberColumn("Quantidade *", min_value=1, step=1, required=True),
            },
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="editor_nova_solicitacao",
        )
        observacao = st.text_area("Observação", placeholder="Inclua detalhes que apoiem o atendimento, se necessário.")
        gravar = st.form_submit_button("Gravar solicitação", type="primary", width="stretch")

    if gravar:
        itens = normalizar_itens(itens_editados)
        erros = []
        if empresa == EMPRESAS[0]:
            erros.append("Selecione a empresa solicitante.")
        if not solicitante.strip():
            erros.append("Informe o nome do solicitante.")
        if not itens:
            erros.append("Inclua pelo menos um produto com quantidade maior que zero.")

        if erros:
            for erro in erros:
                st.error(erro)
            return

        protocolo = gerar_protocolo()
        agora = datetime.now()
        st.session_state.solicitacoes.append(
            {
                "protocolo": protocolo,
                "empresa": empresa,
                "solicitante": solicitante.strip(),
                "setor_solicitante": setor_solicitante.strip(),
                "prioridade": prioridade,
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
        )
        st.session_state.ultimo_protocolo = protocolo
        st.success(f"Solicitação registrada com sucesso. Protocolo: {protocolo}")
        st.info("Guarde o protocolo para acompanhar o andamento da solicitação.")


def pagina_acompanhar_status() -> None:
    """Permite a consulta de uma solicitação pelo protocolo gerado."""
    st.subheader("Acompanhar status")
    st.write("Consulte a evolução de uma solicitação informando o protocolo gerado no momento do registro.")

    protocolo_padrao = st.session_state.ultimo_protocolo
    protocolo = st.text_input("Protocolo da solicitação", value=protocolo_padrao, placeholder="Ex.: GRM-20260720-0001")
    consultar = st.button("Consultar status", type="primary")

    if consultar:
        solicitacao = localizar_solicitacao(protocolo.strip().upper())
        if not solicitacao:
            st.warning("Nenhuma solicitação foi encontrada com esse protocolo nesta sessão.")
            return

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


def autenticar_atendente() -> bool:
    """Controla o acesso à área de triagem sem expor a senha no código."""
    if st.session_state.atendente_autenticado:
        return True

    senha_configurada = os.getenv("GRM_ATTENDANT_PASSWORD")
    senha_esperada = senha_configurada or "demo123"
    if not senha_configurada:
        st.warning("Modo demonstração ativo. Configure `GRM_ATTENDANT_PASSWORD` antes de utilizar a aplicação em ambiente real.")

    with st.form("formulario_acesso_atendente"):
        nome = st.text_input("Nome do atendente", placeholder="Ex.: João da Silva")
        senha = st.text_input("Senha de atendimento", type="password")
        acessar = st.form_submit_button("Acessar triagem", type="primary")

    if acessar:
        if not nome.strip():
            st.error("Informe o nome do atendente.")
        elif senha != senha_esperada:
            st.error("Senha inválida. Verifique os dados e tente novamente.")
        else:
            st.session_state.atendente_autenticado = True
            st.session_state.atendente_nome = nome.strip()
            st.rerun()
    return False


def pagina_atendimento() -> None:
    """Apresenta a triagem que direciona solicitações ao setor responsável."""
    st.subheader("Atendimento e triagem")
    st.write("Após validar a senha, o atendente analisa a solicitação e encaminha para o almoxarifado ou para compras.")

    if not autenticar_atendente():
        return

    cabecalho, sair = st.columns([5, 1])
    cabecalho.success(f"Acesso liberado para {st.session_state.atendente_nome}.")
    if sair.button("Sair", width="stretch"):
        st.session_state.atendente_autenticado = False
        st.session_state.atendente_nome = ""
        st.rerun()

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
        solicitacao["triado_por"] = st.session_state.atendente_nome
        solicitacao["observacao_triagem"] = justificativa.strip()
        atualizar_status(solicitacao, novo_status)
        st.success(f"{solicitacao['protocolo']} encaminhada para {destino.lower()}.")
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
            responsavel = st.text_input("Responsável pela compra", placeholder="Ex.: Ana Souza")
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
        st.rerun()


def renderizar_barra_lateral() -> None:
    """Exibe contexto operacional e limites da versão no menu lateral."""
    with st.sidebar:
        st.markdown("## GRM")
        st.caption("Gestão de Requisições de Materiais")
        st.divider()
        st.markdown("**Fluxo da versão 0.1.0**")
        st.caption("Solicitante → Atendimento → Almoxarifado ou Compras → Acompanhamento")
        st.divider()
        st.markdown("**Ambiente de demonstração**")
        st.caption("As solicitações são mantidas apenas durante esta sessão do navegador. A integração com banco de dados e autenticação corporativa deve ser criada antes do uso produtivo.")
        st.divider()
        st.caption(f"Versão da aplicação: {APP_VERSION}")


def main() -> None:
    configurar_pagina()
    inicializar_estado()
    renderizar_barra_lateral()
    renderizar_cabecalho()
    renderizar_fluxo()

    aba_solicitacao, aba_status, aba_atendimento, aba_almoxarifado, aba_compras = st.tabs(
        [
            "Nova solicitação",
            "Acompanhar status",
            "Atendimento",
            "Almoxarifado",
            "Compras",
        ]
    )
    with aba_solicitacao:
        pagina_nova_solicitacao()
    with aba_status:
        pagina_acompanhar_status()
    with aba_atendimento:
        pagina_atendimento()
    with aba_almoxarifado:
        pagina_almoxarifado()
    with aba_compras:
        pagina_compras()


if __name__ == "__main__":
    main()
