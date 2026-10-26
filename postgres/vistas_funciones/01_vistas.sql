-- Vistas y vista materializada de PostgreSQL
-- Se ejecuta después de cargar los datos (ver README.md de esta carpeta).
-- Se puede volver a correr: primero borra lo que crea.

DROP MATERIALIZED VIEW IF EXISTS mv_ranking_zonas;
DROP VIEW IF EXISTS v_medicion_detalle;
DROP VIEW IF EXISTS v_sensor_detalle;


-- v_sensor_detalle
-- Qué resuelve:
-- Casi todas las consultas repiten los mismos cinco JOIN para pasar de un sensor
-- a su tipo, categoría, organismo, ubicación y distrito. La vista los deja en un
-- solo lugar, así las consultas quedan cortas y todas usan la misma definición.
-- Por qué es una vista normal y no materializada:
-- Son catálogos chicos (324 sensores). Postgres expande la vista dentro de la
-- consulta que la usa, así que siempre muestra el estado actual del sensor.
CREATE VIEW v_sensor_detalle AS
SELECT
    s.id_sensor,
    s.codigo_origen,
    s.nombre AS nombre_sensor,
    s.estado,
    s.fecha_instalacion,
    t.id_tipo,
    t.nombre AS tipo_sensor,
    c.id_categoria,
    c.nombre_categoria AS categoria,
    o.id_organismo,
    o.nombre AS organismo,
    u.id_ubicacion,
    u.nombre_zona,
    u.latitud,
    u.longitud,
    d.id_distrito,
    d.nombre AS distrito
FROM sensor AS s
INNER JOIN tipo_sensor AS t ON t.id_tipo = s.id_tipo
INNER JOIN categoria_sensor AS c ON c.id_categoria = t.id_categoria
INNER JOIN organismo AS o ON o.id_organismo = s.id_organismo
INNER JOIN ubicacion AS u ON u.id_ubicacion = s.id_ubicacion
INNER JOIN distrito AS d ON d.id_distrito = u.id_distrito;


-- v_medicion_detalle
-- Qué resuelve:
-- Cada medición con el nombre de la variable, la unidad, el límite de alerta y el
-- distrito del sensor, más una columna que dice si pasó el límite.
-- Por qué así:
-- Es una vista normal sobre medicion (4.6 millones de filas): no copia datos.
-- Como Postgres la expande, un WHERE sobre fecha_hora o id_sensor sigue podando
-- particiones y usando idx_medicion_sensor_fecha / idx_medicion_variable_fecha.
-- supera_limite usa el mismo criterio que las alertas de Mongo (valor > límite);
-- es NULL cuando la variable no tiene límite (humedad, velocidad, etc.).
CREATE VIEW v_medicion_detalle AS
SELECT
    m.id_medicion,
    m.fecha_hora,
    m.id_sensor,
    sd.tipo_sensor,
    sd.categoria,
    sd.id_distrito,
    sd.distrito,
    v.id_variable,
    v.nombre AS variable,
    v.unidad,
    v.limite_alerta,
    m.valor,
    m.valor > v.limite_alerta AS supera_limite
FROM medicion AS m
INNER JOIN variable AS v ON v.id_variable = m.id_variable
INNER JOIN v_sensor_detalle AS sd ON sd.id_sensor = m.id_sensor;


-- mv_ranking_zonas
-- Qué resuelve:
-- El ranking de zonas (distritos) de la ciudad: cuántos sensores tiene, cuántas
-- mediciones produjo, qué parte de ellas pasó el límite de alerta y cuánto NO2 y
-- PM2.5 registra en promedio. Ordena los distritos de dos formas:
--   posicion_criticidad: por porcentaje de mediciones sobre el límite.
--   posicion_actividad:  por cantidad de mediciones.
-- Por qué es materializada:
-- Para calcularla hay que recorrer toda la tabla medicion (4.6 millones de filas).
-- Ese recorrido tarda segundos y el resultado son solo 21 filas que cambian
-- cuando entra una carga nueva, no a cada rato. Guardarlo hace que el dashboard
-- lo lea al instante. Se actualiza con CALL sp_refrescar_ranking_zonas().
-- Detalles:
-- LEFT JOIN conserva distritos sin sensores o sin mediciones (quedan en cero).
-- Los conteos por distrito se hacen en CTE separadas para que el JOIN con
-- mediciones no multiplique los sensores.
-- pct_sobre_limite solo cuenta mediciones de variables que tienen límite.
-- DENSE_RANK deja empates sin saltos (1, 1, 2).
CREATE MATERIALIZED VIEW mv_ranking_zonas AS
WITH sensores AS (
    SELECT
        d.id_distrito,
        d.nombre AS distrito,
        COUNT(s.id_sensor) AS total_sensores,
        COUNT(s.id_sensor) FILTER (WHERE s.estado = 'activo') AS sensores_activos
    FROM distrito AS d
    LEFT JOIN ubicacion AS u ON u.id_distrito = d.id_distrito
    LEFT JOIN sensor AS s ON s.id_ubicacion = u.id_ubicacion
    GROUP BY d.id_distrito, d.nombre
), mediciones AS (
    SELECT
        u.id_distrito,
        COUNT(*) AS total_mediciones,
        COUNT(*) FILTER (WHERE v.limite_alerta IS NOT NULL) AS mediciones_con_limite,
        COUNT(*) FILTER (WHERE m.valor > v.limite_alerta) AS mediciones_sobre_limite,
        AVG(m.valor) FILTER (WHERE v.nombre = 'no2') AS promedio_no2,
        AVG(m.valor) FILTER (WHERE v.nombre = 'pm25') AS promedio_pm25,
        MAX(m.fecha_hora) AS ultima_medicion
    FROM medicion AS m
    INNER JOIN variable AS v ON v.id_variable = m.id_variable
    INNER JOIN sensor AS s ON s.id_sensor = m.id_sensor
    INNER JOIN ubicacion AS u ON u.id_ubicacion = s.id_ubicacion
    GROUP BY u.id_distrito
), resumen AS (
    SELECT
        se.id_distrito,
        se.distrito,
        se.total_sensores,
        se.sensores_activos,
        COALESCE(me.total_mediciones, 0) AS total_mediciones,
        COALESCE(me.mediciones_sobre_limite, 0) AS mediciones_sobre_limite,
        COALESCE(ROUND(100.0 * me.mediciones_sobre_limite
                       / NULLIF(me.mediciones_con_limite, 0), 3), 0) AS pct_sobre_limite,
        ROUND(me.promedio_no2, 2) AS promedio_no2,
        ROUND(me.promedio_pm25, 2) AS promedio_pm25,
        me.ultima_medicion
    FROM sensores AS se
    LEFT JOIN mediciones AS me ON me.id_distrito = se.id_distrito
)
SELECT
    DENSE_RANK() OVER (ORDER BY pct_sobre_limite DESC) AS posicion_criticidad,
    DENSE_RANK() OVER (ORDER BY total_mediciones DESC) AS posicion_actividad,
    resumen.*,
    now() AS actualizado_en
FROM resumen;

-- Índice único: lo exige REFRESH MATERIALIZED VIEW CONCURRENTLY, que deja leer
-- la vista mientras se recalcula.
CREATE UNIQUE INDEX idx_mv_ranking_zonas_distrito ON mv_ranking_zonas (id_distrito);
