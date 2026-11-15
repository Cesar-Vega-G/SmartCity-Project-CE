# entrar al namenode: docker exec -it smartcity_namenode bash

hdfs dfs -mkdir -p /smartcity/demo
hdfs dfs -put /datos/raw/clima/clima_01.csv /smartcity/demo/
hdfs dfs -ls /smartcity/demo
hdfs dfs -cat /smartcity/demo/clima_01.csv | head -5
hdfs dfs -get /smartcity/demo/clima_01.csv /tmp/copia.csv
ls -lh /tmp/copia.csv
hdfs dfs -rm -r /smartcity/demo

# estructura y bloques
hdfs dfs -ls -R /smartcity
hdfs dfs -du -h /smartcity/raw/madrid /smartcity/raw/mongo
hdfs fsck /smartcity/raw/mongo/lecturas.json -files -blocks
