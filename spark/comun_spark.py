import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, BooleanType, DoubleType, StringType, StructField, StructType

HDFS = "hdfs://namenode:8020/smartcity"
LECTURAS_JSON = f"{HDFS}/raw/mongo/lecturas.json"
LECTURAS = f"{HDFS}/procesado/lecturas"

PG_URL = f"jdbc:postgresql://postgres:5432/{os.environ.get('PG_DB', 'smartcity')}"
PG_PROPS = {
    "user": os.environ.get("PG_USER", "smartcity"),
    "password": os.environ.get("PG_PASSWORD", "smartcity123"),
    "driver": "org.postgresql.Driver",
}

VARIABLES = ["no2", "pm10", "pm25", "co", "o3", "temperatura", "humedad", "precipitacion", "ruido_db",
             "intensidad", "ocupacion", "carga", "velocidad", "ocupacion_parking", "consumo_kwh"]

ESQUEMA_LECTURA = StructType([
    StructField("id_sensor", StringType()),
    StructField("tipo", StringType()),
    StructField("categoria", StringType()),
    StructField("ubicacion", StructType([
        StructField("distrito", StringType()),
        StructField("nombre", StringType()),
        StructField("geo", StructType([StructField("coordinates", ArrayType(DoubleType()))])),
    ])),
    StructField("medicion", StructType([StructField(v, DoubleType()) for v in VARIABLES])),
    StructField("valido", BooleanType()),
    StructField("invalidos", ArrayType(StringType())),
    StructField("timestamp", StructType([StructField("$date", StringType())])),
])


def crear_spark(nombre):
    return SparkSession.builder.appName(nombre).getOrCreate()


def leer_lecturas(spark):
    return spark.read.parquet(LECTURAS)


def leer_pg(spark, tabla):
    return spark.read.jdbc(PG_URL, tabla, properties=PG_PROPS)


def guardar_pg(df, tabla):
    df.write.jdbc(PG_URL, tabla, mode="overwrite", properties=PG_PROPS)


def aplanar(df):
    return df.select(
        "id_sensor", "tipo", "categoria",
        F.col("ubicacion.distrito").alias("distrito"),
        F.col("ubicacion.nombre").alias("lugar"),
        F.col("ubicacion.geo.coordinates")[0].alias("lon"),
        F.col("ubicacion.geo.coordinates")[1].alias("lat"),
        F.to_timestamp(F.col("timestamp.`$date`")).alias("fecha_hora"),
        "valido", "invalidos", "medicion.*",
    ).withColumn("anio", F.year("fecha_hora"))
