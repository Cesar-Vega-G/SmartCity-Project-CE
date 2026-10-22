-- Pregunta:
-- ¿Qué tipos de sensores están presentes en un distrito?

-- Criterio:
-- Parámetro editable: distrito 'Centro', escrito como aparece en el catálogo.
-- Cada fila representa un tipo distinto presente en ese distrito.
-- Incluye todos los estados, aunque el sensor no tenga mediciones registradas.
-- Devuelve vacío si el distrito no existe o no tiene sensores.
-- Ordena por nombre e identificador del tipo.

-- Justificación:
-- Los INNER JOIN recorren distrito -> ubicacion -> sensor -> tipo_sensor.
-- WHERE selecciona el distrito y DISTINCT evita repetir un tipo cuando hay
-- varios sensores de ese tipo en una o varias ubicaciones del distrito.
-- Se incluye id_distrito para distinguir distritos homónimos si se amplía el catálogo.

SELECT DISTINCT
    d.id_distrito,
    d.nombre AS distrito,
    t.id_tipo,
    t.nombre AS tipo_sensor
FROM distrito AS d
INNER JOIN ubicacion AS u ON u.id_distrito = d.id_distrito
INNER JOIN sensor AS s ON s.id_ubicacion = u.id_ubicacion
INNER JOIN tipo_sensor AS t ON t.id_tipo = s.id_tipo
WHERE d.nombre = 'Centro'::varchar
ORDER BY t.nombre, t.id_tipo, d.id_distrito;
