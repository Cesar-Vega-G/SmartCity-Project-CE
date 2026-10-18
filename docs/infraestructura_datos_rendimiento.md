# Infraestructura, datos y rendimiento

Sección del avance 1 a cargo de Cesar.

## 1. Infraestructura

Las dos bases corren en contenedores de Docker, definidos en `docker-compose.yml`. Así cualquiera del grupo levanta exactamente lo mismo con un solo comando.

| Servicio | Imagen | Contenedor | Puerto en la compu | Volumen |
| --- | --- | --- | --- | --- |
| PostgreSQL | `postgres:16` | `smartcity_pg` | 5433 | `pg_data` |
| MongoDB | `mongo:7` | `smartcity_mongo` | 27017 | `mongo_data` |

- PostgreSQL usa el puerto 5433 y no el 5432 porque el 5432 suele estar ocupado si hay un Postgres instalado en Windows. Se puede cambiar con `PG_PORT` en `.env`.
- Usuarios, contraseñas y puerto van en `.env`, que no se sube a GitHub. En el repo solo está `.env.example`.
- Los volúmenes guardan los datos aunque se apaguen los contenedores. `docker compose down -v` los borra y deja todo en cero.
- La carpeta `postgres/init` se monta en el contenedor y Postgres ejecuta `01_ddl.sql` la primera vez que arranca, así las tablas se crean solas.
- Los scripts de carga y de rendimiento están en Python (pandas, numpy, psycopg, pymongo; ver `requirements.txt`). Leen la conexión de `.env` desde `data/generators/comun.py`.

Pasos para levantar todo desde cero: ver `README.md`.

## 2. Datos

La ciudad es Madrid. Se usan datos abiertos reales del Ayuntamiento (calidad del aire y tráfico), clima de Open-Meteo y un patrón real de consumo eléctrico (UCI). Lo que no existe en datos abiertos se genera con semilla fija `42`. El detalle está en `docs/contrato_datos.md` y `docs/generacion_datos.md`.

Flujo:

```
datos crudos (data/raw) ──> MongoDB (lecturas tal cual llegan, alertas, eventos, incidentes)
                                │
                                │ limpieza: solo valores válidos, promedio por hora
                                ▼
                           PostgreSQL (medicion + catálogos)
```

- MongoDB guarda la lectura cruda como documento, con campos distintos según el tipo de sensor.
- PostgreSQL guarda el dato limpio y estructurado, para consultas con JOIN y restricciones.
- Las dos bases se cruzan por `id_sensor` (`S-00001`); `codigo_origen` guarda el código original de Madrid.
- `medicion` está particionada por año (2024, 2025, 2026 y una partición `default`).

Volumen cargado:

| Base | Tabla / colección | Registros |
| --- | --- | --- |
| PostgreSQL | sensor | 324 (304 activos, 11 inactivos, 9 en mantenimiento) |
| PostgreSQL | medicion | 4.664.093 |
| MongoDB | lecturas | 3.151.581 |
| MongoDB | alertas | 47.443 |
| MongoDB | eventos | 7.397 |
| MongoDB | incidentes | 4.000 |

## 3. Rendimiento

### 3.1 Índices

**PostgreSQL** (`postgres/rendimiento/indices.sql`)

| Índice | Para qué |
| --- | --- |
| `medicion (id_sensor, fecha_hora)` | Buscar las mediciones de un sensor en un rango de fechas |
| `medicion (id_variable, fecha_hora)` | Buscar una variable (ej. no2) en un rango de fechas |
| `sensor (id_tipo)`, `sensor (id_ubicacion)`, `sensor (id_organismo)`, `ubicacion (id_distrito)`, `vehiculo (id_ruta)`, `ruta_estacion (id_estacion)` | Llaves foráneas: Postgres no les crea índice solo y se usan en los JOIN |
| `sensor (estado)`, `sensor (fecha_instalacion)` | Filtros frecuentes sobre sensores |

