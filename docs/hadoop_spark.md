# Hadoop y Spark

## Levantar

```
docker compose up -d
docker exec smartcity_namenode hdfs dfsadmin -safemode wait
```

La primera vez hay que cargar HDFS y preparar las lecturas para Spark:

```
python hadoop/cargar_hdfs.py
docker exec smartcity_spark_master /opt/spark/bin/spark-submit /proyecto/spark/etl_lecturas.py
```

Paginas: HDFS `localhost:9870`, YARN `localhost:8088`, Spark `localhost:8080`.

## HDFS

| Carpeta | Contenido |
| --- | --- |
| `/smartcity/raw/madrid` | `data/raw` tal cual (aire, clima, energia, trafico) |
| `/smartcity/raw/mongo` | Las 4 colecciones exportadas a JSON |
| `/smartcity/procesado/lecturas` | Lecturas en Parquet por anio (las deja `etl_lecturas.py`) |
| `/smartcity/resultados` | Salidas de MapReduce |

Una sola computadora, entonces `dfs.replication=1`. Comandos de la demo en `hadoop/comandos_hdfs.sh`.

## Spark

Los scripts van en `spark/` y se corren con:

```
docker exec smartcity_spark_master /opt/spark/bin/spark-submit /proyecto/spark/<script>.py
```

`spark/comun_spark.py` tiene `crear_spark`, `leer_lecturas` (3.151.581 lecturas, una columna por variable), `leer_pg` y `guardar_pg`. Los resultados se guardan en Postgres con prefijo `spark_`.

Cobertura de fechas: aire y clima 2024-2026, energia 2025-2026, trafico, parqueo y ruido solo jun-ago 2026.

## MapReduce

El `nodemanager` tiene Python 3.6. `./hadoop` esta montado en el namenode como `/proyecto/hadoop`. El jar de streaming es `/opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.4.1.jar`.
