# Matriz comparativa

Cada calificacion sale de lo que hicimos y medimos en el proyecto. Tiempos en `docs/rendimiento_motores.md` (15/11/2026) y del Sprint 1 en `docs/rendimiento_postgres.md` y `docs/rendimiento_mongo.md`.

| Criterio | PostgreSQL | MongoDB | Hadoop (HDFS + MapReduce) | Spark |
| --- | --- | --- | --- | --- |
| Datos estructurados | Excelente: catalogos con llaves foraneas y CHECK | Bueno | Bueno: guarda cualquier archivo | Excelente: DataFrames con esquema |
| Datos semiestructurados | Bueno: habria que usar JSONB o una fila por variable | Excelente: cada sensor guarda solo sus variables | Excelente: guardamos el JSON tal cual | Excelente: leyo el JSON de Mongo con esquema |
| Relaciones complejas | Excelente: 5 uniones en `v_sensor_detalle` | Limitado: no hay llaves foraneas, el id_sensor lo cuida la carga | No es su proposito | Bueno: joins entre DataFrames |
| Busqueda puntual | Excelente: 6,6 ms con indice | Excelente: 6,9 ms con indice | Malo: 39 s | Regular: 396 ms |
| Recorrer todos los datos | Bueno: 978 ms | Regular: 2.856 ms | Lento aqui (45 s), pensado para volumenes mucho mayores | Excelente: 469 ms |
| Consultas SQL | Si | No: Aggregation Framework | No directamente | Si: Spark SQL |
| Crecer a mas maquinas | Limitado: una sola maquina | Escala horizontal (sharding), no lo usamos | Si: se agregan datanodes | Si: se agregan workers |
| Integridad de datos | Excelente | No relacional | No es su objetivo | No es su objetivo |

## Lo que muestran las mediciones

- Con indices, PostgreSQL y MongoDB responden busquedas puntuales en milisegundos. Spark tarda 60 veces mas porque organiza el trabajo aunque la respuesta sea chica.
- Cuando hay que recorrer todo, Spark gana: lee solo las columnas que necesita del Parquet y reparte el trabajo.
- MapReduce tarda unos 40 s en cualquier consulta, casi todo en arrancar el trabajo. Con 1,4 GB ese costo pesa; con 100 veces mas datos el trabajo tomaria horas y ese arranque seria despreciable.
- Los 4 dieron el mismo resultado (C2: 16 distritos, 31,95 de NO2 promedio).

## Donde usamos cada uno

- PostgreSQL: catalogos, mediciones limpias y resultados finales que lee el dashboard.
- MongoDB: lecturas tal como llegan, alertas, eventos e incidentes.
- Hadoop: la historia completa sin tocar (1,4 GB en 10 bloques el archivo de lecturas) y conteos con MapReduce.
- Spark: limpieza (JSON a Parquet), indicadores y analisis que recorren todo; guarda resultados en PostgreSQL.

Limitaciones: todo corre en una sola computadora (1 datanode, 1 worker de 2 nucleos), asi que no se mide el beneficio real de agregar maquinas. PostgreSQL guarda una fila por variable y hora, por eso C1 devuelve 3.666 filas contra 744 lecturas.
