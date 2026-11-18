"""PROPOSITO: comprobar el comportamiento del codigo del Sprint 2 con entradas conocidas.
Recibe: el ejecutor unittest y los archivos fuente del proyecto.
Devuelve: resultados de prueba; un fallo se registra mediante las aserciones de unittest.
Se usan datos en memoria y dobles de prueba; este archivo no modifica los historicos."""
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
        """Comprueba envio solo por boton, conservacion sin repetir y ocultamiento tras cambiar consulta.
        Recibe: self, instancia creada por unittest con su contexto de prueba.
        Devuelve: None si las aserciones pasan; unittest informa el fallo si alguna no se cumple."""
        # APP MINIMA: dibujar solo la pantalla que se desea verificar, con filtros conocidos.
        codigo = '''from datetime import datetime
from secciones.consultas import mostrar
mostrar({"desde":datetime(2026,7,1),"hasta":datetime(2026,8,1),
         "distritos":["Centro"],"tipos":["meteorologico"]})'''
        # DOBLE DE PRUEBA: sustituir la consulta real para no lanzar Docker ni consultar bases durante el test.
        backend = Mock(return_value=(pd.DataFrame([["A", 2]], columns=["id_sensor", "cantidad"]),
                                    {"origen": "Hadoop de prueba"}))
        # Mantener el parche durante todos los reruns de AppTest para observar cada llamada al motor.
        with patch.object(consultas, "ejecutar_consulta", backend):
            app = AppTest.from_string(codigo, default_timeout=30).run()
            app.selectbox(key="consulta_motor").select("Hadoop").run()
            backend.assert_not_called()
            # Pulsar Ejecutar debe llamar exactamente una vez al adaptador y mostrar su tabla.
            app.button(key="ejecutar_consulta").click().run()
            backend.assert_called_once()
            self.assertEqual(len(app.dataframe), 1)
            # Un rerun sin pulsar el boton conserva la respuesta sin repetir el procesamiento.
            app.run()
            backend.assert_called_once()
            # Al cambiar de pregunta se oculta la tabla anterior y no se envia otra consulta.
            app.selectbox(key="consulta_id_Hadoop").select_index(4).run()
            backend.assert_called_once()
            self.assertEqual(len(app.dataframe), 0)
            self.assertFalse(app.exception)


# Permitir ejecutar las pruebas directamente o descubrirlas mediante python -m unittest.
if __name__ == "__main__":
    unittest.main()
