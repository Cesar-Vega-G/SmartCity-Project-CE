-- Pregunta:
-- ¿Qué sensores no tienen ninguna medición histórica registrada en PostgreSQL?

-- Criterio:
-- Cada fila representa un sensor sin filas asociadas en medicion, con su tipo,
-- estado, ubicación y distrito. Incluye todos los estados y ordena por id_sensor.
-- “Sin actividad” significa sin mediciones válidas cargadas en PostgreSQL;
-- no demuestra ausencia de lecturas crudas en MongoDB.
-- El resultado es representativo después de completar la carga histórica.

-- Justificación:
-- NOT EXISTS comprueba la ausencia de mediciones para cada id_sensor,
-- independientemente del estado y sin restringir fechas. Consultar la tabla
-- padre medicion abarca sus particiones, incluida medicion_default.
-- Los INNER JOIN aportan el contexto del catálogo sin multiplicar sensores.

SELECT
    s.id_sensor,
    s.nombre AS nombre_sensor,
    t.nombre AS tipo_sensor,
    s.estado,
    u.id_ubicacion,
    u.nombre_zona,
    d.nombre AS distrito
FROM sensor AS s
INNER JOIN tipo_sensor AS t ON t.id_tipo = s.id_tipo
INNER JOIN ubicacion AS u ON u.id_ubicacion = s.id_ubicacion
INNER JOIN distrito AS d ON d.id_distrito = u.id_distrito
WHERE NOT EXISTS (
    SELECT 1
    FROM medicion AS m
    WHERE m.id_sensor = s.id_sensor
)
ORDER BY s.id_sensor;
