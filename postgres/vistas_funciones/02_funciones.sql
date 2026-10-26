-- Funciones y procedimientos almacenados de PostgreSQL
-- Se ejecuta después del archivo de vistas (ver el README de esta carpeta).
-- CREATE OR REPLACE permite volver a correrlo sin borrar nada antes.


-- Función: nivel de alerta de un valor
-- Qué resuelve:
-- Clasifica un valor contra su límite con la misma regla que usa Mongo para crear
-- las alertas (ver el contrato de datos): si pasa el límite es advertencia y si
-- pasa una vez y media el límite es crítica. Así las dos bases dicen lo mismo de
-- un mismo valor.
-- Por qué así:
-- Está escrita en SQL simple porque es una sola expresión; no necesita variables
-- ni validaciones.
-- Es IMMUTABLE porque el resultado depende solo de los dos números que recibe y no
-- lee ninguna tabla. Eso le permite a Postgres optimizarla al usarla en consultas.
-- Si la variable no tiene límite (vacío) devuelve sin límite en vez de normal,
-- porque no hay contra qué comparar.
CREATE OR REPLACE FUNCTION fn_nivel_alerta(p_valor NUMERIC, p_limite NUMERIC)
RETURNS VARCHAR
LANGUAGE sql
IMMUTABLE
AS $$
    -- El orden de los casos importa: primero se revisa el caso más grave, porque
    -- un valor que pasa una vez y media el límite también pasa el límite.
    SELECT CASE
        WHEN p_limite IS NULL THEN 'sin_limite'
        WHEN p_valor > 1.5 * p_limite THEN 'critica'
        WHEN p_valor > p_limite THEN 'advertencia'
        ELSE 'normal'
    -- El texto se convierte a VARCHAR para que coincida exactamente con el tipo que
    -- declara la función.
    END::VARCHAR;
$$;


-- Función: resumen de un sensor en un período
-- Qué resuelve:
-- Para un sensor y un rango de fechas devuelve una fila por cada variable que mide,
-- con la cantidad de mediciones, el promedio, el mínimo, el máximo, cuántas pasaron
-- el límite, el nivel de alerta del valor máximo y la primera y última fecha.
-- Es lo que necesita el dashboard cuando se elige un sensor y un período.
-- Por qué así:
-- La fecha de inicio se incluye y la de fin se excluye, igual que en las consultas
-- de Sebastián. Así un mes completo se pide como del primero de ese mes al primero
-- del mes siguiente, sin preocuparse por la última hora del último día.
-- El filtro por sensor y por fecha usa el índice que Cesar creó con esas dos
-- columnas, y solo lee las particiones del período pedido.
-- Está escrita en plpgsql (el lenguaje de programación de Postgres) y no en SQL
-- simple para poder validar los parámetros y dar un error claro, en vez de devolver
-- una tabla vacía que no explica qué pasó.
-- Es STABLE porque lee tablas pero no las modifica.
CREATE OR REPLACE FUNCTION fn_resumen_sensor(
    p_id_sensor VARCHAR,
    p_desde TIMESTAMP,
    p_hasta TIMESTAMP
)
-- Las columnas que devuelve la función, como si fuera una tabla.
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
-- Algunas columnas de salida se llaman igual que columnas de las tablas (por
-- ejemplo la unidad y el límite). Esta instrucción le dice a Postgres que, si hay
-- duda, se refiere a la columna de la tabla y no a la de salida.
#variable_conflict use_column
BEGIN
    -- Validación 1: las dos fechas tienen que existir y el inicio debe ser antes
    -- que el fin.
    IF p_desde IS NULL OR p_hasta IS NULL OR p_desde >= p_hasta THEN
        RAISE EXCEPTION 'Rango de fechas inválido: desde % hasta %', p_desde, p_hasta;
    END IF;

    -- Validación 2: el sensor tiene que existir. Sin esto, un código mal escrito
    -- devolvería una tabla vacía igual que un sensor real sin datos, y no se
    -- podrían distinguir los dos casos.
    IF NOT EXISTS (SELECT 1 FROM sensor AS s WHERE s.id_sensor = p_id_sensor) THEN
        RAISE EXCEPTION 'No existe el sensor %', p_id_sensor;
    END IF;

    -- RETURN QUERY devuelve como resultado de la función todas las filas de esta
    -- consulta. Las columnas tienen que ir en el mismo orden que en RETURNS TABLE.
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
        -- Se reutiliza la función anterior para que el nivel se calcule con la
        -- misma regla en todas partes.
        fn_nivel_alerta(MAX(m.valor), v.limite_alerta),
        MIN(m.fecha_hora),
        MAX(m.fecha_hora)
    FROM medicion AS m
    INNER JOIN variable AS v ON v.id_variable = m.id_variable
    WHERE m.id_sensor = p_id_sensor
      AND m.fecha_hora >= p_desde
      AND m.fecha_hora < p_hasta
    -- Una fila por variable. Se agrupa también por el identificador para no juntar
    -- dos variables distintas aunque tuvieran el mismo nombre.
    GROUP BY v.id_variable, v.nombre, v.unidad, v.limite_alerta
    ORDER BY v.nombre;
END;
$$;


