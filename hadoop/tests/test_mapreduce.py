import ast
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hadoop.mapreduce import (fecha, filtros_validos, mapear, mapear_maximo, reducir,
                              reducir_maximo, valor_valido)
from hadoop.ejecutar_mapreduce import ejecutar


def lectura(sensor, valor, ts="2026-07-01T00:00:00Z", **extra):
    d = {"id_sensor": sensor, "tipo": "meteorologico", "ubicacion": {"distrito": "Centro"},
         "timestamp": {"$date": ts}, "medicion": {"temperatura": valor}, "valido": True}
    d.update(extra)
    return d


def consulta(n, documentos, filtros=None):
    entrada = io.StringIO("\n".join(json.dumps(d) for d in documentos))
    intermedio, salida = io.StringIO(), io.StringIO()
    mapear(n, filtros or {}, entrada, intermedio)
    reducir(n, sorted(intermedio.getvalue().splitlines(True)), salida)
    if n == 2:
        segundo, maximos = io.StringIO(), io.StringIO()
        mapear_maximo(io.StringIO(salida.getvalue()), segundo)
        reducir_maximo(sorted(segundo.getvalue().splitlines(True)), maximos)
        salida = maximos
    return [json.loads(l) for l in salida.getvalue().splitlines()]


class MapReduceTest(unittest.TestCase):
    def setUp(self):
        self.docs = [lectura("A", 10), lectura("A", 20),
                     lectura("B", 30, invalidos=["humedad"], valido=False),
                     lectura("B", 40, invalidos=["temperatura"], valido=False),
                     lectura("C", 100, valido=False)]
        self.filtros = {"desde": "2026-07-01", "hasta": "2026-08-01", "variable": "temperatura"}

    def test_cuenta_documentos_incluso_invalidos(self):
        self.assertEqual(consulta(1, self.docs), [["A", 2], ["B", 2], ["C", 1]])

    def test_maximo_global_con_empates(self):
        self.assertEqual(consulta(2, self.docs), [["A", 2], ["B", 2]])

    def test_promedio_historico_solo_variables_sanas(self):
        self.assertEqual(consulta(3, self.docs, {"distritos": ["Otra"]}),
                         [["temperatura", "C", 3, 20.0, 10, 30]])

    def test_eventos_separados_de_lecturas(self):
        eventos = [{"ubicacion": {"distrito": z}, "timestamp": {"$date": "2026-07-10T00:00:00Z"}}
                   for z in ["Centro", "Centro", "Retiro"]]
        self.assertEqual(consulta(4, eventos, self.filtros), [["Centro", 2], ["Retiro", 1]])

    def test_temporal_limites_y_faltantes(self):
        docs = self.docs + [lectura("A", 99, "2026-08-01T00:00:00Z"),
                            lectura("A", 1, "2026-06-30T23:59:59Z"), lectura("A", None)]
        self.assertEqual(consulta(5, docs, self.filtros),
                         [["2026-07-01", "A", "temperatura", "C", 2, 15.0, 10, 20],
                          ["2026-07-01", "B", "temperatura", "C", 1, 30.0, 30, 30]])

    def test_filtros_distrito_tipo_y_sensor(self):
        self.assertEqual(consulta(1, self.docs, {"id_sensor": "B", "distritos": ["Centro"],
                                                "tipos": ["meteorologico"]}), [["B", 2]])
        self.assertEqual(consulta(1, self.docs, {"tipos": ["trafico"]}), [])

    def test_vacios_y_sensor_inexistente(self):
        for n in range(1, 6):
            self.assertEqual(consulta(n, []), [])
        self.assertEqual(consulta(1, self.docs, {"id_sensor": "NO-EXISTE"}), [])

    def test_suma_y_cantidad_no_promedio_de_promedios(self):
        entrada = ['["temperatura","C"]\t[1,10,10,10]\n',
                   '["temperatura","C"]\t[3,90,20,40]\n']
        salida = io.StringIO()
        reducir(3, entrada, salida)
        self.assertEqual(json.loads(salida.getvalue()), ["temperatura", "C", 4, 25.0, 10, 40])

    def test_fechas_extended_json_y_zona(self):
        self.assertEqual(fecha({"$date": {"$numberLong": "0"}}).isoformat(), "1970-01-01T00:00:00+00:00")
        self.assertEqual(fecha("2026-07-01T02:00:00+02:00"), fecha("2026-07-01T00:00:00Z"))
        self.assertEqual(fecha("2026-07-01T00:00:00"), fecha("2026-07-01T00:00:00Z"))

    def test_no_numericos_y_no_finitos(self):
        for valor in [None, "20", True, float("inf"), float("nan")]:
            self.assertIsNone(valor_valido(lectura("A", valor), "temperatura"))

    def test_documento_malformado_contabilizado(self):
        salida, errores = io.StringIO(), io.StringIO()
        with patch("sys.stderr", errores):
            mapear(1, {}, io.StringIO("esto no es JSON\n[]\n"), salida)
        self.assertEqual(salida.getvalue(), "")
        self.assertIn("documentos_malformados,2", errores.getvalue())

    def test_rechaza_intervalo_invalido_y_variable_desconocida(self):
        for f in [{"desde": "2026-07-01"}, {"desde": "2026-07-01", "hasta": "2026-07-01"},
                  {"variable": "inventada"}]:
            with self.assertRaises(ValueError):
                filtros_validos(f)

    def test_runner_temporal_exige_periodo_antes_de_docker(self):
        with patch("hadoop.ejecutar_mapreduce.docker") as mock:
            with self.assertRaises(ValueError):
                ejecutar(5)
            mock.assert_not_called()

    def test_mapper_compila_con_gramatica_python36(self):
        ast.parse((Path(__file__).resolve().parents[1] / "mapreduce.py").read_text(encoding="utf-8"),
                  feature_version=(3, 6))


if __name__ == "__main__":
    unittest.main()
