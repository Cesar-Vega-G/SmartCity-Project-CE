# Evidencia de MongoDB - 27 de octubre de 2026

**83/83 comprobaciones aprobadas** en MongoDB 7.0.45: 44 controladas y 39 sobre la carga completa.
Las quince consultas ejecutadas coinciden con referencias independientes. Las pruebas del motor limpio tambien aprobaron 44/44. Adicionalmente, los 17 archivos numerados se ejecutaron individualmente y sus salidas coincidieron con la validacion.

## Archivos

- [Validacion final, parametros, muestras, planes y hashes](validacion.json).
- [Ejecucion independiente de los archivos numerados](archivos_individuales.json).
- [Prueba aprobada antes de aplicar indices](../evidencia_sin_indices/validacion.json).
- [Prueba en MongoDB efimero limpio](../evidencia_limpia/validacion.json) y [entorno](../evidencia_limpia/entorno.json).

No se ejecutaron los scripts masivos de carga ni el benchmark que elimina indices. Se aplico sin cambios el script existente de Cesar despues de registrar el estado inicial.

## Volumen real

| Coleccion | Documentos |
|---|---:|
| lecturas | 3.151.581 |
| eventos | 8.936 |
| alertas | 49.448 |
| incidentes | 4.000 |

Julio de 2026: **661.491 lecturas**. Se uso el intervalo `[2026-07-01T00:00:00Z, 2026-08-01T00:00:00Z)`.

## Accesos antes y despues

Las tres parejas usan exactamente el mismo descriptor de consulta y los mismos datos. Los hashes de documentos coinciden entre ambas ejecuciones.

| Consulta explicada | Documentos examinados sin indice | Con indice | Indice elegido |
|---|---:|---:|---|
| Lecturas de un sensor | 3,151,581 | 744 | idx_sensor_timestamp |
| Promedio por zona y variable | 3,151,581 | 17,112 | idx_tipo_timestamp |
| Alertas por zona | 49,448 | 4,996 | idx_nivel_distrito |

Los tiempos y planes completos estan en JSON. Son observaciones de una ejecucion, no medianas ni una comparacion controlada de velocidad. El benchmark original de Cesar permanece en [docs/rendimiento_mongo.md](../../../docs/rendimiento_mongo.md).

`duracion_cursor_ms` corresponde al cursor de explain; no se debe presentar como duracion total de todos los pasos de una agregacion. `max_filas_etapa` es el maximo observado entre etapas, no el numero de filas del resultado final. En la evidencia historica sin indices esos campos se llamaban `duracion_ms` y `resultados_plan`.

La consulta por sensor conserva una etapa SORT para desempatar por _id: el indice existente no incluye ese campo. Aun asi reduce la lectura de documentos. Las agregaciones amplias pueden seguir recorriendo gran parte del conjunto; no se forzo el optimizador.

## Resultados de las quince consultas

| N.º | Filas devueltas | Duracion observada (ms) |
|---|---:|---:|
| 1 | 100 | 6 |
| 2 | 100 | 2025 |
| 3 | 15 | 8372 |
| 4 | 90 | 9 |
| 5 | 32 | 38 |
| 6 | 246 | 8368 |
| 7 | 15 | 8344 |
| 8 | 7 | 4 |
| 9 | 312 | 1953 |
| 10 | 100 | 1324 |
| 11 | 21 | 1812 |
| 12 | 136 | 42 |
| 13 | 16 | 142 |
| 14 | 651 | 158 |
| 15 | 20 | 3 |

Las consultas de detalle tienen limite 100; esos valores no representan el total de coincidencias. Las agregaciones no aplican ese limite.

Ejemplos interpretables de julio: temperatura promedio en Arganzuela, 29,3571 C sobre 744 muestras; ranking de NO2 encabezado por Carabanchel, 24,9436 ug/m3 sobre 1.471 valores validos. Son resultados del dataset y del periodo elegido, no conclusiones sanitarias ni causales.

## Integridad y reproduccion

- dbHash e inventario de indices iguales antes/despues de la validacion final.
- Hashes documentales iguales tambien entre la prueba sin indices y la final.
- Las bases temporales del CRUD y fixtures se eliminan al terminar.
- La evidencia final incluye SHA-256 de los archivos de codigo que se validaron.
- El ensayo limpio valida scripts y fixtures en un motor nuevo, no la regeneracion integral del stack.
- Compass tiene instrucciones de ejecucion; esta evidencia automatizada se obtuvo con mongosh.

## Checklist de Persona D

- [x] CRUD completo y repetible.
- [x] Consultas obligatorias 1-10.
- [x] Aggregation Framework, filtros, operadores, proyecciones y ordenamiento.
- [x] Preguntas complementarias y campos dinamicos.
- [x] Prueba sobre mas de 500.000 documentos.
- [x] Tres explain con uso de indices confirmado.
- [x] Documentacion tecnica, cobertura y guion de defensa preparados.
- [ ] Integrar la seccion y el diagrama al documento de B; revisar en grupo.
- [ ] Reproducir el stack y la carga completa desde cero con Cesar.
- [ ] Ensayo conjunto y entrega del avance.
- [ ] Abrir PR y obtener revision: pospuesto por instruccion del usuario.
