"""PROPOSITO: puente entre el dashboard y las consultas Spark de Luis.
Recibe: ID 1..10 y filtros JSON codificados en Base64 desde spark-submit.
Devuelve: una linea RESULTADO con columnas, filas y metadatos; main retorna None.
DEPENDENCIA: spark/consultas.py debe exportar ejecutar_consulta(spark, consulta, filtros).
La funcion de Luis devuelve un DataFrame Spark; este puente lo adapta para la pantalla."""
import argparse
import base64
import importlib
import json

from comun_spark import crear_spark


def main():
    """Ejecutar una consulta Spark y serializar su resultado para Streamlit.
    Recibe: argumentos CLI, modulo de consultas de Luis y configuracion de comun_spark.
    Devuelve: None; imprime RESULTADO con hasta 1.000 filas del resultado final.
    La sesion Spark se cierra en finally tanto si la consulta termina como si falla."""
    # ETAPA 1: leer el ID y reconstruir los filtros enviados desde el dashboard.
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("consulta", type=int, choices=range(1, 11))
    p.add_argument("--filtros", required=True)
    a = p.parse_args()
    # ETAPA 2: verificar el contrato del modulo de Luis antes de crear la sesion Spark.
    consultas = importlib.import_module("consultas")
    funcion = getattr(consultas, "ejecutar_consulta", None)
    if not callable(funcion):
        raise RuntimeError("Luis debe exportar ejecutar_consulta(spark, consulta, filtros) en spark/consultas.py")
    filtros = json.loads(base64.urlsafe_b64decode(a.filtros).decode("utf-8"))
    # ETAPA 3: utilizar la misma configuracion Spark del resto del proyecto.
    spark = crear_spark("consulta_dashboard_{}".format(a.consulta))
    try:
        # El analisis pertenece a Luis; el puente solo llama a su funcion y recibe el DataFrame.
        tabla = funcion(spark, a.consulta, filtros)
        # ETAPA 4: pedir 1.001 filas permite detectar truncamiento; se muestran 1.000 despues del analisis.
        filas = tabla.limit(1001).collect()
        resultado = {"columnas": tabla.columns, "filas": [list(r) for r in filas[:1000]],
                     "vista_limitada": len(filas) > 1000, "consulta": a.consulta, "filtros": filtros}
        # El prefijo permite distinguir la respuesta JSON de los logs normales de spark-submit.
        print("RESULTADO " + json.dumps(resultado, default=str, ensure_ascii=True, allow_nan=False))
    # LIBERACION: cerrar la sesion incluso si falla el procesamiento o la serializacion.
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
