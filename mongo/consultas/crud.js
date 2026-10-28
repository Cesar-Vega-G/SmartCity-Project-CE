// Compass > Open MongoDB Shell: pegar este archivo completo y pulsar Enter.
// Las siete operaciones se realizan en una base temporal exclusiva de esta ejecucion.
(() => {
  const nombre = "smartcity_demo_" + new ObjectId().toHexString();
  const demo = db.getSiblingDB(nombre);
  const lecturas = demo.getCollection("lecturas");
  const pasos = [];
  function verificar(operacion, condicion) {
    if (!condicion) throw new Error("Fallo: " + operacion);
    pasos.push(operacion);
    print("OK: " + operacion);
  }
  function lectura(sensor, medicion) {
    return {id_sensor: sensor, tipo: "meteorologico",
      ubicacion: {distrito: "Centro"}, timestamp: ISODate("2026-07-01T00:00:00Z"),
      medicion: medicion, valido: true};
  }
  try {
    const uno = lecturas.insertOne(lectura("DEMO-1", {temperatura: 20}));
    verificar("insertOne", uno.acknowledged && lecturas.countDocuments({}) === 1);

    const varios = lecturas.insertMany([
      lectura("DEMO-2", {temperatura: 30, humedad: 60}),
      lectura("DEMO-3", {precipitacion: 5})
    ]);
    verificar("insertMany", varios.acknowledged && lecturas.countDocuments({}) === 3);

    const encontrados = lecturas.find({"medicion.temperatura": {$gte: 20}},
      {_id: 0, id_sensor: 1, medicion: 1}).sort({id_sensor: 1}).toArray();
    printjson(encontrados);
    verificar("find", encontrados.length === 2);
    verificar("findOne", lecturas.findOne({_id: uno.insertedId}).medicion.temperatura === 20);

    const cambio = lecturas.updateOne({_id: uno.insertedId}, {$set: {"medicion.temperatura": 21}});
    verificar("updateOne", cambio.modifiedCount === 1 &&
      lecturas.findOne({_id: uno.insertedId}).medicion.temperatura === 21);
    const cambios = lecturas.updateMany({}, {$set: {revisada: true}});
    verificar("updateMany", cambios.modifiedCount === 3 && lecturas.countDocuments({revisada: true}) === 3);

    const borrado = lecturas.deleteOne({_id: uno.insertedId});
    verificar("deleteOne", borrado.deletedCount === 1 && lecturas.findOne({_id: uno.insertedId}) === null);
  } finally {
    // El nombre es generado aqui, nunca corresponde a smartcity ni a una base del usuario.
    const limpieza = demo.dropDatabase();
    if (limpieza.ok !== 1) throw new Error("No se pudo limpiar " + nombre);
    print("Base temporal eliminada: " + nombre);
  }
  printjson({aprobado: pasos.length === 7, operaciones: pasos});
})();
