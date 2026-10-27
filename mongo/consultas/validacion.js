(() => {
"use strict";
const M=globalThis.SC;
const COLECCIONES=["lecturas","eventos","alertas","incidentes"];
function aislada(conexion,accion) {
  const nombre="smartcity_personad_pruebas_"+require("crypto").randomUUID().replaceAll("-","");
  const prueba=conexion.getSiblingDB(nombre);
  if (prueba.getCollectionNames().length) throw Error("La base temporal ya existe");
  try {return {base_temporal:nombre,resultado:accion(prueba)};}
  finally {prueba.dropDatabase();}
}
function inventario(base) {
  const existentes=base.getCollectionNames(), colecciones={};
  for (const nombre of COLECCIONES) {
    if (!existentes.includes(nombre)) {colecciones[nombre]={existe:false,cantidad:0};continue;}
    const c=base.getCollection(nombre),fecha=nombre==="incidentes"?"fecha_reporte":"timestamp";
    colecciones[nombre]={existe:true,cantidad:c.countDocuments({}),indices:c.getIndexes(),
      fechas:c.aggregate([{$group:{_id:null,primera:{$min:"$"+fecha},ultima:{$max:"$"+fecha}}}]).toArray(),
      tipos_fecha:c.aggregate([{$group:{_id:{$type:"$"+fecha},cantidad:{$sum:1}}}]).toArray()};
  }
  return {base:base.getName(),version:base.version(),colecciones,
    tipos_sensores:existentes.includes("lecturas")?base.lecturas.distinct("tipo"):[],
    nota_fechas:"Fechas almacenadas sin desplazamiento adicional; cargador sin zona explicita.",
    volumen_minimo_cumplido:Object.values(colecciones).reduce((s,c)=>s+c.cantidad,0)>=500000};
}
function firma(base) {
  const h=base.runCommand({dbHash:1,collections:COLECCIONES});
  if (!h.ok) throw Error("No se pudo verificar dbHash");
  return {colecciones:h.collections,indices:Object.fromEntries(COLECCIONES.map(n=>[n,base.getCollection(n).getIndexes()]))};
}
function estable(x) {
  if (x instanceof Date) return x.toISOString();
  if (x && typeof x.toHexString==="function") return x.toHexString();
  if (Array.isArray(x)) return x.map(estable);
  if (x && typeof x==="object") return Object.fromEntries(Object.keys(x).sort().map(k=>[k,estable(x[k])]));
  return x;
}
const clave=x=>JSON.stringify(estable(x));
function acumular(m,id,valor) {
  const k=clave(id);
  if (!m.has(k)) m.set(k,{_id:id,cantidad:0,suma:0,minimo:Infinity,maximo:-Infinity});
  const a=m.get(k);a.cantidad++;a.suma+=valor;a.minimo=Math.min(a.minimo,valor);a.maximo=Math.max(a.maximo,valor);
}
function contar(m,id) {const k=clave(id);if(!m.has(k))m.set(k,{_id:id,cantidad:0});m.get(k).cantidad++;}
function promedio(m) {return [...m.values()].map(({suma,...x})=>({...x,promedio:suma/x.cantidad}));}
function cerca(a,b) {return Number.isFinite(a) && Number.isFinite(b) && Math.abs(a-b)<=1e-9*Math.max(1,Math.abs(a),Math.abs(b));}
function igualesGrupos(actual,esperado,campos) {
  const mapa=new Map(esperado.map(x=>[clave(x._id),x]));
  return actual.length===esperado.length && new Set(actual.map(x=>clave(x._id))).size===actual.length && actual.every(x=>{
    const e=mapa.get(clave(x._id));return e && campos.every(k=>typeof e[k]==="number"?cerca(Number(x[k]),e[k]):clave(x[k])===clave(e[k]));
  });
}

// Oraculo independiente: recorre BSON crudo y calcula con JavaScript, sin reutilizar pipelines de lib.js.
function referencia(base,p) {
  const extremos=new Map(),zonas=new Map(),tipos=new Map(),sensores=new Map(),dias=new Map(),contaminacion=new Map();
  const umbrales=[];
  let documentos=0;
  for (const d of base.lecturas.find({timestamp:{$gte:p.desde,$lt:p.hasta}},
    {id_sensor:1,tipo:1,ubicacion:1,timestamp:1,medicion:1,valido:1,invalidos:1}).batchSize(5000)) {
    documentos++;contar(sensores,d.id_sensor);
    const malos=Array.isArray(d.invalidos)?d.invalidos:[];
    if (d.valido===false && malos.length===0) continue;
    if (!d.medicion || typeof d.medicion!=="object" || Array.isArray(d.medicion)) continue;
    for (const [variable,valor] of Object.entries(d.medicion)) {
      if (typeof valor!=="number" || !Number.isFinite(valor) || malos.includes(variable) || !Object.hasOwn(M.UNIDADES,variable)) continue;
      const unidad=M.UNIDADES[variable],distrito=d.ubicacion?.distrito;
      acumular(extremos,{variable,unidad},valor);
      acumular(zonas,{distrito,variable,unidad},valor);
      acumular(tipos,{tipo:d.tipo,variable,unidad},valor);
      if (d.tipo==="calidad_aire" && variable==="no2") acumular(contaminacion,{distrito,variable,unidad},valor);
      if (d.tipo==="meteorologico" && variable==="temperatura") acumular(dias,{dia:d.timestamp.toISOString().slice(0,10),distrito,variable,unidad},valor);
      if (d.tipo==="trafico" && distrito==="Centro" && variable==="carga" && valor>80) {
        umbrales.push({_id:d._id,id_sensor:d.id_sensor,tipo:d.tipo,distrito,timestamp:d.timestamp,variable,unidad,valor});
      }
    }
  }
  umbrales.sort((a,b)=>b.valor-a.valor || a.timestamp-b.timestamp || clave(a._id).localeCompare(clave(b._id)));
  const alertas=new Map(),limites=new Map();
  for (const d of base.alertas.find({timestamp:{$gte:p.desde,$lt:p.hasta}})) {
    contar(alertas,{distrito:d.ubicacion?.distrito,nivel:d.nivel});
    if (typeof d.valor!=="number" || typeof d.limite!=="number" || !(d.valor>d.limite)) continue;
    const id={sensor:d.id_sensor,variable:d.variable},k=clave(id);
    if(!limites.has(k)) limites.set(k,{_id:id,cantidad:0,maximo:-Infinity,primera:d.timestamp,ultima:d.timestamp});
    const a=limites.get(k);a.cantidad++;a.maximo=Math.max(a.maximo,d.valor);
    if(d.timestamp<a.primera)a.primera=d.timestamp;if(d.timestamp>a.ultima)a.ultima=d.timestamp;
  }
  const incidentes=new Map(),heridos=[];
  for(const d of base.incidentes.find({fecha_reporte:{$gte:p.desde,$lt:p.hasta}})) {
    contar(incidentes,{categoria:d.categoria,estado:d.estado});
    if(d.categoria==="accidente_transito" && typeof d.datos_extra?.heridos==="number" && d.datos_extra.heridos>0) heridos.push(d);
  }
  heridos.sort((a,b)=>a.fecha_reporte-b.fecha_reporte || clave(a._id).localeCompare(clave(b._id)));
  return {documentos,extremos:promedio(extremos),zonas:promedio(zonas),tipos:promedio(tipos),sensores:[...sensores.values()],
    dias:promedio(dias),contaminacion:promedio(contaminacion),umbrales:umbrales.slice(0,100),alertas:[...alertas.values()],
    limites:[...limites.values()],incidentes:[...incidentes.values()],heridos:heridos.slice(0,100)};
}
function resumenPlan(plan) {
  const etapas=new Set(),indices=new Set();let documentos=0,claves=0,resultados=0,ms=0;
  function visitar(n) {
    if(!n || typeof n!=="object")return;
    if(n.stage)etapas.add(n.stage);if(n.indexName)indices.add(n.indexName);
    documentos=Math.max(documentos,n.totalDocsExamined||0);claves=Math.max(claves,n.totalKeysExamined||0);
    resultados=Math.max(resultados,n.nReturned||0);ms=Math.max(ms,n.executionTimeMillis||0);
    for(const [k,v] of Object.entries(n))if(!["rejectedPlans","allPlansExecution"].includes(k))visitar(v);
  }
  visitar(plan);return {etapas:[...etapas],indices:[...indices],documentos_examinados:documentos,
    claves_examinadas:claves,max_filas_etapa:resultados,duracion_cursor_ms:ms};
}
function explicar(base,s) {
  const cmd=s.operacion==="find"?{find:s.coleccion,filter:s.filtro,projection:s.proyeccion,sort:s.orden,limit:s.limite}:
    {aggregate:s.coleccion,pipeline:s.pipeline,cursor:{},allowDiskUse:true};
  const plan=base.runCommand({explain:cmd,verbosity:"executionStats"});
  if(!plan.ok)throw Error("No se pudo obtener explain");
  return {consulta:s,resumen:resumenPlan(plan),plan};
}
function completa(base,comprobar) {
  const antes=firma(base), inv=inventario(base),p=M.parametros();
  comprobar("cuatro colecciones disponibles",COLECCIONES.every(n=>inv.colecciones[n].existe));
  comprobar("minimo 500000 documentos",inv.volumen_minimo_cumplido);
  comprobar("fechas BSON en todas las colecciones",COLECCIONES.every(n=>Array.isArray(inv.colecciones[n].tipos_fecha) && inv.colecciones[n].tipos_fecha.every(t=>t._id==="date")));
  const resultados={},consultas=[];
  for(let n=1;n<=15;n++) {
    const s=M.construir(n,{},base),inicio=Date.now();
    const filas=M.ejecutar(base,s);resultados[n]=filas;
    consultas.push({consulta:s,duracion_ms:Date.now()-inicio,filas:filas.length,muestra:filas.slice(0,5)});
    comprobar("consulta "+n+" ejecutada",Array.isArray(filas));
  }
  const ref=referencia(base,p),estadisticas=["cantidad","minimo","maximo","promedio"];
  for(const [n,esperado,campos] of [
    [3,ref.extremos,estadisticas],[5,ref.alertas,["cantidad"]],[6,ref.zonas,estadisticas],
    [7,ref.tipos,estadisticas],[8,ref.incidentes,["cantidad"]],[9,ref.sensores,["cantidad"]],
    [11,ref.zonas.filter(x=>x._id.variable==="temperatura"),estadisticas],
    [12,ref.limites,["cantidad","maximo","primera","ultima"]],[13,ref.contaminacion,estadisticas],[14,ref.dias,estadisticas]
  ]) comprobar("consulta "+n+" coincide con calculo independiente",igualesGrupos(resultados[n],esperado,campos));
  comprobar("consulta 10 coincide con filtro y orden independientes",clave(resultados[10])===clave(ref.umbrales));
  comprobar("consulta 15 coincide con seleccion independiente",clave(resultados[15].map(x=>x._id))===clave(ref.heridos.map(x=>x._id)));
  const s1=consultas[0].consulta;
  comprobar("consulta 1 conteo y pertenencia",!s1.vacio && resultados[1].length===Math.min(100,base.lecturas.countDocuments(s1.filtro)) &&
    resultados[1].every(x=>x.id_sensor===s1.parametros.sensor && x.timestamp>=p.desde && x.timestamp<p.hasta));
  comprobar("consulta 2 cuenta periodo y respeta fechas",resultados[2].length===Math.min(100,ref.documentos) && resultados[2].every(x=>x.timestamp>=p.desde && x.timestamp<p.hasta));
  comprobar("consulta 4 selecciona eventos criticos",resultados[4].length===Math.min(100,base.eventos.countDocuments({timestamp:{$gte:p.desde,$lt:p.hasta},severidad:"critica"})) &&
    resultados[4].every(x=>x.severidad==="critica" && x.timestamp>=p.desde && x.timestamp<p.hasta));
  comprobar("ranking ordenado por promedio",resultados[13].every((x,i,a)=>i===0 || a[i-1].promedio>=x.promedio));
  comprobar("conteo de sensores coincide con documentos crudos",resultados[9].reduce((s,x)=>s+x.cantidad,0)===ref.documentos);
  const planes=[explicar(base,s1),explicar(base,M.construir(6,{tipo:"calidad_aire",variable:"no2"},base)),
    explicar(base,M.construir(5,{nivel:"critica"},base))];
  for(const [i,nombre] of ["sensor/fecha","tipo/fecha","alertas criticas/distrito"].entries()) {
    comprobar("explain "+nombre+" ejecutado",planes[i].plan.ok===1);
  }
  const despues=firma(base);
  comprobar("documentos e indices originales intactos (dbHash)",clave(antes)===clave(despues));
  return {inventario:inv,consultas,documentos_periodo:ref.documentos,planes,integridad:{antes,despues},
    advertencias:planes.filter(x=>!x.resumen.indices.length).map(x=>"El optimizador no eligio indice para "+x.consulta.titulo)};
}
function correr(base,modo) {
  const informe={fecha:new Date(),modo,base:base.getName(),version:base.version(),comprobaciones:[]};
  function comprobar(nombre,condicion) {informe.comprobaciones.push({nombre,aprobado:Boolean(condicion)});}
  const inicio=Date.now();
  try {
    if(modo==="comprobar")informe.inventario=inventario(base);
    else if(modo==="consultas")informe.consultas=Array.from({length:15},(_,i)=>{
      const s=M.construir(i+1,{},base),t=Date.now(),r=M.ejecutar(base,s);
      return {consulta:s,duracion_ms:Date.now()-t,filas:r.length,muestra:r.slice(0,5)};
    });
    else if(modo==="crud")informe.crud=aislada(base,b=>globalThis.SC_CRUD.demostrar(b));
    else if(["controladas","completa","todo"].includes(modo)) {
      if(modo!=="completa")informe.controladas=aislada(base,b=>globalThis.SC_TEST.probar(b,comprobar));
      if(modo!=="controladas")informe.completa=completa(base,comprobar);
    } else throw Error("Modo no soportado");
  } catch(e) {informe.error=e.stack || String(e);}
  informe.duracion_ms=Date.now()-inicio;
  informe.aprobado=!informe.error && informe.comprobaciones.every(x=>x.aprobado);
  informe.resumen={aprobadas:informe.comprobaciones.filter(x=>x.aprobado).length,fallidas:informe.comprobaciones.filter(x=>!x.aprobado).length};
  return informe;
}
globalThis.SC_VALIDACION={aislada,inventario,correr,completa,referencia};

})();
