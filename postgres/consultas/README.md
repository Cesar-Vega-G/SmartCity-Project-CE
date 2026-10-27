# Consultas de PostgreSQL

Las consultas 1-8 conservan su implementación. Las complementarias 11-17 cubren
los requisitos básicos, relacionales, analíticos y avanzados junto con las existentes.
Las consultas [9 (vistas)](../vistas_funciones/09_consulta_vistas.sql) y
[10 (funciones y procedimientos)](../vistas_funciones/10_consulta_funciones.sql)
ya están integradas desde el PR #1 de Luis; se conservan en su carpeta.


Cada SQL se puede ejecutar completo en DBeaver, sin variables de `psql`.
Sus comentarios describen la pregunta, el criterio del resultado y la justificación.

## Parámetros de las complementarias

Editar los literales identificados en cada archivo. Los rangos incluyen el inicio
y excluyen el fin; así abarcan el último día sin depender de su precisión horaria.

| Consulta | Parámetros predeterminados | Resultado |
| --- | --- | --- |
| [11. Temperatura por distrito](11_temperatura_por_distrito.sql) | `temperatura`; desde `2026-07-01` hasta antes de `2026-08-01` | Distrito, unidad, cantidad, promedio, mínimo y máximo. Solo distritos con datos. |
| [12. Distritos sobre el promedio](12_distritos_sobre_promedio.sql) | Sin parámetros; catálogo de Madrid | Distritos sobre el promedio, total municipal y participación porcentual. |
| [13. Distritos sobre el umbral](13_distritos_sobre_umbral.sql) | Más de `15` sensores | Distritos y cantidad; exactamente 15 queda excluido. |
| [14. Sensores que dejaron de registrar](14_sensores_que_dejaron_de_registrar.sql) | Corte `2026-07-15 00:00:00`; cierre exclusivo `2026-09-01 00:00:00` | Sensores con historia y última medición anterior al corte. |
| [15. Carga por hora del día](15_carga_promedio_por_hora.sql) | `carga`; desde `2026-07-01` hasta antes de `2026-08-01` | Hasta 24 filas, ordenadas por carga promedio descendente y hora ascendente. |
| [16. Tipos por distrito](16_tipos_de_sensor_por_distrito.sql) | Distrito `Centro` | Tipos distintos, incluyendo sensores de todos los estados. |
| [17. Mediciones por mes](17_mediciones_sensor_por_mes.sql) | Sensor `S-00002`; desde `2025-03-01` hasta antes de `2025-04-01` | Mediciones individuales, con variable y unidad. |

El dataset termina el **31 de agosto de 2026**. Para la consulta 14, mantener
el corte dentro del período de datos y anterior al cierre. El corte elegido coincide
con `FECHA_BAJA` del generador. No usar la fecha actual para analizar este histórico.

## Interpretación de los resultados

- Las consultas de sensores incluyen todos los estados. La actividad de la 14 se
  determina por mediciones, no por el valor actual de `sensor.estado`.
- La 7 busca sensores sin ninguna medición histórica en PostgreSQL. La 14 exige
  historia previa y ausencia desde el corte hasta el cierre; ignora registros
  posteriores al cierre. Ninguna demuestra por sí sola una falla física ni ausencia
  de lecturas crudas en MongoDB.
- La 12 incluye distritos sin ubicaciones o sensores en el promedio. El total de la
  ciudad se calcula antes del filtro; los porcentajes de los distritos seleccionados
  no tienen por qué sumar 100. La protección con `NULLIF` evita dividir entre cero.
  Se presupone el catálogo actual de una sola ciudad, Madrid.
- La 11 filtra solo temperatura y la 15 solo carga. Sus promedios dan el mismo peso
  a cada medición horaria disponible, sin imputar faltantes ni igualar artificialmente
  la cobertura de sensores. Se conserva la precisión de los valores agregados.
- La 15 agrupa por hora del día entre todos los días del período, no por fecha y
  hora específicas. Usa el `TIMESTAMP` almacenado, sin convertir zonas horarias.
- La 17 puede devolver varias variables a una misma hora; cada una conserva su
  unidad y su valor. Su orden incluye el identificador de medición para desempatar.

## Matriz de cobertura

Una consulta puede cubrir varios requisitos. La matriz señala ejemplos, no todos
los usos de cada herramienta.

