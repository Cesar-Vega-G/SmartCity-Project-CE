# Verificar desde Compass

Estas comprobaciones se hacen sobre la carga del proyecto, sin modificarla.
Los resultados esperados corresponden al dataset y fechas originales. Una carga
distinta puede cambiar las cantidades; registrar la diferencia, no inventar resultados.

## Conexion, volumen y modelo

Abrir smartcity y comprobar sus cuatro colecciones. Para un conteo exacto, pegar
este pipeline en Aggregations de cada coleccion y pulsar Run:

```javascript
[{ $count: "documentos" }]
```

La carga examinada tenia lecturas: 3.151.581; alertas: 49.448; eventos: 8.936;
incidentes: 4.000. El total supera 500.000. Una coleccion vacia devuelve `[]`.
En Documents inspeccionar timestamp (fecha), id_sensor, tipo, ubicacion.distrito,
medicion, valido e invalidos. En incidentes la fecha es fecha_reporte.
En Indexes comprobar los indices disponibles; no ejecutar el benchmark para crearlos.

## Consultas y resultados

Ejecutar los quince archivos en las colecciones indicadas en README. Usar Run,
no el numero de documentos de Preview. Comparar con `compass/validacion.json`:

| Consulta | Filas esperadas |
|---|---:|
| 01 | 100 |
| 02 | 100 |
| 03 | 15 |
| 04 | 90 |
| 05 | 32 |
| 06 | 246 |
| 07 | 15 |
| 08 | 7 |
| 09 | 312 |
| 10 | 100 |
| 11 | 21 |
| 12 | 136 |
| 13 | 16 |
| 14 | 651 |
| 15 | 20 |

Los detalles limitados a 100 no indican el total de coincidencias. La 13 debe
mostrar Carabanchel con promedio NO2 aproximado 24,9436 y 1.471 muestras; la 11,
Arganzuela con temperatura aproximada 29,3571 y 744 muestras. No comparar solo filas:
revisar grupos, unidades, cantidades y valores contra las muestras historicas.

En una copia sin guardar de la 01, cambiar id_sensor a un valor inexistente y
comprobar `[]`. En la 02, sustituir el filtro de fechas por `$gte` y `$lt` con la
misma fecha: debe devolver `[]`. Restaurar el archivo original al terminar.
Estas comprobaciones manuales no sustituyen la antigua suite de casos controlados.

## CRUD e indices

Pegar `crud.js` completo en Open MongoDB Shell dos veces: cada ejecucion debe
mostrar siete OK, limpieza y aprobado true. No usa las colecciones de smartcity.

Usar Explain en un pipeline por sensor/fecha (01) y en uno por tipo/fecha (13).
Registrar el indice elegido, documentos examinados y resultados; no asumir IXSCAN.
Para alertas criticas por distrito, explicar esta consulta en alertas:

```javascript
[
  { $match: { nivel: "critica", "ubicacion.distrito": "Centro",
      timestamp: { $gte: ISODate("2026-07-01T00:00:00Z"),
                   $lt: ISODate("2026-08-01T00:00:00Z") } } },
  { $count: "alertas" }
]
```

Los planes anteriores estan en evidencia/validacion.json; los benchmarks de Cesar
en ../../docs/rendimiento_mongo.md. No son mediciones nuevas de Compass.

## Registrar una nueva revision

Anotar fecha, version de Compass y MongoDB (esta ultima se obtiene con `db.version()`
en la shell integrada), coleccion, archivo, filtros, filas y comprobaciones realizadas.
Adjuntar una muestra pequena o captura, sin exportar el dataset ni credenciales.
Marcar cada consulta solo despues de ejecutarla. Conservar los informes anteriores
como historicos. Al editar un pipeline, su SHA-256 anterior deja de respaldarlo.

El cambio a Compass mantuvo los quince pipelines sin alteraciones respecto a la
validacion de equivalencia 15/15. La suite original (83 comprobaciones), la prueba
sin indices y el ensayo limpio pertenecen al commit d2f5884. Sus ejecutores ya no
forman parte del flujo actual y pueden consultarse en el historial Git.

## Revision de la simplificacion — 28 de octubre de 2026

- Los quince archivos conservaron su SHA-256 respecto a compass/validacion.json.
  No fue necesario volver a ejecutar las agregaciones sin cambios.
- El nuevo crud.js se ejecuto dos veces mediante mongosh en el contenedor local:
  siete operaciones aprobadas en cada corrida y ambas bases temporales eliminadas.
  Esta comprobacion del script no se presenta como una prueba nueva de la interfaz.
- Se verificaron los enlaces locales de la documentacion y la ausencia de
  instrucciones que dependan de los ejecutores retirados.
