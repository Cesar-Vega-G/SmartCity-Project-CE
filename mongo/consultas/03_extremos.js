// Pregunta: Cuales son los valores maximos y minimos?
// Justificacion: Descompone medicion y agrupa cada variable con su unidad; excluye solo valores cuya calidad no permite analizarlos.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/03_extremos.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 3, parametros);
})();

