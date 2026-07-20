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
    conn = get_connection()
    cursor = conn.cursor()
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

# Inicializa o banco ao importar o módulo
init_db()
