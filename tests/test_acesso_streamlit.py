"""Testes de acesso setorial na interface Streamlit."""

from __future__ import annotations

import os
import pathlib
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class AcessoSetorialStreamlitTest(unittest.TestCase):
    """Confirma que cada usuário autentica e enxerga somente sua área."""

    def _abrir_aplicacao(self) -> AppTest:
        aplicacao = AppTest.from_file(str(ROOT / "almox_app.py"))
        aplicacao.run(timeout=10)
        self.assertEqual(len(aplicacao.exception), 0)
        return aplicacao

    def test_suprimentos_acessa_atendimento_e_compras(self) -> None:
        with patch.dict(os.environ, {"GRM_SUPRIMENTOS_PASSWORD": "senha-suprimentos"}, clear=False):
            aplicacao = self._abrir_aplicacao()
            aplicacao.button[1].click().run(timeout=10)
            self.assertEqual(len(aplicacao.exception), 0)
            self.assertEqual([campo.label for campo in aplicacao.text_input], ["Usuário", "Senha"])

            aplicacao.text_input[1].set_value("senha-suprimentos")
            aplicacao.button[0].click().run(timeout=10)

            self.assertEqual(len(aplicacao.exception), 0)
            self.assertEqual([aba.label for aba in aplicacao.tabs], ["Atendimento", "Compras"])

    def test_almoxarifado_acessa_somente_estoque(self) -> None:
        with patch.dict(os.environ, {"GRM_ALMOXARIFADO_PASSWORD": "senha-almoxarifado"}, clear=False):
            aplicacao = self._abrir_aplicacao()
            aplicacao.button[2].click().run(timeout=10)
            self.assertEqual(len(aplicacao.exception), 0)
            self.assertEqual([campo.label for campo in aplicacao.text_input], ["Usuário", "Senha"])

            aplicacao.text_input[1].set_value("senha-almoxarifado")
            aplicacao.button[0].click().run(timeout=10)

            self.assertEqual(len(aplicacao.exception), 0)
            self.assertEqual(len(aplicacao.tabs), 0)
            self.assertTrue(any("Painel do almoxarifado" in titulo.value for titulo in aplicacao.subheader))


if __name__ == "__main__":
    unittest.main(verbosity=2)
