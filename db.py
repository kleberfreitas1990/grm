import json
import os
from datetime import datetime
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Banco de dados persistente via TiDB Cloud (SQLAlchemy) com fallback SQLite.
#
# No Streamlit Cloud, o SQLite local é apagado a cada deploy/hibernação.
# Para evitar perda de dados, a aplicação usa TiDB Cloud quando a connection
# está configurada nos secrets. Em ambiente local (desenvolvimento), usa SQLite.
# ─────────────────────────────────────────────────────────────────────────────

DATABASE_PATH = "grm_data.db"

_SQLITE = False  # Seria sobrescrito pelo _init_engine abaixo


def _init_engine():
    """Inicializa o engine: TiDB Cloud se disponível, SQLite como fallback."""
    global _SQLITE

    # Verifica se há segredos de TiDB configurados no Streamlit
    try:
        import streamlit as st
        if "connections" in st.secrets and "tidb" in st.secrets["connections"]:
            # Tenta injetar o PyMySQL como driver padrão do mysql
            try:
                import pymysql
                pymysql.install_as_MySQLdb()
            except ImportError:
                pass
                
            # Força o uso do PyMySQL explicitamente
            conn = st.connection("tidb", type="sql")
            return conn, False
    except Exception as e:
        # Se houver segredos mas a conexão falhar, reportamos o erro no log
        print(f"Erro ao conectar ao TiDB Cloud: {e}")
        pass

    # Fallback: SQLite local (para desenvolvimento)
    import sqlite3
    _SQLITE = True

    class SQLiteEngine:
        def __init__(self, path):
            self.path = path

        def _conn(self):
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            return conn

        def query(self, sql, ttl=0, params=None):
            import pandas as pd
            conn = self._conn()
            df = pd.read_sql_query(sql, conn, params=params)
            conn.close()
            return df

        def run(self, sql, params=None):
            conn = self._conn()
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.executescript(sql)
            conn.commit()
            conn.close()

        def execute(self, sql, params=None):
            """Executa um INSERT/UPDATE com parâmetros."""
            conn = self._conn()
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            conn.close()

        def session(self):
            """Retorna um contexto de conexão para operações transactionais."""
            return SQLiteSession(self.path)

    class SQLiteSession:
        def __init__(self, path):
            self.path = path
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

        def execute(self, sql, params=None):
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)

    return SQLiteEngine(DATABASE_PATH), True


