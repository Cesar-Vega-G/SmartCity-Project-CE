"""PROPOSITO: adaptar las consultas del proyecto a una salida comun para Streamlit.
Recibe: tecnologia, ID de consulta y filtros procedentes de la pantalla.
Devuelve: una tabla pandas y metadatos que explican origen y parametros efectivos.
REUTILIZACION: los SQL y pipelines existentes siguen siendo la fuente de las consultas.
Las consultas de bases son de lectura; Hadoop/Spark pueden crear sus salidas de procesamiento."""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
from bson import json_util


# RUTAS: resolver los archivos desde el modulo, independientemente de la terminal de inicio.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# CATALOGOS: la posicion 0 corresponde al ID 1; los rotulos siguen las preguntas del enunciado.
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
# Las consultas 4, 5 y 8 usan colecciones propias; las restantes consultan lecturas.
COLECCIONES = {4: "eventos", 5: "alertas", 8: "incidentes"}


def sql_postgres(consulta, f):
    """Preparar el SQL del catalogo que debe ejecutar la conexion PostgreSQL.
    Recibe: ID 1..10 y f, con sensor/periodo para la funcion de la consulta 10.
    Devuelve: tupla (sql, params); params es None o una tupla para los marcadores %s.
    Las consultas 1..8 conservan su SQL; 9 usa la vista 9a y 10 la funcion de resumen."""
    if not 1 <= consulta <= 10:
        raise ValueError("Consulta PostgreSQL desconocida")
    # ETAPA 1: ubicar un unico archivo por ID; vistas y funciones viven en otra carpeta.
    carpeta = "postgres/consultas" if consulta <= 8 else "postgres/vistas_funciones"
    archivos = sorted((RAIZ / carpeta).glob("{:02d}_*.sql".format(consulta)))
    if len(archivos) != 1:
        raise RuntimeError("No se encontro un unico archivo para la consulta PostgreSQL")
    # Solo SELECT inicial: 9a y 10a. Nunca ejecutar los procedimientos del archivo 10.
    # ETAPA 2: quitar comentarios SQL y seleccionar solo la primera sentencia del archivo conocido.
    sql = re.sub(r"--[^\n]*", "", archivos[0].read_text(encoding="utf-8-sig")).split(";", 1)[0].strip()
    if not sql.upper().startswith(("SELECT", "WITH")):
        raise ValueError("El catalogo solo admite consultas de lectura")
    params = None
    # ETAPA 3: pasar sensor y fechas por parametros, separados del texto SQL.
    if consulta == 10:
        sql = "SELECT * FROM fn_resumen_sensor(%s, %s, %s)"
        params = (f.get("id_sensor", "S-00002"), f["desde"], f["hasta"])
    return sql, params


def pipeline_mongo(consulta, f):
    """Adaptar un pipeline de Compass a objetos BSON que entiende PyMongo.
    Recibe: ID 1..10 y f con desde/hasta, distritos, tipos y sensor cuando corresponda.
    Devuelve: tupla (nombre de coleccion, lista de etapas del pipeline).
    Se modifica el filtro inicial de la copia cargada; el archivo fuente queda intacto."""
    if not 1 <= consulta <= 10:
        raise ValueError("Consulta MongoDB desconocida")
    archivos = sorted((RAIZ / "mongo/consultas/compass").glob("{:02d}_*.pipeline.js".format(consulta)))
    if len(archivos) != 1:
        raise RuntimeError("No se encontro el pipeline MongoDB")
    # ETAPA 1 MONGO: retirar comentarios de linea completa y convertir ISODate a Extended JSON.
    texto = re.sub(r"(?m)^\s*//[^\n]*", "", archivos[0].read_text(encoding="utf-8-sig"))
    texto = re.sub(r'ISODate\(("[^"]+")\)', r'{"$date":\1}', texto)
    # json_util reconstruye fechas BSON sin ejecutar JavaScript ni usar eval.
    pipeline = json_util.loads(texto)
    # ETAPA 2 MONGO: incidentes usa fecha_reporte; las otras colecciones usan timestamp.
    campo_fecha = "fecha_reporte" if consulta == 8 else "timestamp"
    match = pipeline[0]["$match"]
    match[campo_fecha] = {"$gte": f["desde"], "$lt": f["hasta"]}
    # La seleccion del dashboard reemplaza el distrito de ejemplo del pipeline.
    if f.get("distritos"):
        match["ubicacion.distrito"] = {"$in": f["distritos"]}
    # El tipo de sensor solo existe en lecturas; conservar el alcance de trafico de la consulta 10.
    if consulta not in (4, 5, 8) and f.get("tipos"):
        match["tipo"] = "trafico" if consulta == 10 else {"$in": f["tipos"]}
        if consulta == 10 and "trafico" not in f["tipos"]:
            match["tipo"] = {"$in": []}
    if consulta == 1:
        match["id_sensor"] = f.get("id_sensor", "S-00001")
    return COLECCIONES.get(consulta, "lecturas"), pipeline


