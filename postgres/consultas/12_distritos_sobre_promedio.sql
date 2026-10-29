-- Pregunta:
-- ¿Qué distritos tienen más sensores que el promedio y qué porcentaje del total?

-- Criterio:
-- Cada fila representa un distrito cuyo total supera estrictamente el promedio.
-- El promedio incluye TODOS los distritos, incluso los que tienen cero sensores.
-- Cuenta sensores de todos los estados y no depende de que tengan mediciones.
-- Muestra promedio distrital, total de sensores de Madrid y participación (%).
-- Total y promedio se calculan antes de filtrar los distritos sobre el promedio.
-- Sin distritos o sin sensores, el resultado está vacío; no divide entre cero.
-- Ordena por cantidad descendente y luego por nombre e identificador.
-- No requiere parámetros: el catálogo del proyecto corresponde a Madrid.

-- Justificación:
-- La CTE calcula una fila por distrito; LEFT JOIN conserva distritos vacíos.
-- COUNT(s.id_sensor) evita contar filas sin sensor de los LEFT JOIN.
-- La segunda CTE aplica AVG y SUM sobre todos los conteos, sin duplicar sensores.
-- Una subconsulta escalar obtiene el promedio para la comparación en WHERE.
-- NULLIF protege el denominador y 100.0 conserva la precisión del porcentaje.

WITH sensores_por_distrito AS (
    SELECT
        d.id_distrito,
        d.nombre AS distrito,
        COUNT(s.id_sensor) AS cantidad_sensores
    FROM distrito AS d
    LEFT JOIN ubicacion AS u ON u.id_distrito = d.id_distrito
    LEFT JOIN sensor AS s ON s.id_ubicacion = u.id_ubicacion
    GROUP BY d.id_distrito, d.nombre
), resumen_ciudad AS (
    SELECT
        AVG(cantidad_sensores) AS promedio_sensores_por_distrito,
        SUM(cantidad_sensores) AS total_sensores_ciudad
    FROM sensores_por_distrito
)
SELECT
    spd.id_distrito,
    spd.distrito,
    spd.cantidad_sensores,
    rc.promedio_sensores_por_distrito,
    rc.total_sensores_ciudad,
    ROUND(100.0 * spd.cantidad_sensores / NULLIF(rc.total_sensores_ciudad, 0), 2)
        AS participacion_porcentaje
FROM sensores_por_distrito AS spd
CROSS JOIN resumen_ciudad AS rc
WHERE spd.cantidad_sensores > (
    SELECT promedio_sensores_por_distrito
    FROM resumen_ciudad
)
ORDER BY spd.cantidad_sensores DESC, spd.distrito, spd.id_distrito;
