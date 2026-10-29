// Obligatoria 9: consulta utilizando agregaciones.
// Coleccion: smartcity.lecturas. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Ranking de documentos por sensor. Tres variables en un documento cuentan como UNO.
// Cada etapa recibe la salida de la anterior. Los comentarios explican ese recorrido.
// Solo lectura: $set y $project transforman el resultado, no los documentos guardados.
// Periodo: julio de 2026. Editar ISODate en el primer $match para cambiarlo.
// Se consulta el tiempo almacenado en UTC sin corregir la zona horaria de la ingesta.
[
  // ETAPA 1 — $match
  // Filtrar al inicio reduce los documentos que pasan a las etapas siguientes.
  // Puede aprovechar un indice compatible; comprobarlo con Explain, no asumirlo.
  // $gte incluye el inicio y $lt excluye el fin: evita duplicar fronteras entre meses.
  // ISODate crea fechas BSON, no cadenas de texto.
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      }
    }
  },
  // ETAPA 2 — $group
  // Agrupar por id_sensor y sumar uno por DOCUMENTO, sin $unwind.
  // Incluye lecturas marcadas invalidas: mide actividad registrada, no calidad de medicion.
  {
    "$group": {
      "_id": "$id_sensor",
      "cantidad": {
        "$sum": 1
      }
    }
  },
  // ETAPA 3 — $sort
  // Ordenar la salida: 1 es ascendente y -1 descendente.
  // Criterios en prioridad: cantidad, _id. Los siguientes resuelven empates.
  // _id ofrece un desempate estable para documentos con la misma fecha o valor.
  {
    "$sort": {
      "cantidad": -1,
      "_id": 1
    }
  }
]
