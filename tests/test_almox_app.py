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

    def test_status_previstos_possuem_metadados(self) -> None:
        status_esperados = {
            "Aguardando triagem",
            "Em análise no almoxarifado",
            "Em processo de compra",
            "Atendido pelo almoxarifado",
            "Compra solicitada",
        }

        self.assertTrue(status_esperados.issubset(APP.STATUS_META))

    def test_usuarios_setoriais_possuem_permissoes_separadas(self) -> None:
        self.assertEqual(set(APP.USUARIOS_CONFIGURADOS), {"suprimentos", "almoxarifado"})
        self.assertTrue(APP.usuario_tem_permissao("suprimentos", "atendimento"))
        self.assertTrue(APP.usuario_tem_permissao("suprimentos", "compras"))
        self.assertFalse(APP.usuario_tem_permissao("suprimentos", "almoxarifado"))
        self.assertTrue(APP.usuario_tem_permissao("almoxarifado", "almoxarifado"))
        self.assertFalse(APP.usuario_tem_permissao("almoxarifado", "compras"))

    def test_senha_de_suprimentos_e_lida_da_variavel_de_ambiente(self) -> None:
        with patch.dict(os.environ, {"GRM_SUPRIMENTOS_PASSWORD": "senha-de-teste"}, clear=False):
            self.assertEqual(APP.obter_senha_configurada("suprimentos"), "senha-de-teste")


if __name__ == "__main__":
    unittest.main(verbosity=2)
