# Hadoop — MapReduce de Sebastian

HDFS guarda los archivos; MapReduce responde las cinco preguntas del cronograma.
Se reutiliza la infraestructura y la carga de Cesar. Python solo implementa los
mappers y reducers; los trabajos finales se ejecutan realmente en YARN.

## Preparacion

Desde la raiz del repositorio:

```powershell
docker compose up -d postgres mongo namenode datanode resourcemanager nodemanager
docker exec smartcity_namenode hdfs dfsadmin -safemode wait
docker exec smartcity_namenode hdfs dfs -ls /smartcity/raw/mongo
docker exec smartcity_resourcemanager yarn node -list
```

Si faltan las exportaciones, preparar HDFS con el cargador existente de Cesar:
`python hadoop/cargar_hdfs.py`. Este paso lee MongoDB y copia archivos a HDFS;
no es necesario regenerar PostgreSQL ni MongoDB para ejecutar consultas.

## Las cinco preguntas

```powershell
python hadoop/ejecutar_mapreduce.py 1
python hadoop/ejecutar_mapreduce.py 2
python hadoop/ejecutar_mapreduce.py 3
python hadoop/ejecutar_mapreduce.py 4
python hadoop/ejecutar_mapreduce.py 5 --desde 2026-07-01 --hasta 2026-08-01 --variable temperatura
```

| ID | Pregunta | Salida |
| --- | --- | --- |
| 1 | Mediciones por sensor | Sensor y cantidad de documentos crudos, incluidos los invalidos. |
| 2 | Sensor con mas datos | Todos los sensores empatados en el maximo global de lecturas. |
| 3 | Temperatura promedio historica | Variable, unidad, cantidad valida, promedio, minimo y maximo de todo el historico. |
| 4 | Eventos por zona | Distrito y cantidad de documentos de eventos. |
| 5 | Comportamiento durante un periodo | Dia UTC almacenado, sensor, variable, unidad, cantidad, promedio, minimo y maximo. |

Las consultas 1, 2 y 4 aceptan `--desde`, `--hasta`, `--distrito`; 1, 2 y 5
tambien admiten `--tipo` y `--sensor`. Distrito y tipo se pueden repetir.
La 5 exige periodo. La 3 siempre usa el historico completo e ignora los filtros.
`--evidencia archivo.json` guarda la salida y los identificadores de YARN localmente.

Cada ejecucion crea una ruta nueva `/smartcity/resultados/consulta_<id>_<fecha>_<id>/`.
No borra salidas previas ni datos crudos. El JSON informa la ruta final y las
aplicaciones YARN. Los tiempos incluyen el arranque de los trabajos.

## Como funciona

`mapreduce.py map` lee JSON por linea y emite una clave y un valor separados por
tabulador. Hadoop reparte las entradas, ordena y agrupa las claves. El reducer
acumula conteos o suma/cantidad/minimo/maximo. El promedio se calcula al terminar
el grupo, evitando promediar promedios con distinto numero de muestras.

La consulta 2 ejecuta dos trabajos: primero cuenta por sensor; luego todos los
conteos se agrupan bajo una clave comun para obtener el maximo global y sus empates.
`ejecutar_mapreduce.py` envia los scripts con `-files`; el NodeManager ejecuta
Python 3.6. El NameNode no necesita Python para lanzar el trabajo.

Se respeta la calidad de MongoDB: una variable numerica finita que no este en
`invalidos` puede contribuir aunque otra variable del documento sea invalida.
`valido:false` sin detalle de variables invalidas se excluye de las estadisticas.
No se imputan ausentes ni se mezclan unidades. Los documentos malformados se
descartan y quedan registrados en el contador YARN `documentos_malformados`.

Las fechas admiten Extended JSON relajado y canonico. Se conserva la codificacion
heredada en UTC, con rangos `[desde, hasta)`. No se realiza una correccion a hora
de Madrid. Los conteos de documentos Mongo no equivalen a las filas por variable
y hora de PostgreSQL.

## Pruebas y demostracion

```powershell
python -m unittest discover -s hadoop/tests -v
python hadoop/verificar_integracion.py
docker exec smartcity_namenode hdfs dfs -mkdir -p /smartcity/demo/mapreduce
docker exec smartcity_namenode hdfs dfs -put -f /proyecto/hadoop/tests/lecturas.jsonl /proyecto/hadoop/tests/eventos.jsonl /smartcity/demo/mapreduce/
python hadoop/ejecutar_mapreduce.py 2 --entrada /smartcity/demo/mapreduce/lecturas.jsonl
```

La muestra tiene A=2, B=2, C=1: el maximo debe devolver A y B. La temperatura
historica valida debe dar 3 muestras y promedio 20 C. Los eventos de prueba son
Centro=2 y Retiro=1. La opcion `--entrada` permite repetir las cinco consultas
contra esas muestras antes de ejecutar el historico real.

`verificar_integracion.py` ejecuta las cinco consultas sobre el historico de HDFS,
las contrasta con referencias de MongoDB y guarda un resumen en
`hadoop/evidencia/historico.json`. Puede tardar varios minutos y conserva todas las
salidas HDFS. Solo se considera aprobada la verificacion cuando `aprobado` es true
y las cinco consultas tienen `ok: true`.

HDFS: `http://localhost:9870`; YARN: `http://localhost:8088`. Mostrar una aplicacion
terminada, los bloques con `hdfs fsck <archivo> -files -blocks` y el resultado con
`hdfs dfs -cat <ruta_final>/part-*`. La demostracion de mkdir/put/ls/cat/get/rm ya
esta en `comandos_hdfs.sh`, preparada por Cesar.

La instalacion local tiene un DataNode y replicacion 1. El NameNode registra la
ubicacion de los bloques y el DataNode los almacena. Con mas DataNodes se pueden
distribuir bloques y replicas y ejecutar tareas cerca de los datos. Esta instalacion
no demuestra resistencia a la perdida de un DataNode ni de la computadora completa.
