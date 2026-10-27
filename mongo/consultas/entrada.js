// Entrada del ejecutor Docker. Las credenciales se leen del entorno existente del contenedor.
(() => {
  const admin=db.getSiblingDB("admin");
  if (process.env.MONGO_INITDB_ROOT_USERNAME) {
    admin.auth(process.env.MONGO_INITDB_ROOT_USERNAME,process.env.MONGO_INITDB_ROOT_PASSWORD);
  }
  load(process.env.SC_CONSULTAS_DIR+"/cargar.js");
  const V=globalThis.SC_VALIDACION;
  const resultado=V.correr(db.getSiblingDB(process.env.SC_BASE || "smartcity"),process.env.SC_MODO || "comprobar");
  print(EJSON.stringify(resultado,null,2));
})();
