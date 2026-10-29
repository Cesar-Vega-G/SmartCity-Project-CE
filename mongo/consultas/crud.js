// Compass > Open MongoDB Shell: pegar este archivo completo y pulsar Enter.
// Las siete operaciones se realizan en una base temporal exclusiva de esta ejecucion.
// PROPOSITO: requisito de operaciones MongoDB del enunciado, pagina 11.
// CRUD significa Create (crear), Read (leer), Update (actualizar) y Delete (eliminar).
// Los pipelines responden preguntas y calculan resultados; este archivo demuestra
// como crear, buscar, corregir y eliminar documentos con los siete metodos exigidos.
// No es el cargador del dataset ni debe pegarse en Aggregations.
// La funcion inmediata agrupa la demostracion y evita dejar variables globales.
(() => {
  // PREPARACION: generar un nombre unico permite repetir el ejemplo sin colisiones.
  // getSiblingDB selecciona esa base aunque Compass este mostrando smartcity.
  // La base y la coleccion se materializan al insertar el primer documento.
  const nombre = "smartcity_demo_" + new ObjectId().toHexString();
  const demo = db.getSiblingDB(nombre);
  const lecturas = demo.getCollection("lecturas");
  // COMPROBACIONES: registrar cada operacion aprobada y detenerse si algo falla.
  // Una confirmacion del servidor y una consulta posterior verifican lo ocurrido.
  const pasos = [];
  function verificar(operacion, condicion) {
    if (!condicion) throw new Error("Fallo: " + operacion);
    pasos.push(operacion);
    print("OK: " + operacion);
  }
  // MODELO DOCUMENTAL: misma forma basica de las lecturas del proyecto.
  // ubicacion y medicion son objetos anidados; cada medicion puede tener campos distintos.
  // ISODate guarda una fecha BSON. id_sensor identifica al sensor, no al documento:
  // MongoDB asigna un _id unico a cada documento insertado.
  function lectura(sensor, medicion) {
    return {id_sensor: sensor, tipo: "meteorologico",
      ubicacion: {distrito: "Centro"}, timestamp: ISODate("2026-07-01T00:00:00Z"),
      medicion: medicion, valido: true};
  }
  // try/finally garantiza intentar la limpieza tanto si todo pasa como si hay un error.
  try {
    // 1. CREATE — insertOne: insertar una lectura con temperatura 20.
    // acknowledged confirma la escritura; insertedId permite localizar ESTE documento.
    // La comprobacion confirma que ahora existe exactamente una lectura en la base demo.
    const uno = lecturas.insertOne(lectura("DEMO-1", {temperatura: 20}));
    verificar("insertOne", uno.acknowledged && lecturas.countDocuments({}) === 1);

    // 2. CREATE — insertMany: insertar dos documentos en una sola llamada.
    // Uno tiene temperatura y humedad; el otro, precipitacion. Esto muestra flexibilidad.
    // Al terminar deben existir tres documentos, contando el insertado anteriormente.
    const varios = lecturas.insertMany([
      lectura("DEMO-2", {temperatura: 30, humedad: 60}),
      lectura("DEMO-3", {precipitacion: 5})
    ]);
    verificar("insertMany", varios.acknowledged && lecturas.countDocuments({}) === 3);

    // 3. READ — find: buscar las lecturas con temperatura mayor o igual a 20.
    // La ruta medicion.temperatura accede al campo anidado; $gte incluye el valor 20.
    // La proyeccion oculta _id y muestra solo sensor y medicion. sort ordena por sensor.
    // find entrega un cursor; toArray lo consume para mostrar y comprobar estos pocos datos.
    // Debe encontrar DEMO-1 y DEMO-2; DEMO-3 no tiene temperatura.
    const encontrados = lecturas.find({"medicion.temperatura": {$gte: 20}},
      {_id: 0, id_sensor: 1, medicion: 1}).sort({id_sensor: 1}).toArray();
    printjson(encontrados);
    verificar("find", encontrados.length === 2);
    // 4. READ — findOne: recuperar un unico documento por su _id, sin usar un cursor.
    // Verificar temperatura 20 confirma que recuperamos la lectura de insertOne.
    verificar("findOne", lecturas.findOne({_id: uno.insertedId}).medicion.temperatura === 20);

    // 5. UPDATE — updateOne: corregir solo esa lectura, de 20 a 21.
    // $set con ruta anidada cambia temperatura sin reemplazar todo el documento.
    // modifiedCount confirma un cambio; findOne comprueba el nuevo valor guardado.
    const cambio = lecturas.updateOne({_id: uno.insertedId}, {$set: {"medicion.temperatura": 21}});
    verificar("updateOne", cambio.modifiedCount === 1 &&
      lecturas.findOne({_id: uno.insertedId}).medicion.temperatura === 21);
    // 6. UPDATE — updateMany: agregar revisada:true a las tres lecturas de la demo.
    // {} significa TODOS los documentos de esta coleccion temporal, no del proyecto.
    // No trasladar este filtro vacio a una coleccion real sin definir su alcance.
    // Verificamos tanto documentos modificados como cantidad con la marca nueva.
    const cambios = lecturas.updateMany({}, {$set: {revisada: true}});
    verificar("updateMany", cambios.modifiedCount === 3 && lecturas.countDocuments({revisada: true}) === 3);

    // 7. DELETE — deleteOne: borrar exclusivamente la lectura identificada por _id.
    // deletedCount debe ser uno; findOne devuelve null porque ya no existe.
    // Las otras dos lecturas siguen presentes hasta la limpieza del finally.
    const borrado = lecturas.deleteOne({_id: uno.insertedId});
    verificar("deleteOne", borrado.deletedCount === 1 && lecturas.findOne({_id: uno.insertedId}) === null);
  // LIMPIEZA: esta es una accion auxiliar de la demostracion, no una octava operacion
  // exigida. Elimina la base temporal completa, incluidas las dos lecturas restantes.
  } finally {
    // El nombre es generado aqui, nunca corresponde a smartcity ni a una base del usuario.
    const limpieza = demo.dropDatabase();
    if (limpieza.ok !== 1) throw new Error("No se pudo limpiar " + nombre);
    print("Base temporal eliminada: " + nombre);
  }
  // RESULTADO FINAL: siete operaciones aprobadas y limpieza confirmada.
  // Si alguna comprobacion lanzo un error, la ejecucion no llega a este resumen.
  // Se puede pegar y ejecutar de nuevo: usara otra base temporal independiente.
  printjson({aprobado: pasos.length === 7, operaciones: pasos});
})();
