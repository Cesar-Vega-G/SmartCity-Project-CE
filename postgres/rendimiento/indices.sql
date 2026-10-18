-- Indices de PostgreSQL

-- medicion es la tabla grande (4.6 millones de filas).
-- Al crear el indice en la tabla padre, Postgres lo crea en cada particion.
CREATE INDEX IF NOT EXISTS idx_medicion_sensor_fecha ON medicion (id_sensor, fecha_hora);
CREATE INDEX IF NOT EXISTS idx_medicion_variable_fecha ON medicion (id_variable, fecha_hora);

-- llaves foraneas (Postgres no les crea indice solo)
CREATE INDEX IF NOT EXISTS idx_sensor_tipo ON sensor (id_tipo);
CREATE INDEX IF NOT EXISTS idx_sensor_ubicacion ON sensor (id_ubicacion);
CREATE INDEX IF NOT EXISTS idx_sensor_organismo ON sensor (id_organismo);
CREATE INDEX IF NOT EXISTS idx_ubicacion_distrito ON ubicacion (id_distrito);
CREATE INDEX IF NOT EXISTS idx_vehiculo_ruta ON vehiculo (id_ruta);
CREATE INDEX IF NOT EXISTS idx_ruta_estacion_estacion ON ruta_estacion (id_estacion);

-- filtros frecuentes
CREATE INDEX IF NOT EXISTS idx_sensor_estado ON sensor (estado);
CREATE INDEX IF NOT EXISTS idx_sensor_fecha_instalacion ON sensor (fecha_instalacion);