Como `medicion` está particionada, el índice se crea en la tabla padre y Postgres lo crea en cada partición.

**MongoDB** (`mongo/rendimiento/indices.js`)

| Colección | Índice | Para qué |
| --- | --- | --- |
| lecturas | `{id_sensor, timestamp}` | Lecturas de un sensor en un rango de fechas / últimas lecturas |
| lecturas | `{tipo, timestamp}` | Lecturas de un tipo de sensor en un período |
| lecturas | `{ubicacion.geo: 2dsphere}` | Búsquedas por cercanía geográfica |
| alertas | `{nivel, ubicacion.distrito}` | Alertas por nivel y distrito |
| alertas | `{id_sensor, timestamp}` | Alertas de un sensor en el tiempo |
| eventos | `{tipo_evento, timestamp}` | Eventos por tipo en un período |
| incidentes | `{categoria, fecha_reporte}` | Incidentes por categoría y fecha |

En los índices compuestos va primero el campo que se compara por igualdad y después el de rango (la fecha).

### 3.2 Cómo se midió

- Se hicieron 5 consultas en cada base. Las primeras cuatro hacen la misma pregunta en Postgres y en Mongo, para poder comparar.
- Cada script quita los índices, mide, crea los índices y vuelve a medir.
- Cada tiempo es la mediana de 3 ejecuciones, para que no influya una ejecución suelta más lenta.
- PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS)`. MongoDB: tiempo desde Python + `explain("executionStats")`.
- Scripts: `postgres/rendimiento/medir_pg.py` y `mongo/rendimiento/medir_mongo.py`. Los planes completos quedan en las carpetas `planes/`.

| # | Pregunta | Postgres | Mongo |
| --- | --- | --- | --- |
| 1 | Mediciones de un sensor en marzo 2025 | q1 | m1 |
| 2 | Últimas 24 mediciones de un sensor | q2 | m2 |
| 3 | Promedio de NO2 por distrito en enero 2025 | q3 | m3 |
| 4 | Tráfico en julio 2026 (Postgres: horas con carga > 80; Mongo: lecturas a menos de 1 km de Puerta del Sol) | q4 | m4 |
| 5 | Postgres: sensores sin mediciones / Mongo: cantidad de alertas críticas por distrito | q5 | m5 |

### 3.3 Resultados

Tablas completas: `docs/rendimiento_postgres.md` y `docs/rendimiento_mongo.md`.

**PostgreSQL** (tabla `medicion`: 4.664.093 filas, 304 MB de datos, 268 MB de índices)

| Consulta | Sin índice (ms) | Con índice (ms) | Mejora | Plan sin → con |
| --- | --- | --- | --- | --- |
| q1. Mediciones de un sensor en marzo 2025 | 30,8 | 0,5 | 57x | Seq Scan → Index Scan |
| q2. Últimas 24 mediciones de NO2 de un sensor | 116,9 | 0,1 | 1146x | Seq Scan → Index Scan |
| q3. Promedio de NO2 por distrito en enero 2025 | 44,7 | 12,7 | 4x | Seq Scan → Bitmap Index Scan |
| q4. Horas con carga > 80 en julio 2026 | 80,5 | 24,5 | 3x | Seq Scan → Bitmap Index Scan |
| q5. Sensores sin ninguna medición | 991,1 | 3,4 | 292x | Seq Scan → Index Only Scan |

**MongoDB** (colección `lecturas`: 3.151.581 documentos, 1092 MB de datos, 129 MB de índices)

| Consulta | Sin índice (ms) | Con índice (ms) | Mejora | Docs revisados sin → con | Resultados |
| --- | --- | --- | --- | --- | --- |
| m1. Lecturas de un sensor en marzo 2025 | 1134,7 | 4,9 | 230x | 3.151.581 → 744 | 744 |
| m2. Últimas 24 lecturas de un sensor de tráfico | 1013,8 | 1,4 | 720x | 3.151.581 → 24 | 24 |
| m3. Promedio de NO2 por distrito en enero 2025 | 1202,9 | 42,2 | 29x | 3.151.581 → 17.112 | 16 |
| m4. Lecturas a menos de 1 km de Puerta del Sol en julio 2026 | 1820,8 | 229,9 | 8x | 3.151.581 → 135.317 | 19.900 |
| m5. Alertas críticas por distrito | 18,4 | 7,9 | 2x | 47.443 → 0 | 12 |

### 3.4 Análisis

**PostgreSQL**
- Sin índices, todas las consultas hacen `Seq Scan`, o sea leen la partición completa fila por fila.
- Aun sin índices, q1, q3 y q4 solo leen la partición del año que piden (partition pruning). Por eso sus tiempos sin índice no son tan altos: q1 lee solo `medicion_2025` y no las 4,6 millones de filas.
- q2 no filtra por fecha, así que sin índice revisa todas las particiones. Con `(id_sensor, fecha_hora)` va directo al sensor y lee las fechas ya ordenadas de la más nueva hacia atrás. Solo saca 24 filas y para (0,1 ms).
- q5 es la que más mejora (de casi 1 s a 3 ms). Por cada uno de los 324 sensores pregunta si existe alguna medición. Sin índice tiene que recorrer la tabla; con índice le basta mirar el índice (`Index Only Scan`), sin tocar la tabla.
- q3 y q4 mejoran menos (3–4x) porque, aunque el índice encuentra rápido las filas de la variable y el mes, igual tienen que leer muchas filas para promediar o contar. El `Seq Scan` que sigue apareciendo es en tablas pequeñas (`variable`, `sensor`, `distrito`), donde leer todo es más barato que usar un índice.

**MongoDB**
- Sin índices, todas las consultas a `lecturas` hacen `COLLSCAN`: revisan los 3,1 millones de documentos para devolver unos pocos. Por eso todas tardan alrededor de 1 s.
- Con índices, en m1 y m2 los documentos revisados son exactamente los que se devuelven (744 → 744 y 24 → 24). Es el caso ideal: no se revisa nada de más.
- En m3 se revisan 17.112 lecturas de calidad del aire de enero 2025 para dar 16 promedios (uno por distrito con estación). El índice `{tipo, timestamp}` reduce lo que se revisa, pero el promedio necesita todas esas lecturas.
- m4 usa el índice `2dsphere` para encontrar las lecturas cerca de Puerta del Sol, pero la fecha la filtra después. Por eso revisa 135.317 documentos para devolver 19.900. Se podría mejorar con un índice compuesto `{ubicacion.geo, timestamp}`.
- En m5, `alertas` es una colección pequeña (47 mil documentos), así que la mejora es menor. Revisa 0 documentos porque todo lo que necesita (`nivel` y `ubicacion.distrito`) ya está dentro del índice: es una consulta cubierta.

**Postgres vs Mongo**
- Las tablas no se pueden comparar directamente entre bases. En Postgres el tiempo es el que mide el servidor (`EXPLAIN ANALYZE`). En Mongo se mide desde Python, e incluye mandar los documentos por la red.
- Además, los datos no son iguales: Mongo guarda las lecturas crudas (tráfico cada 15 min, todas las variables en un documento) y Postgres guarda una fila por variable y por hora, ya limpia.
- Lo que sí se compara es el comportamiento: en las dos bases, las consultas que buscan pocos datos por sensor y fecha (1 y 2) son las que más ganan con un índice compuesto, y las que agregan muchos datos (3 y 4) ganan menos.

**Costo de los índices**
- Ocupan espacio: en Postgres los índices de `medicion` (incluida la llave primaria) pesan 268 MB, casi lo mismo que los datos (304 MB).
- Hacen más lentas las inserciones, porque cada fila nueva también se agrega a cada índice. Por eso no se indexa todo, solo los campos que se usan en las consultas.
- Recomendación para la carga masiva: cargar primero y crear los índices después.
