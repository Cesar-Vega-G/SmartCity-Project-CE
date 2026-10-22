-- Pregunta:
-- ¿Qué posición ocupa cada distrito según su cantidad total de sensores?

-- Criterio:
-- Cada fila muestra posición, identificador, nombre, total y activos del distrito.
-- Incluye distritos sin ubicaciones o sin sensores, con cantidades en cero.
-- El total incluye todos los estados; activos cuenta únicamente estado activo.
-- Totales iguales comparten posición y el ranking no deja saltos (1, 1, 2).
-- Ordena por posición, nombre e identificador, sin alterar los empates.

-- Justificación:
-- La CTE separa el conteo por distrito del cálculo posterior del ranking.
-- LEFT JOIN conserva distritos sin sensores; COUNT(s.id_sensor) evita contar
-- filas sin sensor. FILTER calcula activos dentro de la misma agrupación.
-- DENSE_RANK usa únicamente el total descendente para respetar los empates.

WITH sensores_por_distrito AS (
    SELECT
        d.id_distrito,
        d.nombre AS distrito,
        COUNT(s.id_sensor) AS total_sensores,
        COUNT(s.id_sensor) FILTER (WHERE s.estado = 'activo') AS sensores_activos
    FROM distrito AS d
    LEFT JOIN ubicacion AS u ON u.id_distrito = d.id_distrito
    LEFT JOIN sensor AS s ON s.id_ubicacion = u.id_ubicacion
    GROUP BY d.id_distrito, d.nombre
)
SELECT
    DENSE_RANK() OVER (ORDER BY total_sensores DESC) AS posicion,
    id_distrito,
    distrito,
    total_sensores,
    sensores_activos
FROM sensores_por_distrito
ORDER BY posicion, distrito, id_distrito;