| Requisito | Consultas que lo demuestran |
| --- | --- |
| `SELECT` | 1-8 y 11-17 |
| `WHERE` | 7, 11, 12, 14-17 |
| `ORDER BY` | 1-8 y 11-17 |
| `DISTINCT` | 16 |
| `INNER JOIN` | 1, 2, 5, 7, 11, 14, 16, 17 |
| `LEFT JOIN` | 3, 4, 8, 12, 13 |
| `GROUP BY` | 3-6, 8, 11-15 |
| `HAVING` | 13 |
| `COUNT` | 3-6, 8, 11-13, 15 |
| `SUM` | 12: total de sensores de la ciudad |
| `AVG` | 11, 12, 15 |
| `MIN` y `MAX` | 11; `MAX` también en 14 |
| Subconsultas | 7: `NOT EXISTS`; 12: comparación con promedio escalar |
| CTE | 8, 12, 14 |
| Funciones de ventana | 8: `DENSE_RANK()` |
| Fechas | 6: año de instalación; 11, 14, 15, 17: actividad y períodos |
| Consulta compatible con índices | 17: igualdad por sensor y rango de fecha; confirmar con `EXPLAIN` en la base real |
| Vistas y funciones/procedimientos | 9 y 10: implementadas por persona B e integradas; ver enlaces anteriores |

## Validación en la base completa

Conectarse al PostgreSQL del proyecto, con la carga histórica completa, e iniciar
una transacción de solo lectura. No hace falta recrear datos ni índices.

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SELECT COUNT(*) AS cantidad_sensores FROM sensor;

SELECT COUNT(*) AS cantidad_mediciones,
       MIN(fecha_hora) AS primera_medicion,
       MAX(fecha_hora) AS ultima_medicion
FROM medicion;
```

Ejecutar a continuación los siete archivos en esa misma sesión y registrar las
cantidades y resultados observados, sin sustituirlos por las cifras documentadas.
Revisar los siguientes criterios:

| Consulta | Comprobación |
| --- | --- |
| 11 | Solo temperatura en julio; mínimo <= promedio <= máximo; cantidad positiva. |
| 12 | Promedio sobre todos los distritos, incluidos ceros; total municipal igual al conteo de sensores y anterior al filtro. |
| 13 | Todos los conteos son mayores que 15; exactamente 15 queda excluido. |
| 14 | Hay historia previa; no hay registros en `[2026-07-15, 2026-09-01)` para los sensores devueltos. |
| 15 | A lo sumo 24 filas; horas 0-23; solo carga en julio, sin horas vacías inventadas. |
| 16 | No repite distrito y tipo; distrito sin sensores o inexistente devuelve vacío. |
| 17 | Solo el sensor seleccionado; inicio de marzo incluido y abril excluido; variable y unidad separadas. |

Para verificar el acceso de la 17, anteponer `EXPLAIN (ANALYZE, BUFFERS)` a su
sentencia `SELECT` completa y ejecutarla. Debe observarse la poda hacia
`medicion_2025`; revisar si aparece el índice hijo de `idx_medicion_sensor_fecha`
con condiciones sobre `id_sensor` y `fecha_hora`. El índice de la partición puede
tener un nombre distinto al de la tabla padre. Al terminar la sesión:

```sql
ROLLBACK;
```

Si el índice no se usa, registrar el plan y revisar si existe, las estadísticas,
la cantidad de filas y la selectividad. No forzar el optimizador ni presentar el
uso como confirmado. Coordinar cualquier cambio de índices con César.
No ejecutar `postgres/rendimiento/medir_pg.py` para esta revisión: elimina y
recrea índices como parte de su comparación de rendimiento.

## Validación realizada el 22 de octubre de 2026

Se ejecutaron los siete SQL y las consultas 1-8 en una instancia temporal en memoria
con **PGlite 0.5.10 / PostgreSQL 18.6**, usando el DDL y los índices actuales del
repositorio. Los siete SQL se ejecutaron dentro de transacciones de solo lectura;
la preparación de los datos ocurrió únicamente en esa instancia aislada.

Pasaron **11 grupos de comprobaciones** que cubren:

- Variables separadas, límites de julio, promedio, mínimo y máximo.
- Distritos sin ubicaciones y sin sensores dentro del promedio; 41 sensores entre
  6 distritos, con un distrito de 2 sensores excluido del resultado pero incluido
  en el total municipal. Participación del distrito de 16 sensores: 39,02 %.
- Umbral estricto: 15 sensores excluidos y 16 incluidos.
- Sensores sin historia, con lectura exactamente en el corte, después del corte,
  exactamente en el cierre y con historia previa al corte. Un sensor de estado
  activo con última lectura anterior al corte fue incluido correctamente.
- Carga por hora: promedios, cantidades y desempate por hora; filtro de variable
  y fechas. Tipos sin duplicados; distrito inexistente o sin sensores.
- Inicio de marzo incluido y comienzo de abril excluido para el sensor seleccionado.
- Todas las consultas sin sensores ni mediciones, y la 12 sin distritos: resultados
  vacíos sin errores ni división entre cero.

Para el plan de la 17 se agregaron 50.000 mediciones de otro sensor y se actualizaron
las estadísticas **solo en la instancia temporal**. El plan observado incluyó:

```text
Index Scan using medicion_2025_id_sensor_fecha_hora_idx on medicion_2025 m
  Index Cond: (id_sensor = 'S-00002' AND fecha_hora >= '2025-03-01'
               AND fecha_hora < '2025-04-01')
