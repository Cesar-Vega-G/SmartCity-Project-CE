from pyspark.sql import functions as F

from comun_spark import crear_spark, guardar_pg, leer_lecturas

# 50 km/h limite en ciudad, co2 de fondo 420 ppm
VEL_LIBRE = 50.0
FONDO_CO2 = 420.0
CO2_POR_CO = 60.0


# deja en null los valores marcados como invalidos
def valor(var):
    malo = F.array_contains(F.coalesce(F.col("invalidos"), F.array().cast("array<string>")), var)
    return F.when(malo, None).otherwise(F.col(var))


spark = crear_spark("indicadores")
lecturas = leer_lecturas(spark).withColumn("hora", F.date_trunc("hour", "fecha_hora"))

trafico = (lecturas.filter(F.col("tipo") == "trafico")
           .select("id_sensor", "distrito", "hora",
                   valor("intensidad").alias("intensidad"),
                   valor("ocupacion").alias("ocupacion"),
                   valor("carga").alias("carga"),
                   valor("velocidad").alias("velocidad"))
           .withColumn("velocidad", F.when(F.col("velocidad") > 0, F.col("velocidad")))
           .withColumn("tramo", F.least(F.floor(F.col("ocupacion") / 5) * 5, F.lit(90)).cast("int")))

# curva de velocidad segun ocupacion, sale de la m30
real = trafico.filter(F.col("velocidad").isNotNull() & F.col("ocupacion").isNotNull())
vel_libre = real.filter(F.col("ocupacion") < 15).agg(F.avg("velocidad")).first()[0]
print("lecturas con velocidad real:", real.count())
print("velocidad libre M30 (ocupacion < 15%):", round(vel_libre, 1))

curva = (real.groupBy("tramo")
         .agg(F.count("*").alias("lecturas"), F.round(F.avg("velocidad"), 1).alias("velocidad_m30"))
         .withColumn("factor", F.round(F.least(F.col("velocidad_m30") / vel_libre, F.lit(1.0)), 3))
         .orderBy("tramo"))
curva.show(20)
guardar_pg(curva, "spark_curva_velocidad")

# la m30 se queda con su velocidad real
m30 = real.select("id_sensor").distinct().withColumn("es_m30", F.lit(True))
print("puntos con velocidad real (M30):", m30.count())

trafico = (trafico.join(F.broadcast(curva.select("tramo", "factor")), "tramo", "left")
           .join(F.broadcast(m30), "id_sensor", "left")
           .withColumn("velocidad_urbana",
                       F.when(F.col("es_m30").isNull(), F.lit(VEL_LIBRE) * F.col("factor"))))

por_punto = (trafico.groupBy("id_sensor", "distrito", "hora")
             .agg(F.avg("intensidad").alias("intensidad"),
                  F.avg("carga").alias("carga"),
                  F.avg("velocidad").alias("vel_m30"),
                  F.avg("velocidad_urbana").alias("vel_urbana")))

movilidad = (por_punto.groupBy("distrito", "hora")
             .agg(F.round(F.sum("intensidad")).alias("vehiculos_hora"),
                  F.round(F.avg("carga"), 2).alias("congestion"),
                  F.round(F.avg("vel_urbana"), 2).alias("velocidad_urbana_kmh"),
                  F.round(F.avg("vel_m30"), 2).alias("velocidad_m30_kmh"),
                  F.count("vel_m30").alias("puntos_m30"),
                  F.count("*").alias("puntos"))
             .withColumn("tiempo_min_km",
                         F.when(F.col("velocidad_urbana_kmh") > 0, F.round(60 / F.col("velocidad_urbana_kmh"), 2))))

# co2 estimado a partir del co
ambiente = (lecturas.filter(F.col("tipo") == "calidad_aire")
            .select("distrito", "hora", valor("co").alias("co"), valor("pm25").alias("pm25"))
            .groupBy("distrito", "hora")
            .agg(F.round(F.avg("co"), 3).alias("co"), F.round(F.avg("pm25"), 2).alias("pm25"))
            .withColumn("co2_ppm_estimado",
                        F.when(F.col("co").isNotNull(), F.round(F.lit(FONDO_CO2) + F.lit(CO2_POR_CO) * F.col("co"), 1))))

guardar_pg(movilidad, "spark_kpi_movilidad")
guardar_pg(ambiente, "spark_kpi_ambiente")

movilidad.agg(F.count("*").alias("filas"),
              F.round(F.avg("velocidad_urbana_kmh"), 1).alias("vel_urbana_media"),
              F.round(F.avg("velocidad_m30_kmh"), 1).alias("vel_m30_media"),
              F.round(F.avg("tiempo_min_km"), 2).alias("min_por_km"),
              F.round(F.avg("congestion"), 1).alias("congestion_media")).show()
(movilidad.groupBy(F.hour("hora").alias("hora_dia"))
 .agg(F.round(F.avg("velocidad_urbana_kmh"), 1).alias("vel_urbana"),
      F.round(F.avg("velocidad_m30_kmh"), 1).alias("vel_m30"),
      F.round(F.avg("congestion"), 1).alias("congestion"))
 .orderBy("hora_dia").show(24))
ambiente.agg(F.count("*").alias("filas"),
             F.round(F.avg("co2_ppm_estimado"), 1).alias("co2_medio"),
             F.round(F.min("co2_ppm_estimado"), 1).alias("co2_min"),
             F.round(F.max("co2_ppm_estimado"), 1).alias("co2_max")).show()

spark.stop()
