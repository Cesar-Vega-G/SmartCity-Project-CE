"""Puente a las consultas de Luis. No sustituye su implementacion analitica.

Contrato: spark/consultas.py exporta ejecutar_consulta(spark, consulta, filtros)
y devuelve un pyspark.sql.DataFrame. consulta: entero 1..10; fechas ISO, fin exclusivo.
"""
import argparse
import base64
import importlib
import json

from comun_spark import crear_spark


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("consulta", type=int, choices=range(1, 11))
    p.add_argument("--filtros", required=True)
    a = p.parse_args()
    consultas = importlib.import_module("consultas")
    funcion = getattr(consultas, "ejecutar_consulta", None)
    if not callable(funcion):
        raise RuntimeError("Luis debe exportar ejecutar_consulta(spark, consulta, filtros) en spark/consultas.py")
    filtros = json.loads(base64.urlsafe_b64decode(a.filtros).decode("utf-8"))
    spark = crear_spark("consulta_dashboard_{}".format(a.consulta))
    try:
        tabla = funcion(spark, a.consulta, filtros)
        filas = tabla.limit(1001).collect()
        resultado = {"columnas": tabla.columns, "filas": [list(r) for r in filas[:1000]],
                     "vista_limitada": len(filas) > 1000, "consulta": a.consulta, "filtros": filtros}
        print("RESULTADO " + json.dumps(resultado, default=str, ensure_ascii=True, allow_nan=False))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
