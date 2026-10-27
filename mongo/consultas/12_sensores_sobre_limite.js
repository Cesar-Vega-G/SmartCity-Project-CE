// Pregunta: Que sensores registraron valores sobre su limite?
// Justificacion: Compara valor y limite dentro del documento con $expr y agrupa alertas por sensor y variable.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/12_sensores_sobre_limite.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 12, parametros);
})();