class _DBManager:
    """Gerenciador de banco de dados com suporte a TiDB Cloud e SQLite."""

    def __init__(self):
        self.engine, self._is_sqlite = _init_engine()
        self._tables_created = False
        self._init_tables()

    def _init_tables(self):
        """Cria as tabelas necessárias no banco de dados."""
        if self._is_sqlite:
            self._init_tables_sqlite()
        else:
            self._init_tables_tidb()
        self._tables_created = True

    def _init_tables_sqlite(self):
        """Cria tabelas no SQLite."""
        with self.engine.session() as session:
            # Tabela de solicitações
            session.execute('''
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
                    criado_em TEXT DEFAULT (datetime('now')),
                    atualizado_em TEXT DEFAULT (datetime('now'))
                )
            ''')

            # Tabela de usuários
            session.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    chave TEXT PRIMARY KEY,
                    rotulo TEXT NOT NULL,
                    senha TEXT NOT NULL,
                    permissoes TEXT NOT NULL
                )
            ''')

            # Inserir usuários padrão se a tabela estiver vazia
            result = session.cursor.execute("SELECT COUNT(*) as count FROM usuarios")
            total = result.fetchone()[0]
            if total == 0:
                session.execute(
                    "INSERT INTO usuarios (chave, rotulo, senha, permissoes) VALUES (?, ?, ?, ?)",
                    ("compras", "Compras", "Grm@2026", "atendimento,compras")
                )
                session.execute(
                    "INSERT INTO usuarios (chave, rotulo, senha, permissoes) VALUES (?, ?, ?, ?)",
                    ("almoxarifado", "Almoxarifado", "Grm@2026", "almoxarifado")
                )

    def _init_tables_tidb(self):
        """Cria tabelas no TiDB Cloud."""
        sql = """
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
            estoque TEXT,
            itens TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            chave VARCHAR(64) PRIMARY KEY,
            rotulo VARCHAR(100) NOT NULL,
            senha VARCHAR(255) NOT NULL,
            permissoes VARCHAR(500) NOT NULL
        );

        INSERT IGNORE INTO usuarios (chave, rotulo, senha, permissoes)
        VALUES ('compras', 'Compras', 'Grm@2026', 'atendimento,compras');

        INSERT IGNORE INTO usuarios (chave, rotulo, senha, permissoes)
        VALUES ('almoxarifado', 'Almoxarifado', 'Grm@2026', 'almoxarifado');
        """
        self.engine.run(sql)

    # ─── Solicitações ────────────────────────────────────────────────────────

    def salvar_solicitacao(self, solicitacao: dict[str, Any]) -> None:
        """Salva ou atualiza uma solicitação no banco."""
        if self._is_sqlite:
            self._salvar_sqlite(solicitacao)
        else:
            self._salvar_tidb(solicitacao)

    def _salvar_sqlite(self, solicitacao: dict[str, Any]) -> None:
        """Salva no SQLite."""
        criado_em = solicitacao.get("criado_em")
        atualizado_em = solicitacao.get("atualizado_em")

        if isinstance(criado_em, datetime):
            criado_em = criado_em.isoformat()
        if isinstance(atualizado_em, datetime):
            atualizado_em = atualizado_em.isoformat()

        with self.engine.session() as session:
            session.execute('''
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
                criado_em,
                atualizado_em,
            ))

    def _salvar_tidb(self, solicitacao: dict[str, Any]) -> None:
        """Salva no TiDB Cloud via INSERT ... ON DUPLICATE KEY UPDATE."""
        criado_em = solicitacao.get("criado_em")
        atualizado_em = solicitacao.get("atualizado_em")

        if isinstance(criado_em, datetime):
            criado_em = criado_em.isoformat()
        if isinstance(atualizado_em, datetime):
            atualizado_em = atualizado_em.isoformat()

        with self.engine.session() as session:
            session.execute('''
                INSERT INTO solicitacoes (
                    protocolo, empresa, solicitante, setor, prioridade, status,
                    destino, triado_por, observacao_triagem, observacao_almoxarifado,
                    dados_compra, estoque, itens, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    empresa=VALUES(empresa), solicitante=VALUES(solicitante),
                    setor=VALUES(setor), prioridade=VALUES(prioridade),
                    status=VALUES(status), destino=VALUES(destino),
                    triado_por=VALUES(triado_por),
                    observacao_triagem=VALUES(observacao_triagem),
                    observacao_almoxarifado=VALUES(observacao_almoxarifado),
                    dados_compra=VALUES(dados_compra),
                    estoque=VALUES(estoque), itens=VALUES(itens),
                    atualizado_em=VALUES(atualizado_em)
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
                criado_em,
                atualizado_em,
            ))

    def carregar_todas(self) -> list[dict[str, Any]]:
        """Carrega todas as solicitações do banco."""
        if self._is_sqlite:
            return self._carregar_todas_sqlite()
        else:
            return self._carregar_todas_tidb()

    def _carregar_todas_sqlite(self) -> list[dict[str, Any]]:
        """Carrega do SQLite."""
        import pandas as pd
        df = self.engine.query("SELECT * FROM solicitacoes ORDER BY criado_em DESC")
        return [self._parse_row_sqlite(row) for _, row in df.iterrows()]

    def _carregar_todas_tidb(self) -> list[dict[str, Any]]:
        """Carrega do TiDB Cloud."""
        df = self.engine.query("SELECT * FROM solicitacoes ORDER BY criado_em DESC", ttl=60)
        return [self._parse_row_mysql(row) for _, row in df.iterrows()]

    def carregar_por_protocolo(self, protocolo: str) -> dict[str, Any] | None:
        """Carrega uma solicitação pelo protocolo."""
        if self._is_sqlite:
            return self._carregar_por_protocolo_sqlite(protocolo)
        else:
            return self._carregar_por_protocolo_tidb(protocolo)

    def _carregar_por_protocolo_sqlite(self, protocolo: str) -> dict[str, Any] | None:
        """Carrega do SQLite."""
        import pandas as pd
        df = self.engine.query(
            "SELECT * FROM solicitacoes WHERE protocolo = ?", params=(protocolo,)
        )
        if df.empty:
            return None
        return self._parse_row_sqlite(df.iloc[0])

    def _carregar_por_protocolo_tidb(self, protocolo: str) -> dict[str, Any] | None:
        """Carrega do TiDB Cloud."""
        import pandas as pd
        df = self.engine.query(
            "SELECT * FROM solicitacoes WHERE protocolo = %s",
            params=(protocolo,),
            ttl=0,
        )
        if df.empty:
            return None
        return self._parse_row_mysql(df.iloc[0])

    def _parse_row_sqlite(self, row) -> dict[str, Any]:
        """Parseia uma linha do SQLite para dict."""
        solicitacao = dict(row)
        solicitacao['itens'] = json.loads(solicitacao['itens'])
        solicitacao['dados_compra'] = json.loads(solicitacao['dados_compra']) if solicitacao['dados_compra'] else {}
        solicitacao['estoque'] = json.loads(solicitacao['estoque']) if solicitacao['estoque'] else []
        try:
            solicitacao['criado_em'] = datetime.fromisoformat(solicitacao['criado_em'])
        except (TypeError, ValueError):
            solicitacao['criado_em'] = datetime.now()
        try:
            solicitacao['atualizado_em'] = datetime.fromisoformat(solicitacao['atualizado_em'])
        except (TypeError, ValueError):
            solicitacao['atualizado_em'] = datetime.now()
        return solicitacao

    def _parse_row_mysql(self, row) -> dict[str, Any]:
        """Parseia uma linha do MySQL/TiDB para dict."""
        solicitacao = dict(row)
        solicitacao['itens'] = json.loads(solicitacao['itens'])
        solicitacao['dados_compra'] = json.loads(solicitacao['dados_compra']) if solicitacao['dados_compra'] else {}
        solicitacao['estoque'] = json.loads(solicitacao['estoque']) if solicitacao['estoque'] else []
        try:
            solicitacao['criado_em'] = solicitacao['criado_em'].to_pydatetime() if hasattr(solicitacao['criado_em'], 'to_pydatetime') else datetime.strptime(str(solicitacao['criado_em']), '%Y-%m-%d %H:%M:%S')
        except Exception:
            solicitacao['criado_em'] = datetime.now()
        try:
            solicitacao['atualizado_em'] = solicitacao['atualizado_em'].to_pydatetime() if hasattr(solicitacao['atualizado_em'], 'to_pydatetime') else datetime.strptime(str(solicitacao['atualizado_em']), '%Y-%m-%d %H:%M:%S')
        except Exception:
            solicitacao['atualizado_em'] = datetime.now()
        return solicitacao

    def obter_sequencia_protocolo(self) -> int:
        """Retorna o próximo número de sequência para o protocolo de hoje."""
        hoje = datetime.now().strftime("%Y%m%d")
        padrao = f"GRM-{hoje}-%"

        if self._is_sqlite:
            df = self.engine.query(
                "SELECT COUNT(*) as count FROM solicitacoes WHERE protocolo LIKE ?",
                params=(padrao,),
            )
        else:
            df = self.engine.query(
                "SELECT COUNT(*) as count FROM solicitacoes WHERE protocolo LIKE %s",
                params=(padrao,),
                ttl=0,
            )
        return int(df.iloc[0]['count']) + 1

    # ─── Usuários ─────────────────────────────────────────────────────────────

    def obter_usuario(self, chave: str) -> dict[str, Any] | None:
        """Retorna os dados de um usuário pela chave."""
        if self._is_sqlite:
            import pandas as pd
            df = self.engine.query(
                "SELECT * FROM usuarios WHERE chave = ?", params=(chave,)
            )
        else:
            import pandas as pd
            df = self.engine.query(
                "SELECT * FROM usuarios WHERE chave = %s",
                params=(chave,),
                ttl=0,
            )
        if df.empty:
            return None
        return dict(df.iloc[0])

    def obter_senha_usuario(self, chave: str) -> str | None:
        """Retorna a senha de um usuário pela chave."""
        usuario = self.obter_usuario(chave)
        if usuario:
            return usuario["senha"]
        return None

    def obter_permissoes_usuario(self, chave: str) -> list[str]:
        """Retorna a lista de permissões de um usuário."""
        usuario = self.obter_usuario(chave)
        if usuario:
            return usuario["permissoes"].split(",")
        return []


# Instância global do gerenciador de banco de dados
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
