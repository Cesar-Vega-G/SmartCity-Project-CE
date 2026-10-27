// Pregunta: Que lecturas hay en el periodo?
// Justificacion: Inicio incluido y fin excluido evitan perder el ultimo dia; la muestra ordenada no excede 100 documentos.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/02_lecturas_fechas.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 2, parametros);
})();

