-- Consulta obligatoria 9: consulta utilizando vistas
-- Requiere haber ejecutado antes el archivo de vistas.
-- Son tres consultas independientes; se pueden ejecutar una por una en DBeaver
-- poniendo el cursor dentro de cada una y presionando Ctrl+Enter.


-- 9a. Ranking de zonas (vista materializada)
-- Pregunta:
-- ¿Qué distritos son los más críticos según la proporción de mediciones que pasan
-- el límite de alerta, y cuánta actividad tienen?
-- Justificación:
-- Lee la vista materializada, que ya tiene hecho el cálculo sobre los 4,6 millones
-- de mediciones. Por eso responde al instante aunque la pregunta abarque toda la
-- historia. La última columna dice cuándo se hizo el cálculo.
SELECT
    posicion_criticidad,
    distrito,
    pct_sobre_limite,
    mediciones_sobre_limite,
    total_mediciones,
    posicion_actividad,
    posicion_sensores,
    total_sensores,
    sensores_activos,
    promedio_no2,
    promedio_pm25,
    actualizado_en
FROM mv_ranking_zonas
-- Dentro de un empate de posición, el nombre del distrito decide el orden para que
-- el resultado salga siempre igual.
ORDER BY posicion_criticidad, distrito;


-- 9b. ¿Cuál zona presenta mayor contaminación? (vista normal)
-- Pregunta:
-- En enero de 2025, ¿cuál es el promedio de NO2 por distrito y cuántas horas pasó
-- el límite? Es una de las preguntas de ejemplo del enunciado.
-- Criterio:
-- Solo aparecen distritos con sensores de calidad del aire, porque son los únicos
-- que miden NO2. La fecha de inicio se incluye y la de fin se excluye.
-- Justificación:
-- La vista de mediciones ya trae la variable, el distrito y si el valor pasó el
-- límite, así que esta consulta solo filtra y agrupa. Como la vista se expande
-- dentro de la consulta, el filtro por fecha solo lee la partición de 2025 y puede
-- usar el índice por variable y fecha.
-- Debe dar los mismos promedios que la consulta q3 de rendimiento de Cesar, que
-- responde lo mismo escribiendo las uniones a mano.
SELECT
    distrito,
    COUNT(*) AS horas_medidas,
    ROUND(AVG(valor), 2) AS promedio_no2,
    MAX(valor) AS maximo_no2,
    -- Cuenta solo las filas donde el valor pasó el límite.
    COUNT(*) FILTER (WHERE supera_limite) AS horas_sobre_limite
FROM v_medicion_detalle
WHERE variable = 'no2'
  AND fecha_hora >= TIMESTAMP '2025-01-01 00:00:00'
  AND fecha_hora < TIMESTAMP '2025-02-01 00:00:00'
GROUP BY distrito
ORDER BY promedio_no2 DESC, distrito;


-- 9c. Sensores por organismo y categoría (vista normal)
-- Pregunta:
-- ¿Cuántos sensores tiene cada organismo en cada categoría y en qué estado están?
-- Justificación:
-- La vista de sensores evita escribir las uniones de sensor, tipo, categoría y
-- organismo. FILTER cuenta cada estado dentro de la misma agrupación, así se
-- obtienen las tres columnas de estado en una sola pasada.
SELECT
    organismo,
    categoria,
    COUNT(*) AS total_sensores,
    COUNT(*) FILTER (WHERE estado = 'activo') AS activos,
    COUNT(*) FILTER (WHERE estado = 'inactivo') AS inactivos,
    COUNT(*) FILTER (WHERE estado = 'mantenimiento') AS en_mantenimiento
FROM v_sensor_detalle
GROUP BY organismo, categoria
ORDER BY organismo, categoria;
