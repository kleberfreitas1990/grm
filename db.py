import sqlite3
import json
from datetime import datetime
from typing import Any

DATABASE_PATH = "grm_data.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Cria todas as tabelas necessárias e insere os usuários padrão se ainda não existirem."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de solicitações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes (
            protocolo TEXT PRIMARY KEY,
            empresa TEXT NOT NULL,
            solicitante TEXT NOT NULL,
            setor TEXT NOT NULL,
            prioridade TEXT NOT NULL,
            status TEXT NOT NULL,
            destino TEXT,
            triado_por TEXT,
            observacao_triagem TEXT,
            observacao_almoxarifado TEXT,
            dados_compra TEXT,
            estoque TEXT,
            itens TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de usuários internos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            chave TEXT PRIMARY KEY,
            rotulo TEXT NOT NULL,
            senha TEXT NOT NULL,
            permissoes TEXT NOT NULL
        )
    ''')

    # Inserir usuários padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) as count FROM usuarios")
    total = cursor.fetchone()['count']
    if total == 0:
        cursor.execute(
            "INSERT INTO usuarios (chave, rotulo, senha, permissoes) VALUES (?, ?, ?, ?)",
            ("compras", "Compras", "Grm@2026", "atendimento,compras")
        )
        cursor.execute(
            "INSERT INTO usuarios (chave, rotulo, senha, permissoes) VALUES (?, ?, ?, ?)",
            ("almoxarifado", "Almoxarifado", "Grm@2026", "almoxarifado")
        )

    conn.commit()
    conn.close()


def salvar_solicitacao(solicitacao: dict[str, Any]) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO solicitacoes (
            protocolo, empresa, solicitante, setor, prioridade, status,
            destino, triado_por, observacao_triagem, observacao_almoxarifado,
            dados_compra, estoque, itens, criado_em, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        solicitacao['protocolo'],
        solicitacao['empresa'],
        solicitacao['solicitante'],
        solicitacao.get('setor', ''),
        solicitacao['prioridade'],
        solicitacao['status'],
        solicitacao.get('destino', ''),
        solicitacao.get('triado_por', ''),
        solicitacao.get('observacao_triagem', ''),
        solicitacao.get('observacao_almoxarifado', ''),
        json.dumps(solicitacao.get('dados_compra', {})),
        json.dumps(solicitacao.get('estoque', [])),
        json.dumps(solicitacao['itens']),
        solicitacao.get('criado_em', datetime.now().isoformat()),
        solicitacao.get('atualizado_em', datetime.now().isoformat())
    ))

    conn.commit()
    conn.close()


def carregar_todas() -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM solicitacoes ORDER BY criado_em DESC')

    solicitacoes = []
    for row in cursor.fetchall():
        solicitacao = dict(row)
        solicitacao['itens'] = json.loads(solicitacao['itens'])
        solicitacao['dados_compra'] = json.loads(solicitacao['dados_compra']) if solicitacao['dados_compra'] else {}
        solicitacao['estoque'] = json.loads(solicitacao['estoque']) if solicitacao['estoque'] else []
        solicitacao['criado_em'] = datetime.fromisoformat(solicitacao['criado_em'])
        solicitacao['atualizado_em'] = datetime.fromisoformat(solicitacao['atualizado_em'])
        solicitacoes.append(solicitacao)

    conn.close()
    return solicitacoes


def carregar_por_protocolo(protocolo: str) -> dict[str, Any] | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM solicitacoes WHERE protocolo = ?', (protocolo,))
    row = cursor.fetchone()

    if row:
        solicitacao = dict(row)
        solicitacao['itens'] = json.loads(solicitacao['itens'])
        solicitacao['dados_compra'] = json.loads(solicitacao['dados_compra']) if solicitacao['dados_compra'] else {}
        solicitacao['estoque'] = json.loads(solicitacao['estoque']) if solicitacao['estoque'] else []
        solicitacao['criado_em'] = datetime.fromisoformat(solicitacao['criado_em'])
        solicitacao['atualizado_em'] = datetime.fromisoformat(solicitacao['atualizado_em'])
        conn.close()
        return solicitacao

    conn.close()
    return None


def obter_sequencia_protocolo() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    hoje = datetime.now().strftime("%Y%m%d")
    cursor.execute("SELECT COUNT(*) as count FROM solicitacoes WHERE protocolo LIKE ?", (f"GRM-{hoje}-%",))
    count = cursor.fetchone()['count']
    conn.close()
    return count + 1


def obter_usuario(chave: str) -> dict[str, Any] | None:
    """Retorna os dados de um usuário pelo chave (ex: 'compras', 'almoxarifado')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def obter_senha_usuario(chave: str) -> str | None:
    """Retorna a senha de um usuário pelo chave."""
    usuario = obter_usuario(chave)
    if usuario:
        return usuario["senha"]
    return None


def obter_permissoes_usuario(chave: str) -> list[str]:
    """Retorna a lista de permissões de um usuário."""
    usuario = obter_usuario(chave)
    if usuario:
        return usuario["permissoes"].split(",")
    return []


# Inicializa o banco ao importar o módulo
init_db()
