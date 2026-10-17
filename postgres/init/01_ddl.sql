-- Modelo relacional SmartCity Madrid

CREATE TABLE ciudad (
    id_ciudad   SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    pais        VARCHAR(100) NOT NULL,
    UNIQUE (nombre, pais)
);

CREATE TABLE distrito (
    id_distrito INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ciudad   SMALLINT NOT NULL REFERENCES ciudad(id_ciudad),
    nombre      VARCHAR(100) NOT NULL,
    UNIQUE (id_ciudad, nombre)
);

CREATE TABLE ubicacion (
    id_ubicacion INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_distrito  INT NOT NULL REFERENCES distrito(id_distrito),
    nombre_zona  VARCHAR(100) NOT NULL,
    latitud      NUMERIC(9,6) NOT NULL CHECK (latitud BETWEEN -90 AND 90),
    longitud     NUMERIC(9,6) NOT NULL CHECK (longitud BETWEEN -180 AND 180)
);

CREATE TABLE categoria_sensor (
    id_categoria     SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_categoria VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE tipo_sensor (
    id_tipo      SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_categoria SMALLINT NOT NULL REFERENCES categoria_sensor(id_categoria),
    nombre       VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE variable (
    id_variable   SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre        VARCHAR(50) NOT NULL UNIQUE,
    unidad        VARCHAR(20) NOT NULL,
    limite_alerta NUMERIC(10,2)
);

CREATE TABLE organismo (
    id_organismo INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL UNIQUE,
    responsable  VARCHAR(150) NOT NULL
);

CREATE TABLE usuario (
    id_usuario   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    correo       VARCHAR(150) NOT NULL UNIQUE,
    id_organismo INT REFERENCES organismo(id_organismo)
);

-- id_sensor es el mismo codigo que se usa en Mongo (ej: S-00001)
-- codigo_origen es el codigo del sensor en los datos abiertos de Madrid
CREATE TABLE sensor (
    id_sensor         VARCHAR(12) PRIMARY KEY,
    codigo_origen     VARCHAR(30),
    nombre            VARCHAR(150) NOT NULL,
    id_tipo           SMALLINT NOT NULL REFERENCES tipo_sensor(id_tipo),
    id_ubicacion      INT NOT NULL REFERENCES ubicacion(id_ubicacion),
    id_organismo      INT NOT NULL REFERENCES organismo(id_organismo),
    fecha_instalacion DATE NOT NULL,
    estado            VARCHAR(15) NOT NULL DEFAULT 'activo'
                      CHECK (estado IN ('activo', 'inactivo', 'mantenimiento'))
);

CREATE TABLE ruta (
    id_ruta      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo       VARCHAR(20) NOT NULL UNIQUE,
    nombre       VARCHAR(150) NOT NULL,
    id_organismo INT REFERENCES organismo(id_organismo)
);

CREATE TABLE estacion (
    id_estacion  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    tipo         VARCHAR(20) NOT NULL
                 CHECK (tipo IN ('parada_bus', 'estacion_tren', 'estacionamiento')),
    id_ubicacion INT NOT NULL REFERENCES ubicacion(id_ubicacion)
);

CREATE TABLE ruta_estacion (
    id_ruta     INT NOT NULL REFERENCES ruta(id_ruta) ON DELETE CASCADE,
    id_estacion INT NOT NULL REFERENCES estacion(id_estacion),
    orden       SMALLINT NOT NULL CHECK (orden > 0),
    PRIMARY KEY (id_ruta, id_estacion),
    UNIQUE (id_ruta, orden)
);

CREATE TABLE vehiculo (
    id_vehiculo INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    placa       VARCHAR(15) NOT NULL UNIQUE,
    tipo        VARCHAR(15) NOT NULL CHECK (tipo IN ('bus', 'auto', 'moto', 'bicicleta')),
    capacidad   SMALLINT CHECK (capacidad > 0),
    id_ruta     INT REFERENCES ruta(id_ruta)
);

-- particionada por año
CREATE TABLE medicion (
    id_medicion BIGSERIAL,
    id_sensor   VARCHAR(12) NOT NULL REFERENCES sensor(id_sensor),
    id_variable SMALLINT NOT NULL REFERENCES variable(id_variable),
    fecha_hora  TIMESTAMP NOT NULL,
    valor       NUMERIC(12,3) NOT NULL,
    PRIMARY KEY (id_medicion, fecha_hora)
) PARTITION BY RANGE (fecha_hora);

CREATE TABLE medicion_2024 PARTITION OF medicion FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE medicion_2025 PARTITION OF medicion FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE medicion_2026 PARTITION OF medicion FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE medicion_default PARTITION OF medicion DEFAULT;
