-- Consulta obligatoria 10: consulta utilizando procedimientos almacenados o funciones
-- Requiere haber ejecutado antes el archivo de vistas y el archivo de funciones.


-- 10a. Resumen de un sensor en un período (función que devuelve una tabla)
-- Pregunta:
-- ¿Cómo se comportó un sensor de calidad del aire en marzo de 2025?
-- Criterio:
-- Una fila por variable. La fecha de inicio se incluye y la de fin se excluye.
-- Para revisar otro sensor u otro período basta con cambiar los tres valores.
-- Justificación:
-- La función ya trae el filtro por sensor y fechas (que usa el índice por sensor y
-- fecha) y la clasificación del valor máximo con la función de nivel de alerta.
-- La suma de la cantidad de mediciones debe coincidir con las filas que devuelve
-- la consulta 17 de Sebastián, que pide el mismo sensor y el mismo mes.
SELECT *
FROM fn_resumen_sensor('S-00002', TIMESTAMP '2025-03-01 00:00:00', TIMESTAMP '2025-04-01 00:00:00');


-- 10b. Las 20 mediciones más altas de PM2.5 en julio de 2026 (función escalar)
-- Pregunta:
-- ¿Qué mediciones de PM2.5 fueron las más altas en julio de 2026 y qué nivel de
-- alerta les corresponde con la misma regla que usa Mongo?
-- Justificación:
-- La función de nivel de alerta se aplica fila por fila dentro del SELECT, igual que
-- cualquier función propia de Postgres. La vista aporta el distrito y el límite.
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
-- Si dos valores empatan, la fecha y el sensor deciden el orden para que el
-- resultado salga siempre igual.
ORDER BY valor DESC, fecha_hora, id_sensor
LIMIT 20;


-- 10c. Procedimientos almacenados
-- Pregunta:
-- ¿Qué sensores deberían pasar a inactivo porque no enviaron datos en las últimas
-- 72 horas de los datos?
-- Justificación:
-- El procedimiento hace los cambios y avisa cuántos sensores cambió con un mensaje
-- que en DBeaver aparece en la pestaña de salida.
-- Todo se ejecuta dentro de una transacción: BEGIN abre un borrador y ROLLBACK lo
-- descarta, así la demostración no cambia la base de verdad. Para dejar los
-- cambios hay que cambiar ROLLBACK por COMMIT.
-- Se cuenta cuántos sensores hay en cada estado antes y después de llamar al
-- procedimiento para ver el efecto.
BEGIN;

SELECT estado, COUNT(*) AS sensores FROM sensor GROUP BY estado ORDER BY estado;

CALL sp_actualizar_estado_sensores(TIMESTAMP '2026-09-01 00:00:00', 72);

SELECT estado, COUNT(*) AS sensores FROM sensor GROUP BY estado ORDER BY estado;

ROLLBACK;

-- Recalcular el ranking de zonas. Hace falta después de cada carga nueva de
-- mediciones, porque la vista materializada guarda el cálculo anterior.
CALL sp_refrescar_ranking_zonas();
