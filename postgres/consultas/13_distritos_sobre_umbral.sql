-- Pregunta:
-- ¿Qué distritos superan un umbral de sensores instalados?

-- Criterio:
-- Parámetro editable: umbral de 15 sensores, con comparación estricta (>).
-- Cada fila muestra identificador, nombre y cantidad de sensores del distrito.
-- Incluye todos los estados; un distrito con exactamente 15 queda excluido.
-- Ordena por cantidad descendente, nombre e identificador del distrito.

-- Justificación:
-- LEFT JOIN conserva todos los distritos para el conteo, incluso los vacíos.
-- COUNT(s.id_sensor) evita contar las filas sin sensor de los LEFT JOIN.
-- GROUP BY reúne los sensores de cada distrito sin confundir nombres iguales.
-- HAVING filtra el conteo después de agrupar, a diferencia de WHERE.

SELECT
    d.id_distrito,
    d.nombre AS distrito,
    COUNT(s.id_sensor) AS cantidad_sensores
FROM distrito AS d
LEFT JOIN ubicacion AS u ON u.id_distrito = d.id_distrito
LEFT JOIN sensor AS s ON s.id_ubicacion = u.id_ubicacion
GROUP BY d.id_distrito, d.nombre
HAVING COUNT(s.id_sensor) > 15::integer
ORDER BY cantidad_sensores DESC, d.nombre, d.id_distrito;
