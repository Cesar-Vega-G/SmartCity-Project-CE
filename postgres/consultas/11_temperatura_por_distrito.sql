-- Pregunta:
-- ¿Cuál es la temperatura promedio, mínima y máxima por distrito en un período?

-- Criterio:
-- Parámetros editables: variable 'temperatura'; julio de 2026, con inicio
-- incluido (2026-07-01) y fin excluido (2026-08-01).
-- Cada fila representa un distrito con mediciones de temperatura disponibles.
-- Muestra la unidad del catálogo y la cantidad de mediciones horarias utilizadas.
-- El promedio pondera cada medición disponible por igual, sin imputar faltantes.
-- Incluye todos los estados; ordena por promedio descendente y por distrito.
-- Los valores se conservan sin redondear para respetar mínimo <= promedio <= máximo.

-- Justificación:
-- INNER JOIN sigue medicion -> sensor -> ubicacion -> distrito y agrega variable.
-- WHERE selecciona una sola variable antes de AVG, MIN y MAX para no mezclar
-- temperatura, ruido o contaminación. El rango directo sobre fecha_hora permite
-- la poda de particiones y puede aprovechar el índice por variable y fecha.
-- GROUP BY usa el identificador del distrito para separar nombres repetidos.

SELECT
    d.id_distrito,
    d.nombre AS distrito,
    v.unidad,
    COUNT(*) AS cantidad_mediciones,
    AVG(m.valor) AS temperatura_promedio,
    MIN(m.valor) AS temperatura_minima,
    MAX(m.valor) AS temperatura_maxima
FROM medicion AS m
INNER JOIN variable AS v ON v.id_variable = m.id_variable
INNER JOIN sensor AS s ON s.id_sensor = m.id_sensor
INNER JOIN ubicacion AS u ON u.id_ubicacion = s.id_ubicacion
INNER JOIN distrito AS d ON d.id_distrito = u.id_distrito
WHERE v.nombre = 'temperatura'
  AND m.fecha_hora >= TIMESTAMP '2026-07-01 00:00:00'
  AND m.fecha_hora < TIMESTAMP '2026-08-01 00:00:00'
GROUP BY d.id_distrito, d.nombre, v.unidad
ORDER BY temperatura_promedio DESC, d.nombre, d.id_distrito;
