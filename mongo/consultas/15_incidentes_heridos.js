// Pregunta: Que accidentes registraron personas heridas?
// Justificacion: Combina categoria, existencia y valor numerico del campo dinamico datos_extra.heridos.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/15_incidentes_heridos.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 15, parametros);
})();

