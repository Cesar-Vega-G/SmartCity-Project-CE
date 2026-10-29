-- Pregunta:
-- ¿Cuántos sensores están activos, inactivos o en mantenimiento?

-- Criterio:
-- Devuelve exactamente tres filas, en el orden activo, inactivo, mantenimiento.
-- Un estado sin sensores muestra cero, incluso cuando sensor está vacía.

-- Justificación:
-- VALUES define todos los estados permitidos y su orden de presentación.
-- LEFT JOIN conserva los estados sin coincidencias; COUNT(s.id_sensor) cuenta
-- solamente sensores existentes y evita contar la fila sin sensor del JOIN.

SELECT
    e.estado,
    COUNT(s.id_sensor) AS cantidad_sensores
FROM (VALUES
    ('activo', 1),
    ('inactivo', 2),
    ('mantenimiento', 3)
) AS e(estado, orden)
LEFT JOIN sensor AS s ON s.estado = e.estado
GROUP BY e.estado, e.orden
ORDER BY e.orden;
