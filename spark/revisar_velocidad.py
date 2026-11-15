from pyspark.sql import functions as F

from comun_spark import crear_spark, leer_lecturas

spark = crear_spark("revisar_velocidad")
t = (leer_lecturas(spark)
     .filter((F.col("tipo") == "trafico") & F.col("velocidad").isNotNull())
     .select("id_sensor", "carga", "ocupacion", "intensidad", "velocidad"))

print("lecturas con velocidad:", t.count())
print("de esas, con velocidad 0:", t.filter(F.col("velocidad") == 0).count())
t.select(F.min("velocidad"), F.expr("percentile(velocidad, 0.5)").alias("mediana"), F.max("velocidad")).show()

# sin ceros ni -1, que son errores del sensor
v = t.filter(F.col("velocidad") > 0)
for col in ["carga", "ocupacion", "intensidad"]:
    print(f"correlacion {col}-velocidad (sin ceros):", round(v.stat.corr(col, "velocidad"), 3))

(v.withColumn("tramo_carga", (F.floor(F.col("carga") / 10) * 10).cast("int"))
 .groupBy("tramo_carga")
 .agg(F.count("*").alias("lecturas"), F.round(F.avg("velocidad"), 1).alias("velocidad_media"))
 .orderBy("tramo_carga").show(20))

(v.withColumn("tramo_ocupacion", (F.floor(F.col("ocupacion") / 5) * 5).cast("int"))
 .groupBy("tramo_ocupacion")
 .agg(F.count("*").alias("lecturas"), F.round(F.avg("velocidad"), 1).alias("velocidad_media"))
 .orderBy("tramo_ocupacion").show(25))

spark.stop()
