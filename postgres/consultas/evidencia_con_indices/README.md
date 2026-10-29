# Validación con índices — 42/42 aprobadas

Fecha: 2026-10-26T22:15:37.669714-06:00. Commit del código probado: `dc2b7a11db979c838e5f54c37d5c435562617973`.

Se aplicó el script existente de César, postgres/rendimiento/indices.sql. No se modificaron los SQL ni los datos de mediciones. El procedimiento de estados se revirtió con ROLLBACK y se comprobó cada sensor.

Carga observada: PostgreSQL 16.15, 324 sensores, 21 distritos y 4.664.093 mediciones. Las 21 sentencias SELECT correspondientes a las consultas 1–17 se ejecutaron correctamente.

La consulta 17 devolvió 3.666 filas, usó medicion_2025_id_sensor_fecha_hora_idx y leyó solo medicion_2025. Tiempo observado de EXPLAIN: 2.835 ms; no representa un benchmark controlado.

[Informe, muestras e índices](validacion.json) · [EXPLAIN](consulta_17_explain.json) · [Sección para Luis](../SECCION_PERSONA_C.md)

| Comprobación | Resultado |
| --- | --- |
| Motor PostgreSQL 16 | OK |
| Carga de referencia completa | OK |
| 01: detalle y unicidad de sensores | OK |
| 02: ubicación y unicidad | OK |
| 03: tres estados y total | OK |
| 04: organismos incluidos con cero | OK |
| 05: ubicaciones por identificador | OK |
| 06: año de instalación | OK |
| 07: ausencia de historia y exhaustividad | OK |
| 08: conteos, ceros y ranking denso | OK |
| 09a: ranking materializado coincide con 08 | OK |
| 09a: volumen materializado | OK |
| 09a: agregados de criticidad y contaminación | OK |
| 09a: posiciones por criticidad y actividad | OK |
| 09b: vista frente a tablas originales | OK |
| 09c: organismo, categoría y estados | OK |
| 10a: variables y cantidades frente a 17 | OK |
| 10a: resumen de co | OK |
| 10a: resumen de no2 | OK |
| 10a: resumen de o3 | OK |
| 10a: resumen de pm10 | OK |
| 10a: resumen de pm25 | OK |
| 10b: sensores del distrito | OK |
| 10b: mayúsculas/minúsculas | OK |
| 10c: niveles y las 20 mediciones mayores | OK |
| 10: fronteras de alertas | OK |
| 11: temperatura y promedio ponderado | OK |
| 12: selección y total anterior al filtro | OK |
| 13: umbral estricto | OK |
| 14: historia previa y ausencia en ventana | OK |
| 15: horas, variable y promedio | OK |
| 16: tipos sin duplicados | OK |
| 17: mediciones completas y límites del mes | OK |
| 17: poda a partición 2025 | OK |
| 17: acceso mediante índice | OK |
| 10: error esperado sensor inexistente | OK |
| 10: error esperado distrito inexistente | OK |
| 10: error esperado fechas invertidas | OK |
| 10: error esperado fechas iguales | OK |
| 10: error esperado fecha nula | OK |
| 10d: estados calculados y mantenimiento preservado | OK |
| 10d: rollback restaura cada sensor | OK |

El JSON registra hashes del validador y los SQL. La revisión humana del PR, la incorporación al documento y el ensayo grupal siguen pendientes.
