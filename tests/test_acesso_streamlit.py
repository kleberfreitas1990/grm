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

    def test_atendente_ve_tela_de_login(self) -> None:
        """Clicar em ATENDENTE deve exibir o formulário de login antes do painel."""
        aplicacao = self._abrir_aplicacao()
        # Botão ATENDENTE é o segundo botão (índice 1)
        aplicacao.button[1].click().run(timeout=10)
        self.assertEqual(len(aplicacao.exception), 0)
        # Deve exibir seletor de perfil e campo de senha — sem abas ainda
        self.assertEqual(len(aplicacao.tabs), 0)
        campos_senha = [campo for campo in aplicacao.text_input if campo.label == "Senha"]
        self.assertEqual(len(campos_senha), 1)

    def test_compras_acessa_atendimento_e_compras(self) -> None:
        with patch.dict(os.environ, {"GRM_COMPRAS_PASSWORD": "Grm@2026"}, clear=False):
            aplicacao = self._abrir_aplicacao()
            # Clica em ATENDENTE
            aplicacao.button[1].click().run(timeout=10)
            self.assertEqual(len(aplicacao.exception), 0)
            # Seleciona perfil Compras e digita senha
            aplicacao.selectbox[0].set_value("Compras")
            aplicacao.text_input[0].set_value("Grm@2026")
            aplicacao.button[0].click().run(timeout=10)
            self.assertEqual(len(aplicacao.exception), 0)
            self.assertEqual(len(aplicacao.tabs), 0)
            subcabecalhos = [elemento.value for elemento in aplicacao.subheader]
            self.assertIn("Painel de compras", subcabecalhos)

    def test_almoxarifado_acessa_somente_estoque(self) -> None:
        with patch.dict(os.environ, {"GRM_ALMOXARIFADO_PASSWORD": "Grm@2026"}, clear=False):
            aplicacao = self._abrir_aplicacao()
            # Clica em ATENDENTE
            aplicacao.button[1].click().run(timeout=10)
            self.assertEqual(len(aplicacao.exception), 0)
            # Seleciona perfil Almoxarifado e digita senha
            aplicacao.selectbox[0].set_value("Almoxarifado")
            aplicacao.text_input[0].set_value("Grm@2026")
            aplicacao.button[0].click().run(timeout=10)
            self.assertEqual(len(aplicacao.exception), 0)
            self.assertEqual(len(aplicacao.tabs), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
