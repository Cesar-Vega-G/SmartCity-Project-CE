# Rendimiento en PostgreSQL

Tabla `medicion`: 4.664.093 filas; datos: 304 MB; índices: 268 MB.
Cada tiempo es la mediana de 3 ejecuciones de `EXPLAIN (ANALYZE, BUFFERS)`.
Los planes completos están en `postgres/rendimiento/planes/`.

| Consulta | Sin índice (ms) | Con índice (ms) | Mejora | Plan sin índice | Plan con índice | Particiones leídas |
| --- | --- | --- | --- | --- | --- | --- |
| q1. Mediciones de un sensor en marzo 2025 | 30.8 | 0.5 | 57x | Seq Scan | Index Scan | 2025 |
| q2. Ultimas 24 mediciones de NO2 de un sensor | 116.9 | 0.1 | 1146x | Seq Scan | Index Scan, Seq Scan | 2024, 2025, 2026, default |
| q3. Promedio de NO2 por distrito en enero 2025 | 44.7 | 12.7 | 4x | Seq Scan | Bitmap Index Scan, Seq Scan | 2025 |
| q4. Horas con carga de trafico mayor a 80 en julio 2026 | 80.5 | 24.5 | 3x | Seq Scan | Bitmap Index Scan, Seq Scan | 2026 |
| q5. Sensores sin ninguna medicion | 991.1 | 3.4 | 292x | Seq Scan | Index Only Scan, Seq Scan | 2024, 2025, 2026, default |

Índices usados: `postgres/rendimiento/indices.sql`.
