// Pregunta: Cuantos incidentes hay por categoria y estado?
// Justificacion: Usa fecha_reporte y agrupa sin asumir que datos_extra tiene siempre los mismos campos.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/08_incidentes_categoria.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 8, parametros);
})();

