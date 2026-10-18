// Indices de MongoDB (se pueden correr en mongosh o en un playground de VS Code)
use("smartcity");

// lecturas tiene ~3.1 millones de documentos
db.lecturas.createIndex({ id_sensor: 1, timestamp: 1 }, { name: "idx_sensor_timestamp" });
db.lecturas.createIndex({ tipo: 1, timestamp: 1 }, { name: "idx_tipo_timestamp" });
db.lecturas.createIndex({ "ubicacion.geo": "2dsphere" }, { name: "idx_geo" });

db.alertas.createIndex({ nivel: 1, "ubicacion.distrito": 1 }, { name: "idx_nivel_distrito" });
db.alertas.createIndex({ id_sensor: 1, timestamp: 1 }, { name: "idx_sensor_timestamp" });

db.eventos.createIndex({ tipo_evento: 1, timestamp: 1 }, { name: "idx_tipo_timestamp" });

db.incidentes.createIndex({ categoria: 1, fecha_reporte: 1 }, { name: "idx_categoria_fecha" });
