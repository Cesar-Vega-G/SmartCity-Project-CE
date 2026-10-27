(() => {
"use strict";
const M=globalThis.SC;
const CRUD=globalThis.SC_CRUD;
function probar(base,comprobar) {
  const inicio=new Date("2026-07-01T00:00:00Z"), fin=new Date("2026-08-01T00:00:00Z");
  const t=h=>new Date(inicio.getTime()+h*3600000);
  const lectura=(id,medicion,extra={})=>({_id:id,id_sensor:"A",tipo:"meteorologico",ubicacion:{distrito:"Centro"},timestamp:inicio,valido:true,medicion,...extra});
  const docs=[lectura("a1",{temperatura:20,humedad:40}),
    lectura("a2",{temperatura:30,humedad:999},{timestamp:t(1),valido:false,invalidos:["humedad"]}),
    lectura("a3",{temperatura:1000},{timestamp:t(2),valido:false}),
    lectura("a4",{temperatura:999},{timestamp:t(3),valido:false,invalidos:[]}),
    lectura("a5",{temperatura:null,humedad:"mala"},{timestamp:t(4)}),
    lectura("a6",null,{timestamp:t(5)}),
    lectura("antes",{temperatura:-99},{timestamp:t(-1)}),lectura("fin",{temperatura:999},{timestamp:fin}),
    lectura("b1",{no2:100,co:2,pm25:10},{id_sensor:"B",tipo:"calidad_aire"}),
    lectura("b2",{no2:300,co:4},{id_sensor:"B",tipo:"calidad_aire",ubicacion:{distrito:"Salamanca"},valido:false,invalidos:["no2"]}),
    lectura("c1",{carga:80,intensidad:100},{id_sensor:"C",tipo:"trafico"}),
    lectura("c2",{carga:81,intensidad:200},{id_sensor:"C",tipo:"trafico",timestamp:t(1)}),
    lectura("d1",{temperatura:10,humedad:50},{id_sensor:"D",ubicacion:{distrito:"Salamanca"},timestamp:t(24)}),
    lectura("a9","no es objeto",{timestamp:t(6)}),
    lectura("a10",{temperatura:88},{timestamp:t(7),valido:false,invalidos:"temperatura"})];
  delete docs[5].medicion;
  base.lecturas.insertMany(docs);
  base.eventos.insertMany([
    {_id:"e1",timestamp:inicio,severidad:"critica",tipo_evento:"pico_contaminacion",detalles:{no2:301}},
    {_id:"e2",timestamp:inicio,severidad:"alta",nivel:"critica",tipo_evento:"congestion"},
    {_id:"e3",timestamp:fin,severidad:"critica"}]);
  base.alertas.insertMany([200,201,301].map((valor,i)=>({_id:"l"+i,id_sensor:"B",timestamp:inicio,variable:"no2",valor,limite:200,
    nivel:i===2?"critica":"advertencia",ubicacion:{distrito:"Centro"}})));
  base.incidentes.insertMany([
    {_id:"i1",fecha_reporte:inicio,categoria:"accidente_transito",estado:"cerrado",datos_extra:{heridos:1}},
    {_id:"i2",fecha_reporte:inicio,categoria:"accidente_transito",estado:"abierto",datos_extra:{heridos:0}},
    {_id:"i3",fecha_reporte:inicio,categoria:"inundacion",estado:"abierto",datos_extra:{nivel_agua_cm:30}},
    {_id:"i4",fecha_reporte:fin,categoria:"accidente_transito",estado:"cerrado",datos_extra:{heridos:2}}]);
  const q=(n,p={})=>M.ejecutar(base,M.construir(n,p,base));
  const temp=q(3).find(x=>x._id.variable==="temperatura");
  comprobar("estadisticas con valores sanos de documentos parcialmente invalidos",temp.cantidad===3 && temp.promedio===20 && temp.minimo===10 && temp.maximo===30);
  const co=q(3).find(x=>x._id.variable==="co");
  comprobar("variables y unidades separadas",co.cantidad===2 && co.promedio===3 && co._id.unidad==="mg/m3");
  comprobar("variable explicitamente invalida excluida",q(3).find(x=>x._id.variable==="no2").cantidad===1);
  const a=q(1,{sensor:"A"});
  comprobar("inicio incluido y fin excluido",a.length===8 && a.some(x=>x._id==="a1") && !a.some(x=>["antes","fin"].includes(x._id)));
  comprobar("detalle conserva invalidos y proyeccion",a.find(x=>x._id==="a2").invalidos[0]==="humedad" && !Object.hasOwn(a[0],"categoria"));
  comprobar("rango completo cuenta documentos",q(2).length===13);
  comprobar("sensor inexistente",q(1,{sensor:"NO_EXISTE"}).length===0);
  comprobar("distrito inexistente",q(6,{distrito:"NO_EXISTE"}).length===0);
  comprobar("severidad de eventos independiente del nivel",q(4).length===1 && q(4)[0]._id==="e1");
  comprobar("filtro de tipo de evento",q(4,{tipoEvento:"congestion"}).length===0);
  comprobar("alertas por distrito y nivel",q(5).length===2 && q(5)[0].cantidad===2);
  const centro=q(6,{variable:"temperatura"}).find(x=>x._id.distrito==="Centro");
  comprobar("promedio por zona",centro.cantidad===2 && centro.promedio===25);
  comprobar("promedio por tipo y variable",q(7).find(x=>x._id.tipo==="meteorologico" && x._id.variable==="temperatura").promedio===20);
  comprobar("incidentes usan fecha_reporte y estados separados",q(8).length===3 && q(8).reduce((s,x)=>s+x.cantidad,0)===3);
  comprobar("conteo documental no cuenta variables",q(9).find(x=>x._id==="A").cantidad===8 && q(9).reduce((s,x)=>s+x.cantidad,0)===13);
  comprobar("umbral estricto y filtros multiples",q(10).length===1 && q(10)[0].valor===81);
  comprobar("temperatura reutiliza consulta 6",JSON.stringify(q(11))===JSON.stringify(q(6,{variable:"temperatura"})));
  comprobar("comparacion valor > limite entre campos",q(12).length===1 && q(12)[0].cantidad===2 && q(12)[0].maximo===301);
  comprobar("ranking solo del contaminante elegido",q(13).length===1 && q(13)[0].promedio===100);
  comprobar("serie diaria sin ceros inventados",q(14).length===2 && q(14)[0]._id.dia==="2026-07-01" && q(14)[1]._id.dia==="2026-07-02");
  comprobar("campo dinamico de incidentes",q(15).length===1 && q(15)[0]._id==="i1");
  for (const p of [{desde:fin,hasta:inicio},{desde:"2026-07-01"},{variable:"xyz"},{limite:0},{limite:101},{umbral:"80"}]) {
    let fallo=false;try{M.parametros(p);}catch{fallo=true;}comprobar("rechaza parametros invalidos "+JSON.stringify(p),fallo);
  }
  const copias=Array.from({length:105},(_,i)=>lectura("limite"+i,{temperatura:i},{id_sensor:"LIMITE"}));
  base.lecturas.insertMany(copias);
  comprobar("detalle limita a 100 y agregacion procesa 105",q(1,{sensor:"LIMITE"}).length===100 && q(3,{sensor:"LIMITE"})[0].cantidad===105);
  const cru1=CRUD.demostrar(base), cru2=CRUD.demostrar(base);
  comprobar("CRUD repetible, siete operaciones y limpieza",cru1.pasos.length===8 && cru2.pasos.length===8 && base.lecturas_crud.countDocuments({})===0);
  // La base es unica de esta ejecucion. Vaciar fixtures permite probar todas las consultas sin datos.
  for (const col of ["lecturas","eventos","alertas","incidentes"]) base.getCollection(col).deleteMany({});
  for (let n=1;n<=15;n++) comprobar("consulta "+n+" sobre coleccion vacia",q(n).length===0);
  return {casos:docs.length,crud:cru1};
}
globalThis.SC_TEST={probar};

})();
