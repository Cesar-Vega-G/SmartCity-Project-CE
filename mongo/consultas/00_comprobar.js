// Pregunta: esta disponible la base completa y que contrato materializado contiene?
// Justificacion: los conteos y tipos reales evitan atribuir a esta instancia cifras de otra carga.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const V=globalThis.SC_VALIDACION;
  print(EJSON.stringify(V.inventario(db.getSiblingDB("smartcity")),null,2));
})();
