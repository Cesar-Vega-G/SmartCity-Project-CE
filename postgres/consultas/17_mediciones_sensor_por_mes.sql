-- Pregunta:
-- ¿Qué mediciones registró un sensor durante un mes?

-- Criterio:
-- Parámetros editables: sensor 'S-00002'; marzo de 2025, con inicio incluido
-- (2025-03-01) y fin excluido (2025-04-01).
-- Cada fila representa una medición, con fecha, variable, unidad y valor.
-- No agrega ni mezcla valores de variables diferentes; incluye todos los estados.
-- Ordena por fecha, identificador de variable y de medición para resolver empates.

-- Justificación:
-- WHERE combina igualdad por id_sensor y rango directo por fecha_hora, compatible
-- con el índice existente idx_medicion_sensor_fecha (id_sensor, fecha_hora).
-- El rango mensual permite podar las particiones ajenas a 2025.
-- INNER JOIN agrega el nombre y la unidad de cada variable.
-- EXPLAIN (ANALYZE, BUFFERS) permite comprobar el índice y la partición usados;
-- el optimizador decide el acceso según estadísticas, selectividad y volumen.

SELECT
    m.id_medicion,
    m.id_sensor,
    m.fecha_hora,
    v.id_variable,
    v.nombre AS variable,
    v.unidad,
    m.valor
FROM medicion AS m
INNER JOIN variable AS v ON v.id_variable = m.id_variable
WHERE m.id_sensor = 'S-00002'::varchar
  AND m.fecha_hora >= TIMESTAMP '2025-03-01 00:00:00'
  AND m.fecha_hora < TIMESTAMP '2025-04-01 00:00:00'
ORDER BY m.fecha_hora, v.id_variable, m.id_medicion;