```

Solo se accedió a la partición de 2025. Esto confirma el acceso en los datos
aislados; no representa una medición de rendimiento de la carga real.

**Pendiente registrado el 22 de octubre (histórico):** ejecutar sobre la carga completa y confirmar el plan en
**PostgreSQL 16**, que es la versión del `docker-compose.yml` del proyecto.
Durante esta implementación no se pudo establecer conexión al servicio local
en los puertos 5433 y 5432; tampoco había un `.env` en el repositorio.
No se modificaron el esquema, los índices, los generadores ni los datos del proyecto.


## Validación real del 26 de octubre de 2026

**42/42 comprobaciones aprobadas** en PostgreSQL 16.15: 324 sensores,
21 distritos y 4.664.093 mediciones. Se ejecutaron 21 SELECT que abarcan las
consultas 1–17, se compararon resultados con referencias independientes y se
comprobaron los errores esperados de las funciones. Los 324 estados originales
se conservaron después de la prueba del procedimiento y su ROLLBACK.

**Índices resueltos:** se aplicó el script existente de César
`postgres/rendimiento/indices.sql`, sin modificarlo ni ejecutar el programa de
benchmarks. La consulta 17 devuelve 3.666 filas y usa
`medicion_2025_id_sensor_fecha_hora_idx`, leyendo solo la partición de 2025.
Se conserva la evidencia previa de 41/42 como historial, no como estado actual.

- [Sección lista para el documento técnico](SECCION_PERSONA_C.md).
- [Evidencia aprobada, resultados y checklist](evidencia_con_indices/README.md).
- [Validador reproducible](validar_consultas.py).

Desde la raíz, usando el entorno Python del proyecto:

```powershell
.\.venv\Scripts\python.exe postgres/consultas/validar_consultas.py --salida postgres/consultas/evidencia_nueva
```

Devuelve código 0 cuando aprueba todo y 1 si hay fallos o pendientes. La ejecución
actual devuelve 0; las 42 comprobaciones aprobaron. Escribe solo muestras e informes en
`postgres/consultas/evidencia`; para conservar la evidencia anterior, indicar
`--salida postgres/consultas/evidencia_nueva` en una nueva ejecución.
Requiere las dependencias del proyecto y `.env`; no crea ni recarga datos,
vistas o índices. Ejecutarlo cuando no haya otras modificaciones simultáneas.

Las consultas de lectura usan REPEATABLE READ READ ONLY. La prueba de estados
usa otra transacción con ROLLBACK garantizado incluso ante un error.
El validador no ejecuta la llamada final de refresco del archivo 10: escribe
en la vista materializada y debe realizarse por separado.

### Repetición manual en DBeaver

Conectar al PostgreSQL del proyecto (puerto predeterminado 5433; credenciales
de `.env`). Ejecutar 1–8 y 11–17, y los bloques 9a–9c y 10a–10c en una sesión
de solo lectura como la descrita arriba. Cerrar con ROLLBACK antes de abrir la
transacción del bloque 10d; ejecutarlo completo hasta su ROLLBACK y comprobar
de nuevo los estados. La llamada `CALL sp_refrescar_ranking_zonas()` se ejecuta
por separado si se requiere refrescar. No lanzar el archivo 10 completo dentro
de la sesión de solo lectura.

La validación registrada se hizo con psycopg contra la instancia Docker;
DBeaver no estaba disponible. No se atribuyen estas pruebas al cliente gráfico.
