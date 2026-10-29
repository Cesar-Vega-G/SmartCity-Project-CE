-- Pregunta:
-- ¿Qué horas del día tienen mayor carga promedio de tráfico en un período?

-- Criterio:
-- Parámetros editables: variable 'carga'; julio de 2026, con inicio incluido
-- (2026-07-01) y fin excluido (2026-08-01).
-- Cada fila representa una hora del día (0 a 23) con mediciones disponibles,
-- reuniendo todos los días y sensores con datos de carga del período.
-- Muestra unidad del catálogo, promedio y cantidad de mediciones horarias.
-- Cada medición pesa lo mismo; no imputa horas faltantes ni filtra por estado.
-- Ordena por promedio descendente y hora ascendente, sin LIMIT.
-- Usa la hora almacenada en fecha_hora, sin aplicar conversión de zona horaria.

-- Justificación:
-- WHERE selecciona únicamente carga antes de AVG para no mezclar variables.
-- El rango directo sobre fecha_hora permite podar particiones y puede usar
-- el índice por variable y fecha. EXTRACT se usa solamente para agrupar la hora.
-- GROUP BY produce como máximo 24 filas y COUNT informa su cantidad de datos.

SELECT
    EXTRACT(HOUR FROM m.fecha_hora)::integer AS hora_del_dia,
    v.unidad,
    AVG(m.valor) AS carga_promedio,
    COUNT(*) AS cantidad_mediciones
FROM medicion AS m
INNER JOIN variable AS v ON v.id_variable = m.id_variable
WHERE v.nombre = 'carga'
  AND m.fecha_hora >= TIMESTAMP '2026-07-01 00:00:00'
  AND m.fecha_hora < TIMESTAMP '2026-08-01 00:00:00'
GROUP BY EXTRACT(HOUR FROM m.fecha_hora)::integer, v.unidad
ORDER BY carga_promedio DESC, hora_del_dia;
