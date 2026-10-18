# Rendimiento en MongoDB

Colección `lecturas`: 3.151.581 documentos; datos: 1092 MB; índices: 129 MB.
Cada tiempo es la mediana de 3 ejecuciones medidas desde Python; el plan y los documentos revisados salen de `explain("executionStats")`.
Los planes completos están en `mongo/rendimiento/planes/`.

| Consulta | Sin índice (ms) | Con índice (ms) | Mejora | Plan sin índice | Plan con índice | Docs revisados sin → con | Resultados |
| --- | --- | --- | --- | --- | --- | --- | --- |
| m1. Lecturas de un sensor en marzo 2025 | 999.1 | 6.0 | 167x | COLLSCAN | IXSCAN | 3.151.581 → 744 | 744 |
| m2. Ultimas 24 lecturas de un sensor de trafico | 972.0 | 1.3 | 723x | COLLSCAN | IXSCAN | 3.151.581 → 24 | 24 |
| m3. Promedio de NO2 por distrito en enero 2025 | 1055.6 | 39.7 | 27x | COLLSCAN | IXSCAN | 3.151.581 → 17.112 | 16 |
| m4. Lecturas a menos de 1 km de Puerta del Sol en julio 2026 | 1740.4 | 228.5 | 8x | COLLSCAN | IXSCAN | 3.151.581 → 135.317 | 19.900 |
| m5. Cantidad de alertas criticas por distrito | 21.8 | 9.3 | 2x | COLLSCAN | IXSCAN | 49.448 → 0 | 12 |

Índices usados: `mongo/rendimiento/indices.js`.
