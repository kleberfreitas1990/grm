"""Testes de fumaça para as regras centrais da aplicação GRM."""

from __future__ import annotations

import importlib.util
import pathlib
import os
import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("almox_app", ROOT / "almox_app.py")
assert SPEC is not None and SPEC.loader is not None
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class RegrasDaAplicacaoTest(unittest.TestCase):
    """Valida as regras puras de dados e de status da primeira versão."""

    def test_normalizar_itens_remove_linhas_incompletas(self) -> None:
        dados = pd.DataFrame(
            [
                {"Produto": "  Luva de proteção ", "Quantidade": "4"},
                {"Produto": "", "Quantidade": 3},
                {"Produto": "Item sem quantidade", "Quantidade": 0},
            ]
        )

        itens = APP.normalizar_itens(dados)

        self.assertEqual(itens, [{"Produto": "Luva de proteção", "Quantidade": 4}])

    def test_status_atualiza_data_de_movimentacao(self) -> None:
        solicitacao = {"status": "Aguardando triagem", "atualizado_em": datetime(2020, 1, 1)}

        with patch.object(APP.db, "salvar_solicitacao") as salvar_solicitacao:
            APP.atualizar_status(solicitacao, "Em processo de compra")

        salvar_solicitacao.assert_called_once_with(solicitacao)
        self.assertEqual(solicitacao["status"], "Em processo de compra")
        self.assertGreater(solicitacao["atualizado_em"], datetime(2020, 1, 1))
        self.assertEqual(solicitacao["historico_status"][0]["status"], "Em processo de compra")
        self.assertEqual(solicitacao["historico_status"][0]["responsavel"], "Sistema")

    def test_status_previstos_possuem_metadados(self) -> None:
        status_esperados = {
            "Aguardando triagem",
            "Em análise no almoxarifado",
            "Em processo de compra",
            "Atendido pelo almoxarifado",
            "Compra solicitada",
        }

        self.assertTrue(status_esperados.issubset(APP.STATUS_META))

    def test_novos_status_do_fluxo_possuem_metadados_e_categorias(self) -> None:
        status_logisticos = {
            "Em processo de autorização": "Compras",
            "Aguardando recebimento no almoxarifado": "Recebimento",
            "Aguardando envio ao solicitante": "Envio",
            "Produto enviado ao solicitante": "Concluído",
        }
        self.assertTrue(set(status_logisticos).issubset(APP.STATUS_META))
        for status, categoria in status_logisticos.items():
            self.assertEqual(APP._categoria_status(status), categoria)
        self.assertIn("Produto enviado ao solicitante", APP.STATUS_CONCLUIDOS)

    def test_atualizacao_logistica_preserva_responsavel_e_observacao(self) -> None:
        solicitacao = {"status": "Aguardando envio ao solicitante", "atualizado_em": datetime(2020, 1, 1)}
        with patch.object(APP.db, "salvar_solicitacao"):
            APP.atualizar_status(
                solicitacao,
                "Produto enviado ao solicitante",
                "João do Almoxarifado",
                "Entrega interna registrada.",
            )
        movimento = solicitacao["historico_status"][0]
        self.assertEqual(movimento["status"], "Produto enviado ao solicitante")
        self.assertEqual(movimento["responsavel"], "João do Almoxarifado")
        self.assertEqual(movimento["observacao"], "Entrega interna registrada.")

    def test_usuarios_setoriais_possuem_permissoes_separadas(self) -> None:
        self.assertEqual(set(APP.USUARIOS_CONFIGURADOS), {"compras", "almoxarifado"})
        self.assertTrue(APP.usuario_tem_permissao("compras", "atendimento"))
        self.assertTrue(APP.usuario_tem_permissao("compras", "compras"))
        self.assertFalse(APP.usuario_tem_permissao("compras", "almoxarifado"))
        self.assertTrue(APP.usuario_tem_permissao("almoxarifado", "almoxarifado"))
        self.assertFalse(APP.usuario_tem_permissao("almoxarifado", "compras"))

    def test_senha_de_compras_e_lida_do_banco(self) -> None:
        self.assertEqual(APP.obter_senha_configurada("compras"), "Grm@2026")
        self.assertEqual(APP.obter_senha_configurada("almoxarifado"), "Grm@2026")


if __name__ == "__main__":
    unittest.main(verbosity=2)
