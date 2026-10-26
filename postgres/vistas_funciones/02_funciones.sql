-- Funciones y procedimiento almacenado de PostgreSQL
-- Se ejecuta después de 01_vistas.sql (ver README.md de esta carpeta).
-- CREATE OR REPLACE permite volver a correrlo sin borrar nada.


-- fn_nivel_alerta(valor, limite)
-- Qué resuelve:
-- Clasifica un valor contra su límite con la misma regla que usa Mongo para las
-- alertas (docs/contrato_datos.md): pasa el límite = advertencia, pasa 1.5 veces
-- el límite = critica. Así las dos bases dicen lo mismo de un mismo valor.
-- Por qué así:
-- Es IMMUTABLE porque el resultado depende solo de sus argumentos; eso permite
-- usarla en cualquier consulta y que Postgres la evalúe sin acceder a tablas.
-- Si la variable no tiene límite (NULL) devuelve 'sin_limite'.
CREATE OR REPLACE FUNCTION fn_nivel_alerta(p_valor NUMERIC, p_limite NUMERIC)
RETURNS VARCHAR
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE
        WHEN p_limite IS NULL THEN 'sin_limite'
        WHEN p_valor > 1.5 * p_limite THEN 'critica'
        WHEN p_valor > p_limite THEN 'advertencia'
        ELSE 'normal'
    END::VARCHAR;
$$;


-- fn_resumen_sensor(id_sensor, desde, hasta)
-- Qué resuelve:
-- Para un sensor y un período, devuelve una fila por variable medida con la
-- cantidad de mediciones, promedio, mínimo, máximo, cuántas pasaron el límite y
-- la primera y última fecha. Es lo que necesita el dashboard cuando se elige un
-- sensor y un rango de fechas.
-- Por qué así:
-- Recibe el período como parámetros: el inicio se incluye y el fin se excluye,
-- igual que en las consultas de la persona C.
-- El WHERE sobre id_sensor y fecha_hora usa idx_medicion_sensor_fecha y solo lee
-- las particiones del período.
-- Es plpgsql (y no sql) para poder validar los parámetros y dar un error claro
-- en vez de devolver una tabla vacía que no explica nada.
-- #variable_conflict use_column evita que los nombres de las columnas de salida
-- choquen con columnas de las tablas.
CREATE OR REPLACE FUNCTION fn_resumen_sensor(
    p_id_sensor VARCHAR,
    p_desde TIMESTAMP,
    p_hasta TIMESTAMP
)
RETURNS TABLE (
    variable VARCHAR,
    unidad VARCHAR,
    limite_alerta NUMERIC,
    cantidad_mediciones BIGINT,
    promedio NUMERIC,
    minimo NUMERIC,
    maximo NUMERIC,
    mediciones_sobre_limite BIGINT,
    nivel_maximo VARCHAR,
    primera_medicion TIMESTAMP,
    ultima_medicion TIMESTAMP
)
LANGUAGE plpgsql
STABLE
AS $$
#variable_conflict use_column
BEGIN
    IF p_desde IS NULL OR p_hasta IS NULL OR p_desde >= p_hasta THEN
        RAISE EXCEPTION 'Rango de fechas inválido: desde % hasta %', p_desde, p_hasta;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM sensor AS s WHERE s.id_sensor = p_id_sensor) THEN
        RAISE EXCEPTION 'No existe el sensor %', p_id_sensor;
    END IF;

    RETURN QUERY
    SELECT
        v.nombre,
        v.unidad,
        v.limite_alerta,
        COUNT(*),
        ROUND(AVG(m.valor), 3),
        MIN(m.valor),
        MAX(m.valor),
        COUNT(*) FILTER (WHERE m.valor > v.limite_alerta),
        fn_nivel_alerta(MAX(m.valor), v.limite_alerta),
        MIN(m.fecha_hora),
        MAX(m.fecha_hora)
    FROM medicion AS m
    INNER JOIN variable AS v ON v.id_variable = m.id_variable
    WHERE m.id_sensor = p_id_sensor
      AND m.fecha_hora >= p_desde
      AND m.fecha_hora < p_hasta
    GROUP BY v.id_variable, v.nombre, v.unidad, v.limite_alerta
    ORDER BY v.nombre;
