// Compass > Open MongoDB Shell: pegar todo el archivo despues de cargar los datos.
// No elimina indices ni modifica documentos. Repetir tras una recarga de colecciones.
// Se usa una variable local para seleccionar smartcity sin depender de la pestaña activa.
(() => {
  const base = db.getSiblingDB("smartcity");

  // lecturas tiene ~3.1 millones de documentos
  base.lecturas.createIndex({ id_sensor: 1, timestamp: 1 }, { name: "idx_sensor_timestamp" });
  base.lecturas.createIndex({ tipo: 1, timestamp: 1 }, { name: "idx_tipo_timestamp" });
  base.lecturas.createIndex({ "ubicacion.geo": "2dsphere" }, { name: "idx_geo" });

  base.alertas.createIndex({ nivel: 1, "ubicacion.distrito": 1 }, { name: "idx_nivel_distrito" });
  base.alertas.createIndex({ id_sensor: 1, timestamp: 1 }, { name: "idx_sensor_timestamp" });

  base.eventos.createIndex({ tipo_evento: 1, timestamp: 1 }, { name: "idx_tipo_timestamp" });

  base.incidentes.createIndex({ categoria: 1, fecha_reporte: 1 }, { name: "idx_categoria_fecha" });

})();
