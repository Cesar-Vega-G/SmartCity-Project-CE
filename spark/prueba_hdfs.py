from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("prueba_hdfs").getOrCreate()

# prueba: leer de hdfs y guardar parquet
clima = spark.read.csv("hdfs://namenode:8020/smartcity/raw/madrid/clima", header=True, inferSchema=True)
print("filas de clima:", clima.count())
clima.printSchema()

clima.write.mode("overwrite").parquet("hdfs://namenode:8020/smartcity/procesado/prueba_clima")
print("parquet guardado:", spark.read.parquet("hdfs://namenode:8020/smartcity/procesado/prueba_clima").count())

spark.stop()
