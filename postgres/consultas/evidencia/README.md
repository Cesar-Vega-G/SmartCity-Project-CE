# Evidencia de validación — 26 de octubre de 2026

**Estado: 41/42 comprobaciones aprobadas; acceso por índice pendiente.**

Fuente SQL: `583d64b1d649a7147097648cc27f3f8a7ce6179f`. Motor: `PostgreSQL 16.15 (Debian 16.15-1.pgdg13+2) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit`.

Se ejecutaron los 17 archivos mediante 21 SELECT y una prueba de procedimiento con ROLLBACK. Los tiempos de los SELECT incluyen obtención de filas y no son benchmarks.

[Informe reproducible y muestras](validacion.json) · [EXPLAIN JSON](consulta_17_explain.json) · [Sección técnica](../SECCION_PERSONA_C.md)

| Consulta | Filas |
| --- | --- |
| 01 | 324 |
| 02 | 324 |
| 03 | 3 |
| 04 | 4 |
| 05 | 261 |
| 06 | 22 |
| 07 | 9 |
| 08 | 21 |
| 09a | 21 |
| 09b | 16 |
| 09c | 4 |
| 10a | 5 |
| 10b | 16 |
| 10c | 20 |
| 11 | 21 |
| 12 | 9 |
| 13 | 9 |
| 14 | 14 |
| 15 | 24 |
| 16 | 6 |
| 17 | 3666 |

| Comprobación | Estado | Detalle |
| --- | --- | --- |
| Motor PostgreSQL 16 | OK |  |
| Carga de referencia completa | OK | Referencia del repositorio: 324 sensores y 4.664.093 mediciones; diferencias requieren explicación. |
| 01: detalle y unicidad de sensores | OK |  |
| 02: ubicación y unicidad | OK |  |
| 03: tres estados y total | OK |  |
| 04: organismos incluidos con cero | OK |  |
| 05: ubicaciones por identificador | OK |  |
| 06: año de instalación | OK |  |
| 07: ausencia de historia y exhaustividad | OK |  |
| 08: conteos, ceros y ranking denso | OK |  |
| 09a: ranking materializado coincide con 08 | OK |  |
| 09a: volumen materializado | OK |  |
| 09a: agregados de criticidad y contaminación | OK |  |
| 09a: posiciones por criticidad y actividad | OK |  |
| 09b: vista frente a tablas originales | OK |  |
| 09c: organismo, categoría y estados | OK |  |
| 10a: variables y cantidades frente a 17 | OK |  |
| 10a: resumen de co | OK |  |
| 10a: resumen de no2 | OK |  |
| 10a: resumen de o3 | OK |  |
| 10a: resumen de pm10 | OK |  |
| 10a: resumen de pm25 | OK |  |
| 10b: sensores del distrito | OK |  |
| 10b: mayúsculas/minúsculas | OK |  |
| 10c: niveles y las 20 mediciones mayores | OK |  |
| 10: fronteras de alertas | OK |  |
| 11: temperatura y promedio ponderado | OK |  |
| 12: selección y total anterior al filtro | OK |  |
| 13: umbral estricto | OK |  |
| 14: historia previa y ausencia en ventana | OK |  |
| 15: horas, variable y promedio | OK |  |
| 16: tipos sin duplicados | OK |  |
| 17: mediciones completas y límites del mes | OK |  |
| 17: poda a partición 2025 | OK |  |
| 17: acceso mediante índice | PENDIENTE | No se observó acceso por índice; revisar indices_medicion y plan_17, sin forzar el optimizador. |
| 10: error esperado sensor inexistente | OK |  |
| 10: error esperado distrito inexistente | OK |  |
| 10: error esperado fechas invertidas | OK |  |
| 10: error esperado fechas iguales | OK |  |
| 10: error esperado fecha nula | OK |  |
| 10d: estados calculados y mantenimiento preservado | OK |  |
| 10d: rollback restaura cada sensor | OK |  |

El JSON incluye hashes SHA-256 del validador y de cada SQL ejecutado. El hash del commit identifica el código de consultas existente al iniciar la validación, no el futuro commit que incorpora estos archivos.

No se incluyen credenciales ni volcados completos de datos. No se ejecutó DBeaver ni se fabricaron capturas: las muestras proceden directamente de PostgreSQL mediante psycopg.
