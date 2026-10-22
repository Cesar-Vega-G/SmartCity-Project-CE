-- Pregunta:
-- ¿Cuáles son los sensores de cada tipo y cuál es su estado?

-- Criterio:
-- Cada fila representa un sensor, con su identificador, nombre, tipo y estado.
-- Incluye todos los estados; ordena por tipo, nombre e identificador del sensor.

-- Justificación:
-- INNER JOIN relaciona cada sensor con el nombre de su tipo mediante id_tipo.
-- La llave foránea obligatoria garantiza un tipo existente para cada sensor.
-- No se agrupa porque se necesita el detalle individual de los sensores.

SELECT
    s.id_sensor,
    s.nombre AS nombre_sensor,
    t.nombre AS tipo_sensor,
    s.estado
FROM sensor AS s
INNER JOIN tipo_sensor AS t ON t.id_tipo = s.id_tipo
ORDER BY t.nombre, s.nombre, s.id_sensor;
