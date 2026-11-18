"""Adaptadores de las consultas existentes. Las agregaciones no escriben datos."""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
from bson import json_util


RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PG_NOMBRES = ["Sensores por tipo", "Sensores por ubicacion", "Sensores activos e inactivos",
              "Sensores por organismo", "Ubicaciones con mas sensores", "Instalaciones por anio",
              "Sensores sin actividad historica", "Ranking de zonas monitoreadas",
              "Ranking mediante vista materializada", "Resumen mediante funcion"]
MONGO_NOMBRES = ["Lecturas de un sensor", "Lecturas por fechas", "Maximos y minimos",
                 "Eventos criticos", "Alertas por zona", "Promedios por zona",
                 "Promedios por tipo", "Incidentes por categoria", "Cantidad por sensor",
                 "Filtros multiples de trafico"]
SPARK_NOMBRES = ["Sensores que generan mas informacion", "Distribucion geografica de eventos",
                 "Evolucion temporal de indicadores", "Correlacion entre variables",
                 "Ranking de zonas con mas actividad", "Tendencias por periodo",
                 "Deteccion de anomalias", "Agrupamiento por categorias",
                 "Comparacion historica entre anios", "Reporte consolidado"]
COLECCIONES = {4: "eventos", 5: "alertas", 8: "incidentes"}


def sql_postgres(consulta, f):
    if not 1 <= consulta <= 10:
        raise ValueError("Consulta PostgreSQL desconocida")
    carpeta = "postgres/consultas" if consulta <= 8 else "postgres/vistas_funciones"
    archivos = sorted((RAIZ / carpeta).glob("{:02d}_*.sql".format(consulta)))
    if len(archivos) != 1:
        raise RuntimeError("No se encontro un unico archivo para la consulta PostgreSQL")
    # Solo SELECT inicial: 9a y 10a. Nunca ejecutar los procedimientos del archivo 10.
    sql = re.sub(r"--[^\n]*", "", archivos[0].read_text(encoding="utf-8-sig")).split(";", 1)[0].strip()
    if not sql.upper().startswith(("SELECT", "WITH")):
        raise ValueError("El catalogo solo admite consultas de lectura")
    params = None
    if consulta == 10:
        sql = "SELECT * FROM fn_resumen_sensor(%s, %s, %s)"
        params = (f.get("id_sensor", "S-00002"), f["desde"], f["hasta"])
    return sql, params


def pipeline_mongo(consulta, f):
    if not 1 <= consulta <= 10:
        raise ValueError("Consulta MongoDB desconocida")
    archivos = sorted((RAIZ / "mongo/consultas/compass").glob("{:02d}_*.pipeline.js".format(consulta)))
    if len(archivos) != 1:
        raise RuntimeError("No se encontro el pipeline MongoDB")
    texto = re.sub(r"(?m)^\s*//[^\n]*", "", archivos[0].read_text(encoding="utf-8-sig"))
    texto = re.sub(r'ISODate\(("[^"]+")\)', r'{"$date":\1}', texto)
    pipeline = json_util.loads(texto)
    campo_fecha = "fecha_reporte" if consulta == 8 else "timestamp"
    match = pipeline[0]["$match"]
    match[campo_fecha] = {"$gte": f["desde"], "$lt": f["hasta"]}
    if f.get("distritos"):
        match["ubicacion.distrito"] = {"$in": f["distritos"]}
    if consulta not in (4, 5, 8) and f.get("tipos"):
        match["tipo"] = "trafico" if consulta == 10 else {"$in": f["tipos"]}
        if consulta == 10 and "trafico" not in f["tipos"]:
            match["tipo"] = {"$in": []}
    if consulta == 1:
        match["id_sensor"] = f.get("id_sensor", "S-00001")
    return COLECCIONES.get(consulta, "lecturas"), pipeline


def ejecutar_spark(consulta, f):
    if not (RAIZ / "spark/consultas.py").exists():
        raise RuntimeError("Pendiente de Luis: agregar spark/consultas.py con ejecutar_consulta(spark, consulta, filtros). "
                           "El catalogo y la conexion del dashboard ya estan preparados.")
    texto = json.dumps(f, default=lambda v: v.isoformat(), ensure_ascii=True)
    token = base64.urlsafe_b64encode(texto.encode("utf-8")).decode("ascii")
    r = subprocess.run(["docker", "exec", "smartcity_spark_master", "/opt/spark/bin/spark-submit",
                        "/proyecto/spark/consultas_dashboard.py", str(consulta), "--filtros", token],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    if r.returncode:
        raise RuntimeError("Spark no pudo ejecutar la consulta:\n" + (r.stderr or r.stdout)[-4000:])
    lineas = [l[len("RESULTADO "):] for l in r.stdout.splitlines() if l.startswith("RESULTADO ")]
    if len(lineas) != 1:
        raise RuntimeError("Spark no devolvio una tabla RESULTADO valida")
    resultado = json.loads(lineas[0])
    return pd.DataFrame(resultado["filas"], columns=resultado["columnas"]), resultado


def ejecutar_consulta(tecnologia, consulta, filtros):
    from conexiones import mongo, pg_df
    if tecnologia == "PostgreSQL":
        sql, params = sql_postgres(consulta, filtros)
        return pg_df(sql, params), {"origen": "PostgreSQL", "parametros": params or "Catalogo completo / snapshot historico"}
    if tecnologia == "MongoDB":
        coleccion, pipeline = pipeline_mongo(consulta, filtros)
        documentos = list(mongo()[coleccion].aggregate(pipeline, allowDiskUse=True, maxTimeMS=300000))
        documentos = json.loads(json_util.dumps(documentos))
        return pd.json_normalize(documentos), {"origen": "MongoDB", "coleccion": coleccion,
                                               "filtros": json.loads(json_util.dumps(pipeline[0]["$match"]))}
    if tecnologia == "Hadoop":
        from hadoop.ejecutar_mapreduce import ejecutar
        resultado = ejecutar(consulta, filtros)
        return pd.DataFrame(resultado["filas"], columns=resultado["columnas"]), dict(resultado, origen="HDFS / Hadoop MapReduce")
    if tecnologia == "Spark":
        tabla, resultado = ejecutar_spark(consulta, filtros)
        return tabla, dict(resultado, origen="Spark SQL / DataFrames")
    raise ValueError("Tecnologia desconocida")
