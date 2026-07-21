"""Teste de carregamento dos componentes da interface Streamlit."""

from __future__ import annotations

import pathlib
import unittest

from streamlit.testing.v1 import AppTest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class InterfaceStreamlitTest(unittest.TestCase):
    """Confirma que a primeira tela carrega sem exceções e oferece o fluxo previsto."""

    def test_tela_inicial_exibe_componentes_essenciais(self) -> None:
        aplicacao = AppTest.from_file(str(ROOT / "almox_app.py"))
        aplicacao.run(timeout=10)

        self.assertEqual(len(aplicacao.exception), 0)
        self.assertEqual(len(aplicacao.tabs), 0)
        labels = [botao.label for botao in aplicacao.button]
        self.assertIn("👤  SOLICITANTE", labels)
        self.assertIn("🔐  ATENDENTE", labels)
        self.assertEqual(len(labels), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
