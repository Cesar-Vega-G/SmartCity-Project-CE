// Pregunta: Como evoluciona una variable durante el periodo?
// Justificacion: Agrupa por dia almacenado y distrito; no inventa dias ni ceros y conserva las fechas tal como fueron cargadas.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/14_evolucion_diaria.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 14, parametros);
})();

