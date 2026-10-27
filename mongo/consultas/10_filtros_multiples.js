// Pregunta: Que lecturas de trafico del Centro superaron carga 80?
// Justificacion: Combina tipo, zona, fechas, variable, calidad y umbral estricto; limita solo despues de filtrar y ordenar.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/10_filtros_multiples.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 10, parametros);
})();

