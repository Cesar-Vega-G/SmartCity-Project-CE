// Pregunta: Que zonas tienen mayor concentracion de contaminacion?
// Justificacion: Ordena el promedio de un solo contaminante (no2 por defecto); muestra cobertura y no suma contaminantes.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/13_ranking_contaminacion.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 13, parametros);
})();