def ejecutar_spark(consulta, f):
    """Solicitar a spark-submit la consulta analitica que proveera Luis.
    Recibe: ID de consulta y filtros con fechas datetime y selecciones del dashboard.
    Devuelve: (DataFrame pandas, diccionario de resultado) si Spark devuelve RESULTADO.
    Lanza un error claro si falta el modulo de Luis o falla el procesamiento."""
    # DEPENDENCIA: el catalogo no implica que las diez consultas Spark ya esten implementadas.
    if not (RAIZ / "spark/consultas.py").exists():
        raise RuntimeError("Pendiente de Luis: agregar spark/consultas.py con ejecutar_consulta(spark, consulta, filtros). "
                           "El catalogo y la conexion del dashboard ya estan preparados.")
    # Serializar fechas y transportar filtros en Base64; el puente de Spark los reconstruye.
    texto = json.dumps(f, default=lambda v: v.isoformat(), ensure_ascii=True)
    token = base64.urlsafe_b64encode(texto.encode("utf-8")).decode("ascii")
    # EJECUCION SPARK: el proceso corre dentro de su contenedor y se espera hasta 30 minutos.
    r = subprocess.run(["docker", "exec", "smartcity_spark_master", "/opt/spark/bin/spark-submit",
                        "/proyecto/spark/consultas_dashboard.py", str(consulta), "--filtros", token],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    if r.returncode:
        raise RuntimeError("Spark no pudo ejecutar la consulta:\n" + (r.stderr or r.stdout)[-4000:])
    # PROTOCOLO: separar la unica linea RESULTADO de los mensajes normales de Spark.
    lineas = [l[len("RESULTADO "):] for l in r.stdout.splitlines() if l.startswith("RESULTADO ")]
    if len(lineas) != 1:
        raise RuntimeError("Spark no devolvio una tabla RESULTADO valida")
    resultado = json.loads(lineas[0])
    return pd.DataFrame(resultado["filas"], columns=resultado["columnas"]), resultado


def ejecutar_consulta(tecnologia, consulta, filtros):
    """Despachar una consulta al motor seleccionado y uniformar su respuesta.
    Recibe: tecnologia, consulta y filtros del usuario.
    Devuelve: (tabla pandas, detalle), donde detalle incluye el origen y parametros/evidencia.
    La pantalla puede mostrar cualquiera de los motores sin conocer su protocolo particular."""
    # Reutilizar las conexiones compartidas de la aplicacion, creadas por el modulo de Cesar.
    from conexiones import mongo, pg_df
    # POSTGRESQL: ejecutar el SQL preparado y devolver su tabla con el alcance efectivo.
    if tecnologia == "PostgreSQL":
        sql, params = sql_postgres(consulta, filtros)
        return pg_df(sql, params), {"origen": "PostgreSQL", "parametros": params or "Catalogo completo / snapshot historico"}
    # MONGODB: ejecutar la agregacion; permitir uso de disco y limitar la espera a cinco minutos.
    if tecnologia == "MongoDB":
        coleccion, pipeline = pipeline_mongo(consulta, filtros)
        documentos = list(mongo()[coleccion].aggregate(pipeline, allowDiskUse=True, maxTimeMS=300000))
        # ObjectId y fechas BSON se convierten a Extended JSON antes de aplanar la tabla para Streamlit.
        documentos = json.loads(json_util.dumps(documentos))
        return pd.json_normalize(documentos), {"origen": "MongoDB", "coleccion": coleccion,
                                               "filtros": json.loads(json_util.dumps(pipeline[0]["$match"]))}
    # HADOOP: invocar el mismo ejecutor utilizado por la CLI; conservar la evidencia YARN.
    if tecnologia == "Hadoop":
        from hadoop.ejecutar_mapreduce import ejecutar
        resultado = ejecutar(consulta, filtros)
        return pd.DataFrame(resultado["filas"], columns=resultado["columnas"]), dict(resultado, origen="HDFS / Hadoop MapReduce")
    # SPARK: convertir la respuesta del puente y etiquetar su motor de procesamiento.
    if tecnologia == "Spark":
        tabla, resultado = ejecutar_spark(consulta, filtros)
        return tabla, dict(resultado, origen="Spark SQL / DataFrames")
    raise ValueError("Tecnologia desconocida")
