-- Vistas y vista materializada de PostgreSQL
-- Se ejecuta después de cargar los datos (ver el README de esta carpeta).
-- Se puede volver a correr las veces que haga falta porque primero borra lo que crea.

-- Se borra en orden inverso a la creación: la vista de mediciones usa la vista
-- de sensores, así que la de sensores no se puede borrar mientras exista la otra.
DROP MATERIALIZED VIEW IF EXISTS mv_ranking_zonas;
DROP VIEW IF EXISTS v_medicion_detalle;
DROP VIEW IF EXISTS v_sensor_detalle;


-- Vista de sensores con todo su contexto
-- Qué resuelve:
-- Casi todas las consultas repiten las mismas cinco uniones para pasar de un sensor
-- a su tipo, su categoría, su organismo, su ubicación y su distrito. La vista las
-- deja escritas en un solo lugar, así las consultas quedan cortas y todas usan la
-- misma definición.
-- Por qué es una vista normal y no materializada:
-- Son catálogos pequeños (324 sensores). Postgres expande la vista dentro de la
-- consulta que la usa, así que siempre muestra el estado actual de cada sensor.
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
-- Todas son uniones internas porque las llaves foráneas del sensor son obligatorias:
-- todo sensor tiene tipo, organismo y ubicación, así que ninguno se pierde.
INNER JOIN tipo_sensor AS t ON t.id_tipo = s.id_tipo
INNER JOIN categoria_sensor AS c ON c.id_categoria = t.id_categoria
INNER JOIN organismo AS o ON o.id_organismo = s.id_organismo
INNER JOIN ubicacion AS u ON u.id_ubicacion = s.id_ubicacion
INNER JOIN distrito AS d ON d.id_distrito = u.id_distrito;


-- Vista de mediciones con su variable y su distrito
-- Qué resuelve:
-- Cada medición junto con el nombre de la variable, su unidad, su límite de alerta
-- y el distrito del sensor, más una columna que dice si el valor pasó el límite.
-- Por qué así:
-- Es una vista normal sobre la tabla de mediciones (4,6 millones de filas), así que
-- no copia datos. Como Postgres la expande dentro de cada consulta, un filtro por
-- fecha o por sensor sigue leyendo solo las particiones necesarias y sigue usando
-- los índices que creó Cesar sobre la tabla de mediciones.
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
    -- Mismo criterio que las alertas de Mongo: hay alerta cuando el valor supera el
    -- límite. Si la variable no tiene límite (humedad, velocidad) el resultado queda
    -- vacío (NULL) en vez de falso, porque no tiene sentido decir que no lo pasó.
    m.valor > v.limite_alerta AS supera_limite
FROM medicion AS m
INNER JOIN variable AS v ON v.id_variable = m.id_variable
-- Se reutiliza la vista anterior para no repetir las cinco uniones del sensor.
INNER JOIN v_sensor_detalle AS sd ON sd.id_sensor = m.id_sensor;


-- Ranking de zonas (vista materializada)
-- Qué resuelve:
-- Una fila por distrito con cuántos sensores tiene, cuántas mediciones produjo, qué
-- parte de ellas pasó el límite de alerta y cuánto NO2 y PM2.5 registra en promedio.
-- Ordena los distritos de tres maneras:
--   posición por sensores: por cantidad total de sensores, con el mismo criterio
--   que la consulta 8 de Sebastián, para que los dos resultados coincidan.
--   posición de criticidad: por porcentaje de mediciones sobre el límite.
--   posición de actividad: por cantidad de mediciones.
-- Por qué es materializada:
-- Para calcularla hay que recorrer toda la tabla de mediciones. Ese recorrido tarda
-- segundos y el resultado son solo 21 filas que cambian únicamente cuando entra una
-- carga nueva. Guardar el resultado permite que el dashboard lo lea al instante.
-- Se recalcula con el procedimiento de refresco que está en el archivo de funciones.
CREATE MATERIALIZED VIEW mv_ranking_zonas AS

-- Paso 1: sensores por distrito.
-- Las uniones externas (LEFT JOIN) conservan los distritos que no tienen ubicaciones
-- ni sensores; para esos el conteo da cero. Se cuentan los identificadores de sensor
-- y no las filas porque un distrito vacío igual produce una fila, con el sensor vacío.
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
),

-- Paso 2: mediciones por distrito.
-- Va en un paso aparte del anterior porque si se unieran sensores y mediciones en
-- la misma consulta, cada sensor se repetiría una vez por cada medición y los
-- conteos de sensores saldrían inflados.
-- FILTER permite sacar varios conteos y promedios distintos en una sola pasada por
-- la tabla, en vez de recorrerla una vez por cada número.
mediciones AS (
    SELECT
        u.id_distrito,
        COUNT(*) AS total_mediciones,
        -- Solo estas cuentan para el porcentaje: una medición de humedad no puede
        -- pasar un límite que no existe.
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
),

-- Paso 3: juntar los dos pasos anteriores, una fila por distrito.
-- Se parte de los sensores con LEFT JOIN para que aparezcan los 21 distritos aunque
-- alguno no tenga mediciones; COALESCE cambia esos vacíos por cero.
-- NULLIF evita dividir entre cero cuando un distrito no tiene mediciones con límite.
-- Se multiplica por 100.0 y no por 100 para que la división dé decimales.
resumen AS (
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

-- Paso 4: calcular las tres posiciones.
-- La función de ranking denso da la misma posición a los empates y no deja huecos:
-- si dos distritos empatan en el primer lugar, el siguiente queda segundo y no tercero.
-- La posición por sensores cuenta los sensores de todos los estados y usa el mismo
-- ranking denso que la consulta 8, así que para cada distrito da el mismo número.
-- La última columna guarda cuándo se calculó, para saber si el ranking está al día.
SELECT
    DENSE_RANK() OVER (ORDER BY total_sensores DESC) AS posicion_sensores,
    DENSE_RANK() OVER (ORDER BY pct_sobre_limite DESC) AS posicion_criticidad,
    DENSE_RANK() OVER (ORDER BY total_mediciones DESC) AS posicion_actividad,
    resumen.*,
    now() AS actualizado_en
FROM resumen;

-- Índice único por distrito. Lo exige la actualización concurrente de la vista
-- (REFRESH MATERIALIZED VIEW CONCURRENTLY), que deja seguir leyendo el ranking
-- mientras se recalcula, porque compara fila por fila usando esta llave.
CREATE UNIQUE INDEX idx_mv_ranking_zonas_distrito ON mv_ranking_zonas (id_distrito);
