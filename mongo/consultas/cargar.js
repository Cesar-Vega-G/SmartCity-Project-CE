// load permite que mongosh transforme las operaciones asincronas de su API.
(() => {
  const carpeta=process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas";
  for (const archivo of ["lib.js","crud.js","pruebas_controladas.js","validacion.js"]) load(carpeta+"/"+archivo);
})();
