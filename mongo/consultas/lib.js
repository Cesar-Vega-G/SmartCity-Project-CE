(() => {
"use strict";
// Funciones compartidas por mongosh, Compass y las pruebas. No abre conexiones ni escribe.
const UNIDADES = Object.freeze({no2:"ug/m3", pm10:"ug/m3", pm25:"ug/m3", co:"mg/m3",
  o3:"ug/m3", temperatura:"C", humedad:"%", precipitacion:"mm", ruido_db:"dB",
  intensidad:"veh/h", ocupacion:"%", carga:"0-100", velocidad:"km/h",
  ocupacion_parking:"%", consumo_kwh:"kWh"});
const TITULOS = [null, "Lecturas de un sensor", "Lecturas en un rango de fechas",
  "Maximos y minimos por variable", "Eventos criticos", "Alertas por zona",
  "Promedio por zona y variable", "Promedio por tipo y variable", "Incidentes por categoria y estado",
  "Cantidad de lecturas por sensor", "Filtros multiples", "Temperatura promedio por zona",
  "Sensores que superaron limites", "Ranking de contaminacion", "Evolucion diaria",
  "Incidentes con personas heridas"];

function parametros(entrada = {}) {
  const p = {desde:new Date("2026-07-01T00:00:00Z"), hasta:new Date("2026-08-01T00:00:00Z"),
    limite:100, ...entrada};
  for (const k of ["desde", "hasta"]) {
    if (!(p[k] instanceof Date) || !Number.isFinite(p[k].getTime())) throw Error(k+" debe ser una fecha BSON/Date valida");
  }
  if (p.desde >= p.hasta) throw Error("El inicio debe ser anterior al fin exclusivo");
  if (!Number.isInteger(p.limite) || p.limite < 1 || p.limite > 100) throw Error("limite debe estar entre 1 y 100");
  if (p.variable != null && !Object.hasOwn(UNIDADES, p.variable)) throw Error("Variable desconocida: "+p.variable);
  for (const k of ["sensor", "distrito", "tipo", "tipoEvento", "nivel"]) {
    if (p[k] != null && (typeof p[k] !== "string" || !p[k].length)) throw Error(k+" debe ser texto no vacio");
  }
  if (p.umbral != null && (typeof p.umbral !== "number" || !Number.isFinite(p.umbral))) throw Error("umbral debe ser numerico y finito");
  return p;
}
function filtro(p, fecha="timestamp") {
  const f = {[fecha]:{$gte:p.desde, $lt:p.hasta}};
  if (p.sensor != null) f.id_sensor = p.sensor;
  if (p.distrito != null) f["ubicacion.distrito"] = p.distrito;
  return f;
}
const PROYECCION = {_id:1,id_sensor:1,tipo:1,ubicacion:1,medicion:1,timestamp:1,valido:1,invalidos:1};

// No se descarta una variable sana porque otra variable del mismo documento sea invalida.
// valido:false sin una lista NO VACIA de invalidos no ofrece calidad suficiente.
function valores(p) {
  const f = filtro(p);
  if (p.tipo != null) f.tipo = p.tipo;
  if (p.variable != null) f["medicion."+p.variable] = {$exists:true};
  return [
    {$match:f},
    {$set:{_invalidos:{$cond:[{$isArray:"$invalidos"},"$invalidos",[]]}}},
    {$match:{$expr:{$or:[{$ne:["$valido",false]},{$gt:[{$size:"$_invalidos"},0]}]}}},
    {$project:{id_sensor:1,tipo:1,ubicacion:1,timestamp:1,_invalidos:1,
      par:{$objectToArray:{$cond:[{$eq:[{$type:"$medicion"},"object"]},"$medicion",{}]}}}},
    {$unwind:"$par"},
    {$match:{$expr:{$and:[{$isNumber:"$par.v"},{$not:[{$in:["$par.k","$_invalidos"]}]}]},
      "par.k":p.variable || {$in:Object.keys(UNIDADES)}}},
    {$set:{unidad:{$switch:{branches:Object.entries(UNIDADES).map(([k,v])=>({case:{$eq:["$par.k",k]},then:v})),default:"desconocida"}}}}
  ];
}
function estadistica(id, orden) {
  return [{$group:{_id:id,cantidad:{$sum:1},promedio:{$avg:"$par.v"},minimo:{$min:"$par.v"},maximo:{$max:"$par.v"}}},
    {$sort:orden}];
}
function construir(numero, entrada={}, base) {
  if (!Number.isInteger(numero) || !TITULOS[numero]) throw Error("Consulta inexistente");
  const defaults = numero === 10 ? {tipo:"trafico",distrito:"Centro",variable:"carga",umbral:80} :
    numero === 11 ? {variable:"temperatura"} : numero === 13 ? {tipo:"calidad_aire",variable:"no2"} :
    numero === 14 ? {tipo:"meteorologico",variable:"temperatura"} : {};
  const p = parametros({...defaults,...entrada});
  if (numero === 11 && p.variable !== "temperatura") throw Error("La consulta 11 es de temperatura");
  if (numero === 13 && !["no2","pm10","pm25","co","o3"].includes(p.variable)) throw Error("Elegir un contaminante");
  const s = {numero,titulo:TITULOS[numero],parametros:p,coleccion:"lecturas",operacion:"aggregate"};
  switch(numero) {
    case 1: {
      if (!p.sensor) {
        if (!base) throw Error("Indicar sensor o proporcionar la base para elegir uno existente");
        const candidato = base.lecturas.find(filtro(p),{id_sensor:1}).sort({id_sensor:1}).limit(1).toArray()[0];
        if (!candidato) {s.vacio=true; break;}
        p.sensor=candidato.id_sensor;
      }
      s.operacion="find"; s.filtro=filtro(p); s.proyeccion=PROYECCION; s.orden={timestamp:1,_id:1}; s.limite=p.limite; break;
    }
    case 2:
      s.operacion="find"; s.filtro=filtro(p); s.proyeccion=PROYECCION; s.orden={timestamp:1,_id:1}; s.limite=p.limite; break;
    case 3:
      s.pipeline=[...valores(p), ...estadistica({variable:"$par.k",unidad:"$unidad"},{"_id.variable":1})]; break;
    case 4:
      s.coleccion="eventos"; s.operacion="find"; s.filtro={...filtro(p),severidad:"critica"};
      if (p.tipoEvento) s.filtro.tipo_evento=p.tipoEvento;
      s.proyeccion={id_sensor:1,tipo_evento:1,severidad:1,ubicacion:1,timestamp:1,detalles:1};
      s.orden={timestamp:-1,_id:1}; s.limite=p.limite; break;
    case 5:
      s.coleccion="alertas";
      s.pipeline=[{$match:{...filtro(p),...(p.nivel ? {nivel:p.nivel}: {})}},
        {$group:{_id:{distrito:"$ubicacion.distrito",nivel:"$nivel"},cantidad:{$sum:1}}},
        {$sort:{cantidad:-1,"_id.distrito":1,"_id.nivel":1}}]; break;
    case 6: case 11: case 13:
      s.pipeline=[...valores(p),...estadistica({distrito:"$ubicacion.distrito",variable:"$par.k",unidad:"$unidad"},
        numero===13 ? {promedio:-1,"_id.distrito":1} : {"_id.distrito":1,"_id.variable":1})]; break;
    case 7:
      s.pipeline=[...valores(p),...estadistica({tipo:"$tipo",variable:"$par.k",unidad:"$unidad"},{"_id.tipo":1,"_id.variable":1})]; break;
    case 8:
      s.coleccion="incidentes";
      s.pipeline=[{$match:filtro(p,"fecha_reporte")},{$group:{_id:{categoria:"$categoria",estado:"$estado"},cantidad:{$sum:1}}},
        {$sort:{cantidad:-1,"_id.categoria":1,"_id.estado":1}}]; break;
    case 9:
      s.pipeline=[{$match:filtro(p)},{$group:{_id:"$id_sensor",cantidad:{$sum:1}}},{$sort:{cantidad:-1,_id:1}}]; break;
    case 10:
      s.pipeline=[...valores(p),{$match:{"par.v":{$gt:p.umbral}}},
        {$project:{id_sensor:1,tipo:1,distrito:"$ubicacion.distrito",timestamp:1,variable:"$par.k",unidad:1,valor:"$par.v"}},
        {$sort:{valor:-1,timestamp:1,_id:1}},{$limit:p.limite}]; break;
    case 12:
      s.coleccion="alertas";
      s.pipeline=[{$match:{...filtro(p),valor:{$type:"number"},limite:{$type:"number"},
        ...(p.variable ? {variable:p.variable}:{}),$expr:{$gt:["$valor","$limite"]}}},
        {$group:{_id:{sensor:"$id_sensor",variable:"$variable"},cantidad:{$sum:1},maximo:{$max:"$valor"},
          primera:{$min:"$timestamp"},ultima:{$max:"$timestamp"}}},{$sort:{cantidad:-1,"_id.sensor":1,"_id.variable":1}}]; break;
    case 14:
      s.pipeline=[...valores(p),...estadistica({dia:{$dateToString:{date:"$timestamp",format:"%Y-%m-%d",timezone:"UTC"}},
        distrito:"$ubicacion.distrito",variable:"$par.k",unidad:"$unidad"},{"_id.dia":1,"_id.distrito":1,"_id.variable":1})]; break;
    case 15:
      s.coleccion="incidentes"; s.operacion="find";
      s.filtro={...filtro(p,"fecha_reporte"),categoria:{$in:["accidente_transito"]},
        $and:[{"datos_extra.heridos":{$exists:true}},{"datos_extra.heridos":{$type:"number",$gt:0}}]};
      s.proyeccion={categoria:1,estado:1,ubicacion:1,fecha_reporte:1,datos_extra:1};
      s.orden={fecha_reporte:1,_id:1}; s.limite=p.limite; break;
  }
  return s;
}
function cursor(base,s) {
  const c=base.getCollection(s.coleccion);
  return s.operacion === "find" ? c.find(s.filtro,s.proyeccion).sort(s.orden).limit(s.limite) :
    c.aggregate(s.pipeline,{allowDiskUse:true});
}
function ejecutar(base,s) {return s.vacio ? [] : cursor(base,s).toArray();}
function mostrar(base,numero,entrada={}) {
  const s=construir(numero,entrada,base);
  const inicio=Date.now(), resultados=ejecutar(base,s);
  print(EJSON.stringify({consulta:s,duracion_ms:Date.now()-inicio,resultados},null,2));
}
globalThis.SC={UNIDADES,TITULOS,parametros,filtro,construir,cursor,ejecutar,mostrar};

})();
