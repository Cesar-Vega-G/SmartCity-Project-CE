import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dashboard.consultas_motores import pipeline_mongo, sql_postgres, ejecutar_spark


class AdaptadoresTest(unittest.TestCase):
    def setUp(self):
        self.f = {"desde": datetime(2026, 7, 1), "hasta": datetime(2026, 8, 1),
                  "distritos": ["Centro"], "tipos": ["trafico"], "id_sensor": "S-00002"}

    def test_diez_sql_de_lectura_sin_procedimientos(self):
        for n in range(1, 11):
            sql, _ = sql_postgres(n, self.f)
            self.assertTrue(sql.upper().startswith(("SELECT", "WITH")))
            self.assertNotIn("CALL ", sql.upper())
        self.assertIn("mv_ranking_zonas", sql_postgres(9, self.f)[0])

    def test_funcion_parametrizada(self):
        sql, params = sql_postgres(10, self.f)
        self.assertEqual(sql.count("%s"), 3)
        self.assertEqual(params, ("S-00002", self.f["desde"], self.f["hasta"]))

    def test_diez_pipelines_y_colecciones(self):
        for n in range(1, 11):
            coleccion, p = pipeline_mongo(n, self.f)
            campo = "fecha_reporte" if n == 8 else "timestamp"
            self.assertEqual(p[0]["$match"][campo]["$lt"], self.f["hasta"])
            self.assertEqual(p[0]["$match"]["ubicacion.distrito"], {"$in": ["Centro"]})
            self.assertEqual(coleccion, {4: "eventos", 5: "alertas", 8: "incidentes"}.get(n, "lecturas"))
            self.assertFalse(any("$out" in etapa or "$merge" in etapa for etapa in p))

    def test_tipo_no_se_aplica_a_eventos(self):
        for n in [4, 5, 8]:
            self.assertNotIn("tipo", pipeline_mongo(n, self.f)[1][0]["$match"])

    def test_filtro_multiple_no_amplia_trafico(self):
        self.f["tipos"] = ["meteorologico"]
        match = pipeline_mongo(10, self.f)[1][0]["$match"]
        self.assertEqual(match["tipo"], {"$in": []})

    def test_spark_ausente_no_inventa_resultados_ni_lanza_docker(self):
        with patch("pathlib.Path.exists", return_value=False), patch("subprocess.run") as mock:
            with self.assertRaisesRegex(RuntimeError, "Pendiente de Luis"):
                ejecutar_spark(1, self.f)
            mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
