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

## Indicadores estimados (`spark/indicadores.py`)

Madrid no publica CO2, velocidad en calles normales ni tiempo de recorrido. Se calculan con datos reales:

- Velocidad: solo 16 puntos de la M30 la miden. Con sus lecturas se sacó cuanto baja la velocidad segun la ocupacion (tabla `spark_curva_velocidad`; a partir de 20 % de ocupacion empieza a caer). En las demas calles: `50 km/h x factor de su ocupacion`. Revision en `spark/revisar_velocidad.py` (la carga casi no se relaciona con la velocidad, la ocupacion si: -0,375).
- Tiempo de recorrido: `60 / velocidad` minutos por km.
- CO2: `420 + 60 x CO` ppm. El 60 es un supuesto nuestro, es una estimacion.

Tablas en Postgres: `spark_kpi_movilidad` y `spark_kpi_ambiente` (por distrito y hora). Limitaciones: no considera semaforos y los promedios esconden presas puntuales; en la ciudad la ocupacion casi nunca pasa de 15 %, por eso la velocidad urbana estimada casi no cambia en el dia (47 km/h) aunque la congestion si (3,5 de madrugada, 24 a mediodia).
