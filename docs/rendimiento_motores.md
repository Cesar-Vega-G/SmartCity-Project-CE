# Rendimiento de los 4 motores

Medido el 15/11/2026 14:14 con `rendimiento/medir_motores.py`. Mediana de 3 ejecuciones, en ms.

| Consulta | PostgreSQL | MongoDB | Spark | MapReduce |
| --- | --- | --- | --- | --- |
| Lecturas de S-00002 en marzo 2025 (busqueda puntual) | 6.6 | 6.9 | 396.0 | 39285.6 |
| NO2 promedio por distrito, enero 2025 (agregacion) | 17.3 | 45.6 | 503.1 | 39630.1 |
| Lecturas por tipo de sensor y anio (recorre todo) | 977.9 | 2856.0 | 469.1 | 45179.1 |

Resultados (para comprobar que responden lo mismo):

| Consulta | PostgreSQL | MongoDB | Spark | MapReduce |
| --- | --- | --- | --- | --- |
| c1 | 3666 filas | 744 filas | 744 filas | 744 filas |
| c2 | 16 distritos, prom. 31.95 | 16 distritos, prom. 31.95 | 16 distritos, prom. 31.95 | 16 distritos, prom. 31.95 |
| c3 | 11 grupos, 4664093 total | 11 grupos, 3151581 total | 11 grupos, 3151581 total | 11 grupos, 3151581 total |

Spark completo (arrancar + 9 consultas + cerrar): 16125 ms. El tiempo de Spark de la tabla es solo la consulta; el de MapReduce incluye arrancar cada trabajo.