-- Función: sensores de un distrito
-- Qué resuelve:
-- Recibe el nombre de un distrito y devuelve sus sensores con su tipo, su estado, la
-- zona donde están y la fecha en que se instalaron. La pidió Sebastián para usarla
-- en su consulta 10.
-- Por qué así:
-- El nombre se compara sin importar mayúsculas ni minúsculas, para que Centro y
-- centro den el mismo resultado.
-- Incluye sensores de todos los estados, igual que las consultas de Sebastián, para
-- que el estado se pueda ver y filtrar después.
-- Si el distrito no existe da un error claro. Sin esa validación, un nombre mal
-- escrito y un distrito real sin sensores devolverían los dos una tabla vacía, y no
-- se podrían distinguir.
-- Lee la vista de sensores para no repetir sus cinco uniones.
-- Es STABLE porque lee tablas pero no las modifica.
CREATE OR REPLACE FUNCTION fn_sensores_por_distrito(p_distrito VARCHAR)
RETURNS TABLE (
    id_sensor VARCHAR,
    nombre_sensor VARCHAR,
    tipo_sensor VARCHAR,
    estado VARCHAR,
    nombre_zona VARCHAR,
    fecha_instalacion DATE
)
LANGUAGE plpgsql
STABLE
AS $$
-- Las columnas de salida se llaman igual que las de la vista. Esta instrucción le
-- dice a Postgres que, si hay duda, se refiere a la columna de la vista.
#variable_conflict use_column
BEGIN
    IF NOT EXISTS (SELECT 1 FROM distrito AS d WHERE lower(d.nombre) = lower(p_distrito)) THEN
        RAISE EXCEPTION 'No existe el distrito %', p_distrito;
    END IF;

    RETURN QUERY
    SELECT
        sd.id_sensor,
        sd.nombre_sensor,
        sd.tipo_sensor,
        sd.estado,
        sd.nombre_zona,
        sd.fecha_instalacion
    FROM v_sensor_detalle AS sd
    WHERE lower(sd.distrito) = lower(p_distrito)
    -- Primero agrupados por tipo y dentro de cada tipo por código de sensor, para que
    -- el resultado salga siempre en el mismo orden.
    ORDER BY sd.tipo_sensor, sd.id_sensor;
END;
$$;


-- Procedimiento: actualizar el estado de los sensores según si llegan datos
-- Qué resuelve:
-- Pasa a inactivo los sensores activos que no tienen mediciones en las últimas
-- horas antes de la fecha de referencia, y vuelve a poner como activos los
-- inactivos que sí tienen. Los que están en mantenimiento no se tocan, porque ese
-- estado lo pone una persona y no depende de los datos.
-- Por qué es un procedimiento y no una función:
-- Modifica datos (hace UPDATE) y es una tarea de mantenimiento que se ejecuta con
-- CALL, no algo que se use dentro de una consulta.
-- Por qué la fecha de referencia es un parámetro:
-- Los datos terminan el 31 de agosto de 2026. Si se usara la fecha de hoy, todos
-- los sensores parecerían apagados. Por defecto se usa el cierre de los datos y
-- una ventana de 72 horas.
-- No confirma los cambios por su cuenta: quien lo llama decide si los confirma
-- (COMMIT) o los descarta (ROLLBACK). Así se puede probar sin cambiar la base.
CREATE OR REPLACE PROCEDURE sp_actualizar_estado_sensores(
    p_fecha_referencia TIMESTAMP DEFAULT TIMESTAMP '2026-09-01 00:00:00',
    p_horas_sin_datos INT DEFAULT 72
)
LANGUAGE plpgsql
AS $$
-- Variables internas del procedimiento.
DECLARE
    v_desde TIMESTAMP;      -- inicio de la ventana que se revisa
    v_desactivados INT;     -- cuántos sensores pasaron a inactivo
    v_reactivados INT;      -- cuántos sensores volvieron a activo
BEGIN
    -- Una ventana de cero horas o negativa no tiene sentido.
    IF p_horas_sin_datos IS NULL OR p_horas_sin_datos <= 0 THEN
        RAISE EXCEPTION 'horas_sin_datos debe ser mayor que cero';
    END IF;

    -- La ventana va desde N horas antes de la fecha de referencia hasta esa fecha.
    v_desde := p_fecha_referencia - make_interval(hours => p_horas_sin_datos);

    -- Primer cambio: activos sin ninguna medición dentro de la ventana.
    -- NOT EXISTS se detiene en cuanto encuentra una medición, así que no necesita
    -- contar todas las mediciones del sensor.
    UPDATE sensor AS s
    SET estado = 'inactivo'
    WHERE s.estado = 'activo'
      AND NOT EXISTS (
          SELECT 1 FROM medicion AS m
          WHERE m.id_sensor = s.id_sensor
            AND m.fecha_hora >= v_desde
            AND m.fecha_hora < p_fecha_referencia
      );
    -- Guarda cuántas filas cambió el UPDATE anterior.
    GET DIAGNOSTICS v_desactivados = ROW_COUNT;

    -- Segundo cambio: inactivos que sí tienen mediciones dentro de la ventana.
    -- Los que el paso anterior acaba de desactivar no entran aquí, porque justamente
    -- no tienen mediciones en la ventana.
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

    -- NOTICE muestra un mensaje informativo sin detener nada. En DBeaver aparece en
    -- la pestaña de salida.
    RAISE NOTICE 'Ventana [%, %): % sensores pasaron a inactivo, % volvieron a activo',
        v_desde, p_fecha_referencia, v_desactivados, v_reactivados;
END;
$$;


-- Procedimiento: recalcular el ranking de zonas
-- Qué resuelve:
-- La vista materializada guarda una foto del ranking. Después de cargar mediciones
-- nuevas hay que volver a calcularla, y este procedimiento lo hace.
-- Por qué así:
-- Con el parámetro en verdadero (el valor por defecto) la recalcula de forma
-- concurrente: se puede seguir leyendo el ranking viejo mientras se calcula el
-- nuevo. Para eso necesita el índice único por distrito que crea el archivo de
-- vistas. Con el parámetro en falso es más rápido pero bloquea las lecturas
-- mientras dura.
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
