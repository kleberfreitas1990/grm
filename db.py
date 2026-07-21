"""Persistência das solicitações do GRM com TiDB Cloud e fallback SQLite."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

DATABASE_PATH = "grm_data.db"


def _usar_sqlite_forcado() -> bool:
    """Permite isolar testes e desenvolvimento local do banco remoto."""
    return os.getenv("GRM_USE_SQLITE", "").strip().lower() in {"1", "true", "yes"}


def _init_engine():
    """Inicializa TiDB quando configurado; caso contrário, utiliza SQLite local."""
    if not _usar_sqlite_forcado():
        try:
            import streamlit as st

            if "connections" in st.secrets and "tidb" in st.secrets["connections"]:
                conn = st.connection("tidb", type="sql")
                conn.query("SELECT 1 AS conectado", ttl=0)
                return conn, False
        except Exception as exc:
            import streamlit as st

            if "connections" in st.secrets and "tidb" in st.secrets["connections"]:
                st.error(f"Erro crítico de conexão com o banco de dados: {exc}")
                raise

    import sqlite3

    class SQLiteEngine:
        def __init__(self, path: str):
            self.path = path

        def _conn(self):
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            return conn

        def query(self, sql: str, ttl: int = 0, params=None):
            import pandas as pd

            conn = self._conn()
            try:
                return pd.read_sql_query(sql, conn, params=params)
            finally:
                conn.close()

        def session(self):
            return SQLiteSession(self.path)

    class SQLiteSession:
        def __init__(self, path: str):
            self.conn = sqlite3.connect(path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close()

        def execute(self, sql: str, params=None):
            if params is None:
                self.cursor.execute(sql)
            else:
                self.cursor.execute(sql, params)

    return SQLiteEngine(DATABASE_PATH), True


def _serializar_json(valor: Any) -> str:
    """Serializa estruturas de dados sem perder caracteres UTF-8."""
    return json.dumps(valor, ensure_ascii=False, default=str)


def _desserializar_json(valor: Any, padrao: Any) -> Any:
    """Recupera JSON salvo sem interromper registros legados incompletos."""
    if valor is None or valor == "":
        return padrao
    if isinstance(valor, float) and str(valor).lower() == "nan":
        return padrao
    if isinstance(valor, (dict, list)):
        return valor
    try:
        return json.loads(valor)
    except (TypeError, ValueError, json.JSONDecodeError):
        return padrao


def _normalizar_datetime(valor: Any) -> datetime:
    """Converte valores vindos de SQLite, pandas ou TiDB para datetime."""
    if isinstance(valor, datetime):
        return valor
    if hasattr(valor, "to_pydatetime"):
        return valor.to_pydatetime()
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor)
        except ValueError:
            try:
                return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
    return datetime.now()


class _DBManager:
    """Gerenciador único de solicitações e usuários do GRM."""

    def __init__(self):
        self.engine, self._is_sqlite = _init_engine()
        self._init_tables()

    def _init_tables(self) -> None:
        if self._is_sqlite:
            self._init_tables_sqlite()
        else:
            self._init_tables_tidb()

    def _init_tables_sqlite(self) -> None:
        with self.engine.session() as session:
            session.execute(
                """
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
                    dados_logistica TEXT,
                    historico_status TEXT,
                    estoque TEXT,
                    itens TEXT NOT NULL,
                    criado_em TEXT DEFAULT (datetime('now')),
                    atualizado_em TEXT DEFAULT (datetime('now'))
                )
                """
            )
            colunas = {
                linha[1]
                for linha in session.cursor.execute("PRAGMA table_info(solicitacoes)").fetchall()
            }
            for coluna in ("dados_logistica", "historico_status"):
                if coluna not in colunas:
                    session.execute(f"ALTER TABLE solicitacoes ADD COLUMN {coluna} TEXT")

            session.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    chave TEXT PRIMARY KEY,
                    rotulo TEXT NOT NULL,
                    senha TEXT NOT NULL,
                    permissoes TEXT NOT NULL
                )
                """
            )
            total = session.cursor.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
            if total == 0:
                session.execute(
                    "INSERT INTO usuarios (chave, rotulo, senha, permissoes) VALUES (?, ?, ?, ?)",
                    ("compras", "Compras", "Grm@2026", "atendimento,compras"),
                )
                session.execute(
                    "INSERT INTO usuarios (chave, rotulo, senha, permissoes) VALUES (?, ?, ?, ?)",
                    ("almoxarifado", "Almoxarifado", "Grm@2026", "almoxarifado"),
                )

    def _executar_tidb(self, sql: str, params: dict[str, Any] | None = None) -> None:
        """Executa escrita transacional por meio da sessão SQLAlchemy do Streamlit."""
        from sqlalchemy import text

        with self.engine.session as session:
            session.execute(text(sql), params or {})
            session.commit()

    def _consultar_tidb(self, sql: str, params: dict[str, Any] | None = None):
        """Executa consulta parametrizada no TiDB sem depender do cache de leitura do Streamlit."""
        import pandas as pd
        from sqlalchemy import text

        with self.engine.session as session:
            resultado = session.execute(text(sql), params or {})
            linhas = [dict(linha) for linha in resultado.mappings().all()]
        return pd.DataFrame(linhas)

    def _init_tables_tidb(self) -> None:
        self._executar_tidb(
            """
            CREATE TABLE IF NOT EXISTS solicitacoes (
                protocolo VARCHAR(64) PRIMARY KEY,
                empresa VARCHAR(255) NOT NULL,
                solicitante VARCHAR(255) NOT NULL,
                setor VARCHAR(255) NOT NULL DEFAULT '',
                prioridade VARCHAR(50) NOT NULL DEFAULT 'Normal',
                status VARCHAR(100) NOT NULL,
                destino VARCHAR(100) DEFAULT '',
                triado_por VARCHAR(100) DEFAULT '',
                observacao_triagem TEXT,
                observacao_almoxarifado TEXT,
                dados_compra TEXT,
                dados_logistica TEXT,
                historico_status TEXT,
                estoque TEXT,
                itens TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self._executar_tidb(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                chave VARCHAR(64) PRIMARY KEY,
                rotulo VARCHAR(100) NOT NULL,
                senha VARCHAR(255) NOT NULL,
                permissoes VARCHAR(500) NOT NULL
            )
            """
        )
        self._executar_tidb(
            """
            INSERT IGNORE INTO usuarios (chave, rotulo, senha, permissoes)
            VALUES ('compras', 'Compras', 'Grm@2026', 'atendimento,compras')
            """
        )
        self._executar_tidb(
            """
            INSERT IGNORE INTO usuarios (chave, rotulo, senha, permissoes)
            VALUES ('almoxarifado', 'Almoxarifado', 'Grm@2026', 'almoxarifado')
            """
        )

        from sqlalchemy import text

        with self.engine.session as session:
            colunas = {
                str(linha[0])
                for linha in session.execute(text("SHOW COLUMNS FROM solicitacoes")).all()
            }
            for coluna in ("dados_logistica", "historico_status"):
                if coluna not in colunas:
                    session.execute(text(f"ALTER TABLE solicitacoes ADD COLUMN {coluna} TEXT"))
            session.commit()

    def salvar_solicitacao(self, solicitacao: dict[str, Any]) -> None:
        if self._is_sqlite:
            self._salvar_sqlite(solicitacao)
        else:
            self._salvar_tidb(solicitacao)

    @staticmethod
    def _valores_solicitacao(solicitacao: dict[str, Any]) -> dict[str, Any]:
        criado_em = solicitacao.get("criado_em", datetime.now())
        atualizado_em = solicitacao.get("atualizado_em", datetime.now())
        if isinstance(criado_em, datetime):
            criado_em = criado_em.isoformat()
        if isinstance(atualizado_em, datetime):
            atualizado_em = atualizado_em.isoformat()
        return {
            "protocolo": solicitacao["protocolo"],
            "empresa": solicitacao["empresa"],
            "solicitante": solicitacao["solicitante"],
            "setor": solicitacao.get("setor", ""),
            "prioridade": solicitacao.get("prioridade", "Normal"),
            "status": solicitacao["status"],
            "destino": solicitacao.get("destino", ""),
            "triado_por": solicitacao.get("triado_por", ""),
            "observacao_triagem": solicitacao.get("observacao_triagem", ""),
            "observacao_almoxarifado": solicitacao.get("observacao_almoxarifado", ""),
            "dados_compra": _serializar_json(solicitacao.get("dados_compra", {})),
            "dados_logistica": _serializar_json(solicitacao.get("dados_logistica", {})),
            "historico_status": _serializar_json(solicitacao.get("historico_status", [])),
            "estoque": _serializar_json(solicitacao.get("estoque", [])),
            "itens": _serializar_json(solicitacao["itens"]),
            "criado_em": criado_em,
            "atualizado_em": atualizado_em,
        }

    def _salvar_sqlite(self, solicitacao: dict[str, Any]) -> None:
        valores = self._valores_solicitacao(solicitacao)
        with self.engine.session() as session:
            session.execute(
                """
                INSERT OR REPLACE INTO solicitacoes (
                    protocolo, empresa, solicitante, setor, prioridade, status, destino,
                    triado_por, observacao_triagem, observacao_almoxarifado, dados_compra,
                    dados_logistica, historico_status, estoque, itens, criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(valores.values()),
            )

    def _salvar_tidb(self, solicitacao: dict[str, Any]) -> None:
        valores = self._valores_solicitacao(solicitacao)
        self._executar_tidb(
            """
            INSERT INTO solicitacoes (
                protocolo, empresa, solicitante, setor, prioridade, status, destino,
                triado_por, observacao_triagem, observacao_almoxarifado, dados_compra,
                dados_logistica, historico_status, estoque, itens, criado_em, atualizado_em
            ) VALUES (
                :protocolo, :empresa, :solicitante, :setor, :prioridade, :status, :destino,
                :triado_por, :observacao_triagem, :observacao_almoxarifado, :dados_compra,
                :dados_logistica, :historico_status, :estoque, :itens, :criado_em, :atualizado_em
            )
            ON DUPLICATE KEY UPDATE
                empresa=VALUES(empresa), solicitante=VALUES(solicitante), setor=VALUES(setor),
                prioridade=VALUES(prioridade), status=VALUES(status), destino=VALUES(destino),
                triado_por=VALUES(triado_por), observacao_triagem=VALUES(observacao_triagem),
                observacao_almoxarifado=VALUES(observacao_almoxarifado),
                dados_compra=VALUES(dados_compra), dados_logistica=VALUES(dados_logistica),
                historico_status=VALUES(historico_status), estoque=VALUES(estoque), itens=VALUES(itens),
                atualizado_em=VALUES(atualizado_em)
            """,
            valores,
        )

    def carregar_todas(self) -> list[dict[str, Any]]:
        if self._is_sqlite:
            dataframe = self.engine.query("SELECT * FROM solicitacoes ORDER BY criado_em DESC")
        else:
            dataframe = self._consultar_tidb("SELECT * FROM solicitacoes ORDER BY criado_em DESC")
        return [self._parse_row(linha) for _, linha in dataframe.iterrows()]

    def carregar_por_protocolo(self, protocolo: str) -> dict[str, Any] | None:
        if self._is_sqlite:
            dataframe = self.engine.query(
                "SELECT * FROM solicitacoes WHERE protocolo = ?", params=(protocolo,)
            )
        else:
            dataframe = self._consultar_tidb(
                "SELECT * FROM solicitacoes WHERE protocolo = :protocolo",
                {"protocolo": protocolo},
            )
        if dataframe.empty:
            return None
        return self._parse_row(dataframe.iloc[0])

    @staticmethod
    def _parse_row(row) -> dict[str, Any]:
        solicitacao = dict(row)
        solicitacao["itens"] = _desserializar_json(solicitacao.get("itens"), [])
        solicitacao["dados_compra"] = _desserializar_json(solicitacao.get("dados_compra"), {})
        solicitacao["dados_logistica"] = _desserializar_json(solicitacao.get("dados_logistica"), {})
        solicitacao["historico_status"] = _desserializar_json(solicitacao.get("historico_status"), [])
        solicitacao["estoque"] = _desserializar_json(solicitacao.get("estoque"), [])
        solicitacao["criado_em"] = _normalizar_datetime(solicitacao.get("criado_em"))
        solicitacao["atualizado_em"] = _normalizar_datetime(solicitacao.get("atualizado_em"))
        return solicitacao

    def obter_sequencia_protocolo(self) -> int:
        hoje = datetime.now().strftime("%Y%m%d")
        padrao = f"GRM-{hoje}-%"
        if self._is_sqlite:
            dataframe = self.engine.query(
                "SELECT COUNT(*) AS count FROM solicitacoes WHERE protocolo LIKE ?",
                params=(padrao,),
            )
        else:
            dataframe = self._consultar_tidb(
                "SELECT COUNT(*) AS count FROM solicitacoes WHERE protocolo LIKE :padrao",
                {"padrao": padrao},
            )
        return int(dataframe.iloc[0]["count"]) + 1

    def obter_usuario(self, chave: str) -> dict[str, Any] | None:
        if self._is_sqlite:
            dataframe = self.engine.query(
                "SELECT * FROM usuarios WHERE chave = ?", params=(chave,)
            )
        else:
            dataframe = self._consultar_tidb(
                "SELECT * FROM usuarios WHERE chave = :chave",
                {"chave": chave},
            )
        if dataframe.empty:
            return None
        return dict(dataframe.iloc[0])

    def obter_senha_usuario(self, chave: str) -> str | None:
        usuario = self.obter_usuario(chave)
        return str(usuario["senha"]) if usuario else None

    def obter_permissoes_usuario(self, chave: str) -> list[str]:
        usuario = self.obter_usuario(chave)
        if not usuario:
            return []
        return [permissao for permissao in str(usuario["permissoes"]).split(",") if permissao]


_manager = _DBManager()


def salvar_solicitacao(solicitacao: dict[str, Any]) -> None:
    _manager.salvar_solicitacao(solicitacao)


def carregar_todas() -> list[dict[str, Any]]:
    return _manager.carregar_todas()


def carregar_por_protocolo(protocolo: str) -> dict[str, Any] | None:
    return _manager.carregar_por_protocolo(protocolo)


def obter_sequencia_protocolo() -> int:
    return _manager.obter_sequencia_protocolo()


def obter_usuario(chave: str) -> dict[str, Any] | None:
    return _manager.obter_usuario(chave)


def obter_senha_usuario(chave: str) -> str | None:
    return _manager.obter_senha_usuario(chave)


def obter_permissoes_usuario(chave: str) -> list[str]:
    return _manager.obter_permissoes_usuario(chave)
