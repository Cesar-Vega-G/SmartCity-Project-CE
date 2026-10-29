-- Pregunta:
-- ¿Cuántos sensores fueron instalados en cada año?

-- Criterio:
-- Cada fila representa un año con instalaciones y su cantidad de sensores.
-- Incluye todos los estados y todos los años registrados, anteriores o no a 2024.
-- No agrega años sin instalaciones; ordena cronológicamente de menor a mayor.

-- Justificación:
-- EXTRACT obtiene el año de fecha_instalacion y el cast lo presenta como entero.
-- GROUP BY reúne las instalaciones del mismo año; COUNT cuenta sus sensores.
-- No se consulta medicion porque instalación y actividad son hechos distintos.

SELECT
    EXTRACT(YEAR FROM s.fecha_instalacion)::integer AS anio,
    COUNT(s.id_sensor) AS cantidad_sensores
FROM sensor AS s
GROUP BY EXTRACT(YEAR FROM s.fecha_instalacion)::integer
ORDER BY anio;
