import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "dashboard")]
from secciones import consultas


class PantallaTest(unittest.TestCase):
    def test_solo_boton_ejecuta_y_cambios_ocultan_resultado(self):
        codigo = '''from datetime import datetime
from secciones.consultas import mostrar
mostrar({"desde":datetime(2026,7,1),"hasta":datetime(2026,8,1),
         "distritos":["Centro"],"tipos":["meteorologico"]})'''
        backend = Mock(return_value=(pd.DataFrame([["A", 2]], columns=["id_sensor", "cantidad"]),
                                    {"origen": "Hadoop de prueba"}))
        with patch.object(consultas, "ejecutar_consulta", backend):
            app = AppTest.from_string(codigo, default_timeout=30).run()
            app.selectbox(key="consulta_motor").select("Hadoop").run()
            backend.assert_not_called()
            app.button(key="ejecutar_consulta").click().run()
            backend.assert_called_once()
            self.assertEqual(len(app.dataframe), 1)
            app.run()
            backend.assert_called_once()
            app.selectbox(key="consulta_id_Hadoop").select_index(4).run()
            backend.assert_called_once()
            self.assertEqual(len(app.dataframe), 0)
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
