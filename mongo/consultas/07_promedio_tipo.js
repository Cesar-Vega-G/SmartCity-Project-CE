// Pregunta: Cual es el promedio por tipo de sensor?
// Justificacion: Separa tipo y variable porque un sensor puede emitir magnitudes de distintas unidades.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/07_promedio_tipo.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 7, parametros);
})();

