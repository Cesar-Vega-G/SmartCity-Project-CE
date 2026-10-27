(() => {
"use strict";
// Demuestra las siete operaciones sobre una coleccion de prueba con el mismo modelo.
// Cada ejecucion es duena solamente de los documentos con su identificador corrida.
function demostrar(base) {
  if (!base.getName().startsWith("smartcity_personad_pruebas_")) throw Error("CRUD requiere base aislada de Persona D");
  const c=base.getCollection("lecturas_crud"), corrida=require("crypto").randomUUID();
  const pasos=[];
  function verificar(nombre,condicion) {if (!condicion) throw Error("CRUD: "+nombre); pasos.push(nombre);}
  function doc(sensor,medicion) {return {corrida,id_sensor:sensor,tipo:"meteorologico",categoria:"ambiente",
    ubicacion:{distrito:"Centro",nombre:"Demostracion"},timestamp:new Date("2026-07-01T00:00:00Z"),medicion,valido:true};}
  try {
    const uno=c.insertOne(doc("DEMO-1",{temperatura:20}));
    verificar("insertOne",uno.acknowledged && c.countDocuments({corrida})===1);
    const varios=c.insertMany([doc("DEMO-2",{temperatura:30,humedad:60}),doc("DEMO-3",{precipitacion:5})]);
    verificar("insertMany",varios.acknowledged && Object.keys(varios.insertedIds).length===2);
    verificar("find",c.find({corrida,"medicion.temperatura":{$gte:20}},{id_sensor:1,_id:0}).sort({id_sensor:1}).toArray().length===2);
    verificar("findOne",c.findOne({_id:uno.insertedId,corrida}).medicion.temperatura===20);
    const actualizada=c.updateOne({_id:uno.insertedId,corrida},{$set:{"medicion.temperatura":21}});
    verificar("updateOne",actualizada.matchedCount===1 && actualizada.modifiedCount===1 && c.findOne({_id:uno.insertedId}).medicion.temperatura===21);
    const todas=c.updateMany({corrida},{$set:{revisada:true}});
    verificar("updateMany",todas.matchedCount===3 && todas.modifiedCount===3 && c.countDocuments({corrida,revisada:true})===3);
    const eliminada=c.deleteOne({_id:uno.insertedId,corrida});
    verificar("deleteOne",eliminada.deletedCount===1 && c.findOne({_id:uno.insertedId})===null);
  } finally {
    c.deleteMany({corrida});
  }
  verificar("limpieza",c.countDocuments({corrida})===0);
  return {pasos,documentos_restantes:0};
}
globalThis.SC_CRUD={demostrar};

})();
