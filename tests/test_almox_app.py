"""Testes de fumaça para as regras centrais da aplicação GRM."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest
from datetime import datetime

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

        APP.atualizar_status(solicitacao, "Em processo de compra")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
