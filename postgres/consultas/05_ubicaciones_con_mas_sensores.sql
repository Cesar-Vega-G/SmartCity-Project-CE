-- Pregunta:
-- ¿Cuáles ubicaciones tienen mayor cantidad de sensores instalados?

-- Criterio:
-- Cada fila representa una ubicación con sensores, su distrito y su cantidad.
-- Incluye todos los estados y todas las ubicaciones con al menos un sensor.
-- Ordena de mayor a menor cantidad y desempata por id_ubicacion, sin LIMIT.

-- Justificación:
-- INNER JOIN incluye solamente ubicaciones con sensores y agrega su distrito.
-- GROUP BY incluye los identificadores para no unir ubicaciones homónimas.
-- COUNT(s.id_sensor) cuenta los sensores instalados en cada punto específico.

SELECT
    u.id_ubicacion,
    u.nombre_zona,
    d.id_distrito,
    d.nombre AS distrito,
    COUNT(s.id_sensor) AS cantidad_sensores
FROM ubicacion AS u
INNER JOIN distrito AS d ON d.id_distrito = u.id_distrito
INNER JOIN sensor AS s ON s.id_ubicacion = u.id_ubicacion
GROUP BY u.id_ubicacion, u.nombre_zona, d.id_distrito, d.nombre
ORDER BY cantidad_sensores DESC, u.id_ubicacion;
