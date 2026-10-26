-- Consulta obligatoria 9: consulta utilizando vistas
-- Requiere 01_vistas.sql. Son tres consultas independientes; se pueden ejecutar
-- una por una en DBeaver.


-- 9a. Ranking de zonas (vista materializada)
-- Pregunta:
-- ¿Qué distritos son los más críticos según la proporción de mediciones que
-- pasan el límite de alerta, y cuánta actividad tienen?
-- Justificación:
-- Lee mv_ranking_zonas, que ya tiene el cálculo hecho sobre los 4.6 millones de
-- mediciones; por eso responde al instante aunque la pregunta recorra toda la
-- historia. actualizado_en muestra de cuándo es el cálculo.
SELECT
    posicion_criticidad,
    distrito,
    pct_sobre_limite,
    mediciones_sobre_limite,
    total_mediciones,
    posicion_actividad,
    total_sensores,
    sensores_activos,
    promedio_no2,
    promedio_pm25,
    actualizado_en
FROM mv_ranking_zonas
ORDER BY posicion_criticidad, distrito;


-- 9b. ¿Cuál zona presenta mayor contaminación? (vista normal)
-- Pregunta:
-- En enero de 2025, ¿cuál es el promedio de NO2 por distrito y cuántas horas
-- pasó el límite? (pregunta de ejemplo del enunciado)
-- Criterio:
-- Solo distritos con sensores de calidad del aire. Inicio incluido, fin excluido.
-- Justificación:
-- v_medicion_detalle ya trae variable, distrito y si pasó el límite, así que la
-- consulta solo filtra y agrupa. Como la vista se expande dentro de la consulta,
-- el filtro por fecha solo lee la partición medicion_2025 y puede usar
-- idx_medicion_variable_fecha.
SELECT
    distrito,
    COUNT(*) AS horas_medidas,
    ROUND(AVG(valor), 2) AS promedio_no2,
    MAX(valor) AS maximo_no2,
    COUNT(*) FILTER (WHERE supera_limite) AS horas_sobre_limite
FROM v_medicion_detalle
WHERE variable = 'no2'
  AND fecha_hora >= TIMESTAMP '2025-01-01 00:00:00'
  AND fecha_hora < TIMESTAMP '2025-02-01 00:00:00'
GROUP BY distrito
ORDER BY promedio_no2 DESC, distrito;


-- 9c. Sensores por categoría y organismo (vista normal)
-- Pregunta:
-- ¿Cuántos sensores tiene cada organismo en cada categoría y en qué estado están?
-- Justificación:
-- v_sensor_detalle evita escribir los JOIN de sensor, tipo, categoría y
-- organismo. FILTER cuenta cada estado en la misma agrupación.
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
