// Ejecutar solo el CRUD demostrativo; nunca modifica las cuatro colecciones del proyecto.
(() => {
  load((process.env.SC_CONSULTAS_DIR || process.cwd()+"/mongo/consultas")+"/cargar.js");
  const V=globalThis.SC_VALIDACION;
  print(EJSON.stringify(V.aislada(db,base=>globalThis.SC_CRUD.demostrar(base)),null,2));
})();
