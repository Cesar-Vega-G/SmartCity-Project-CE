-- Pregunta:
-- ¿Qué sensores con historia dejaron de registrar desde una fecha de corte?

-- Criterio:
-- Parámetros editables: corte 2026-07-15 incluido y cierre 2026-09-01 excluido.
-- El corte está dentro del dataset, que termina el 31 de agosto de 2026.
-- Cada fila representa un sensor con alguna medición anterior al corte y ninguna
-- desde el corte hasta el cierre. Una lectura exactamente en el corte lo excluye.
-- Muestra tipo, estado, distrito y última fecha registrada antes del cierre.
-- Incluye todos los estados; el estado del catálogo no decide la selección.
-- Excluye sensores sin historia, que corresponden a la consulta 7.
-- La ausencia de registros válidos en PostgreSQL no demuestra una falla física
-- ni ausencia de lecturas crudas en MongoDB. Requiere la carga histórica completa.
-- Ordena por última medición ascendente e identificador del sensor.

-- Justificación:
-- La CTE obtiene MAX(fecha_hora) por sensor antes del cierre, sin mezclar valores
-- de variables: aquí interesa cualquier registro de actividad del sensor.
-- INNER JOIN excluye sensores que nunca registraron y aporta el contexto.
-- Comparar la última fecha con el corte implica que no hay lecturas posteriores
-- dentro del período observado; las posteriores al cierre no participan.

WITH ultima_actividad AS (
    SELECT
        m.id_sensor,
        MAX(m.fecha_hora) AS ultima_medicion
    FROM medicion AS m
    WHERE m.fecha_hora < TIMESTAMP '2026-09-01 00:00:00'
    GROUP BY m.id_sensor
)
SELECT
    s.id_sensor,
    s.nombre AS nombre_sensor,
    t.nombre AS tipo_sensor,
    s.estado,
    d.id_distrito,
    d.nombre AS distrito,
    ua.ultima_medicion
FROM ultima_actividad AS ua
INNER JOIN sensor AS s ON s.id_sensor = ua.id_sensor
INNER JOIN tipo_sensor AS t ON t.id_tipo = s.id_tipo
INNER JOIN ubicacion AS u ON u.id_ubicacion = s.id_ubicacion
INNER JOIN distrito AS d ON d.id_distrito = u.id_distrito
WHERE ua.ultima_medicion < TIMESTAMP '2026-07-15 00:00:00'
ORDER BY ua.ultima_medicion, s.id_sensor;
