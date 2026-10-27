// Pregunta: Que lecturas produjo un sensor?
// Justificacion: Igualdad por sensor y rango temporal permiten aprovechar el indice compuesto; conserva la calidad del dato crudo.
// Ejecucion desde la raiz: mongosh [conexion] --file mongo/consultas/01_lecturas_sensor.js
// En Compass: ver README; el resultado incluye el filtro/pipeline exacto y sus parametros.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const M=globalThis.SC;
  // Editar, por ejemplo: {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z")}
  const parametros = {};
  M.mostrar(db.getSiblingDB("smartcity"), 1, parametros);
})();

