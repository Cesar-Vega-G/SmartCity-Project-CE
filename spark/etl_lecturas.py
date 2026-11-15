from pyspark.sql import functions as F

from comun_spark import ESQUEMA_LECTURA, LECTURAS, LECTURAS_JSON, aplanar, crear_spark, guardar_pg, leer_pg

spark = crear_spark("etl_lecturas")

crudo = spark.read.schema(ESQUEMA_LECTURA).json(LECTURAS_JSON)
lecturas = aplanar(crudo)
lecturas.write.mode("overwrite").partitionBy("anio").parquet(LECTURAS)

lecturas = spark.read.parquet(LECTURAS)
print("lecturas en parquet:", lecturas.count())

resumen = (lecturas.groupBy("tipo")
           .agg(F.count("*").alias("lecturas"),
                F.sum(F.when(~F.col("valido"), 1).otherwise(0)).alias("invalidas"),
                F.min("fecha_hora").alias("desde"),
                F.max("fecha_hora").alias("hasta"))
           .orderBy("tipo"))
resumen.show(truncate=False)
guardar_pg(resumen, "spark_resumen_carga")

print("sensores en postgres:", leer_pg(spark, "sensor").count())

spark.stop()
