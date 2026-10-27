// Pregunta: Cual es el promedio de cada variable por zona?
// Justificacion: Un voto por valor valido, sin imputacion ni mezcla de unidades; devuelve cantidad, promedio y extremos.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/06_promedio_zona.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 6, parametros);
})();