END;
$$;


-- sp_actualizar_estado_sensores(fecha_referencia, horas_sin_datos)
-- Qué resuelve:
-- Pasa a 'inactivo' los sensores 'activo' que no tienen mediciones en las
-- últimas horas_sin_datos horas antes de fecha_referencia, y vuelve a 'activo'
-- los 'inactivo' que sí tienen. Los de 'mantenimiento' no se tocan, porque ese
-- estado lo pone una persona, no los datos.
-- Por qué es un procedimiento y no una función:
-- Modifica datos (UPDATE) y es una tarea de mantenimiento que se ejecuta con
-- CALL, no algo que se consulte dentro de un SELECT.
-- La fecha de referencia es un parámetro porque el dataset termina el
-- 2026-08-31: con now() todos los sensores quedarían inactivos.
-- Por defecto revisa las últimas 72 horas antes del cierre del dataset.
-- No hace COMMIT: quien lo llama decide si confirma o hace ROLLBACK, así se
-- puede probar dentro de una transacción sin cambiar la base.
CREATE OR REPLACE PROCEDURE sp_actualizar_estado_sensores(
    p_fecha_referencia TIMESTAMP DEFAULT TIMESTAMP '2026-09-01 00:00:00',
    p_horas_sin_datos INT DEFAULT 72
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_desde TIMESTAMP;
    v_desactivados INT;
    v_reactivados INT;
BEGIN
    IF p_horas_sin_datos IS NULL OR p_horas_sin_datos <= 0 THEN
        RAISE EXCEPTION 'horas_sin_datos debe ser mayor que cero';
    END IF;

    v_desde := p_fecha_referencia - make_interval(hours => p_horas_sin_datos);

    UPDATE sensor AS s
    SET estado = 'inactivo'
    WHERE s.estado = 'activo'
      AND NOT EXISTS (
          SELECT 1 FROM medicion AS m
          WHERE m.id_sensor = s.id_sensor
            AND m.fecha_hora >= v_desde
            AND m.fecha_hora < p_fecha_referencia
      );
    GET DIAGNOSTICS v_desactivados = ROW_COUNT;

    UPDATE sensor AS s
    SET estado = 'activo'
    WHERE s.estado = 'inactivo'
      AND EXISTS (
          SELECT 1 FROM medicion AS m
          WHERE m.id_sensor = s.id_sensor
            AND m.fecha_hora >= v_desde
            AND m.fecha_hora < p_fecha_referencia
      );
    GET DIAGNOSTICS v_reactivados = ROW_COUNT;

    RAISE NOTICE 'Ventana [%, %): % sensores pasaron a inactivo, % volvieron a activo',
        v_desde, p_fecha_referencia, v_desactivados, v_reactivados;
END;
$$;


-- sp_refrescar_ranking_zonas(concurrente)
-- Qué resuelve:
-- Recalcula mv_ranking_zonas después de una carga nueva de mediciones.
-- Por qué así:
-- Con concurrente = true (por defecto) usa REFRESH ... CONCURRENTLY, que deja
-- leer la vista mientras se recalcula (necesita el índice único sobre
-- id_distrito). Con false bloquea las lecturas pero es más rápido.
CREATE OR REPLACE PROCEDURE sp_refrescar_ranking_zonas(p_concurrente BOOLEAN DEFAULT true)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_concurrente THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ranking_zonas;
    ELSE
        REFRESH MATERIALIZED VIEW mv_ranking_zonas;
    END IF;
    RAISE NOTICE 'mv_ranking_zonas actualizada';
END;
$$;
