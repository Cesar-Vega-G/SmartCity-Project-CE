-- Pregunta:
-- ¿Cuántos sensores tiene asignados cada organismo responsable?

-- Criterio:
-- Cada fila representa un organismo con su nombre, responsable y cantidad.
-- Incluye todos los estados y organismos sin sensores, cuya cantidad es cero.
-- Ordena por cantidad descendente y nombre del organismo.

-- Justificación:
-- LEFT JOIN parte de organismo para conservar los que no tienen sensores.
-- COUNT(s.id_sensor), en lugar de COUNT(*), no cuenta la fila sin sensor.
-- GROUP BY reúne los sensores de cada organismo sin confundir responsables.

SELECT
    o.id_organismo,
    o.nombre AS nombre_organismo,
    o.responsable,
    COUNT(s.id_sensor) AS cantidad_sensores
FROM organismo AS o
LEFT JOIN sensor AS s ON s.id_organismo = o.id_organismo
GROUP BY o.id_organismo, o.nombre, o.responsable
ORDER BY cantidad_sensores DESC, o.nombre;
