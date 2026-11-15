import json
import statistics
import time

from pyspark.sql import functions as F

from comun_spark import crear_spark, leer_lecturas

REP = 3

spark = crear_spark("medir_spark")
df = leer_lecturas(spark)


# las mismas 3 consultas que en postgres, mongo y mapreduce
def c1():
    return df.filter((F.col("anio") == 2025) & (F.col("id_sensor") == "S-00002")
                     & (F.col("fecha_hora") >= "2025-03-01") & (F.col("fecha_hora") < "2025-04-01")).count()


def c2():
    malo = F.array_contains(F.coalesce(F.col("invalidos"), F.array().cast("array<string>")), "no2")
    filas = (df.filter((F.col("anio") == 2025) & (F.col("tipo") == "calidad_aire")
                       & (F.col("fecha_hora") >= "2025-01-01") & (F.col("fecha_hora") < "2025-02-01")
                       & F.col("no2").isNotNull() & ~malo)
             .groupBy("distrito").agg(F.avg("no2").alias("no2")).collect())
    return len(filas), round(sum(r["no2"] for r in filas) / len(filas), 3)


def c3():
    filas = df.groupBy("tipo", "anio").count().collect()
    return len(filas), sum(r["count"] for r in filas)


salida = {}
for nombre, f in [("c1", c1), ("c2", c2), ("c3", c3)]:
    tiempos = []
    for _ in range(REP):
        t = time.perf_counter()
        res = f()
        tiempos.append((time.perf_counter() - t) * 1000)
    salida[nombre] = {"ms": round(statistics.median(tiempos), 1), "resultado": res}

print("RESULTADO " + json.dumps(salida))
spark.stop()
