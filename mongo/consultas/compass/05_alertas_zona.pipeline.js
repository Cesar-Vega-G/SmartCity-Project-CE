// Obligatoria 5: alertas emitidas por zona geografica.
// Coleccion: smartcity.alertas. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Cantidad de alertas por distrito y nivel, de mayor a menor.
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
  // Agrupar por distrito, nivel; $sum:1 cuenta documentos de cada grupo.
  // Cada combinacion produce una fila, sin mezclar niveles o estados distintos.
  {
    "$group": {
      "_id": {
        "distrito": "$ubicacion.distrito",
        "nivel": "$nivel"
      },
      "cantidad": {
        "$sum": 1
      }
    }
  },
  // ETAPA 3 — $sort
  // Ordenar la salida: 1 es ascendente y -1 descendente.
  // Criterios en prioridad: cantidad, _id.distrito, _id.nivel. Los siguientes resuelven empates.
  {
    "$sort": {
      "cantidad": -1,
      "_id.distrito": 1,
      "_id.nivel": 1
    }
  }
]
