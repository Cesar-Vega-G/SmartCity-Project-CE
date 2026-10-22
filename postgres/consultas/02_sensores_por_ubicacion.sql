-- Pregunta:
-- ¿Qué sensores están instalados en cada ubicación y a qué distrito pertenecen?

-- Criterio:
-- Cada fila representa un sensor con su estado, ubicación y distrito.
-- Incluye todos los estados y únicamente ubicaciones con sensores instalados.
-- Ordena por distrito, nombre e identificador de ubicación y luego por sensor.

-- Justificación:
-- Los INNER JOIN siguen las llaves foráneas sensor -> ubicacion -> distrito.
-- Estas relaciones obligatorias conservan una fila por sensor.
-- id_ubicacion permite distinguir puntos que comparten el mismo nombre_zona.

SELECT
    s.id_sensor,
    s.nombre AS nombre_sensor,
    s.estado,
    u.id_ubicacion,
    u.nombre_zona,
    d.nombre AS distrito
FROM sensor AS s
INNER JOIN ubicacion AS u ON u.id_ubicacion = s.id_ubicacion
INNER JOIN distrito AS d ON d.id_distrito = u.id_distrito
ORDER BY d.nombre, u.nombre_zona, u.id_ubicacion, s.id_sensor;
