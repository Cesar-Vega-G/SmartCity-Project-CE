-- Consulta obligatoria 10: consulta utilizando procedimientos almacenados o funciones
-- Requiere 01_vistas.sql y 02_funciones.sql.


-- 10a. Resumen de un sensor en un período (función que devuelve una tabla)
-- Pregunta:
-- ¿Cómo se comportó el sensor S-00002 (calidad del aire) en marzo de 2025?
-- Criterio:
-- Una fila por variable; inicio incluido y fin excluido. Cambiar los tres
-- parámetros para revisar otro sensor u otro período.
-- Justificación:
-- La función encapsula el filtro por sensor y fechas (usa
-- idx_medicion_sensor_fecha) y la clasificación del máximo con fn_nivel_alerta.
SELECT *
FROM fn_resumen_sensor('S-00002', TIMESTAMP '2025-03-01 00:00:00', TIMESTAMP '2025-04-01 00:00:00');


-- 10b. Las 20 mediciones más altas de PM2.5 en julio de 2026 (función escalar)
-- Pregunta:
-- ¿Qué mediciones de PM2.5 fueron las más altas en julio de 2026 y qué nivel de
-- alerta les corresponde con la misma regla que usa Mongo?
-- Justificación:
-- fn_nivel_alerta se aplica fila por fila dentro del SELECT, igual que una
-- función propia de Postgres. La vista aporta distrito y límite.
SELECT
    fecha_hora,
    id_sensor,
    distrito,
    valor,
    limite_alerta,
    fn_nivel_alerta(valor, limite_alerta) AS nivel
FROM v_medicion_detalle
WHERE variable = 'pm25'
  AND fecha_hora >= TIMESTAMP '2026-07-01 00:00:00'
  AND fecha_hora < TIMESTAMP '2026-08-01 00:00:00'
ORDER BY valor DESC, fecha_hora, id_sensor
LIMIT 20;


-- 10c. Procedimientos almacenados
-- Pregunta:
-- ¿Qué sensores deberían pasar a inactivo porque no enviaron datos en las
-- últimas 72 horas del dataset?
-- Justificación:
-- sp_actualizar_estado_sensores hace los UPDATE y avisa cuántos cambió con un
-- NOTICE (en DBeaver aparece en la pestaña de salida). Se corre dentro de una
-- transacción y se termina con ROLLBACK para que la demostración no cambie la
-- base; cambiar ROLLBACK por COMMIT para dejar los cambios.
BEGIN;

SELECT estado, COUNT(*) AS sensores FROM sensor GROUP BY estado ORDER BY estado;

CALL sp_actualizar_estado_sensores(TIMESTAMP '2026-09-01 00:00:00', 72);

SELECT estado, COUNT(*) AS sensores FROM sensor GROUP BY estado ORDER BY estado;

ROLLBACK;

-- Recalcular el ranking de zonas después de una carga nueva:
CALL sp_refrescar_ranking_zonas();
