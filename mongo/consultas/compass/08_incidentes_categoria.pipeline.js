// Obligatoria 8: incidentes registrados por categoria.
// Coleccion: smartcity.incidentes. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Cantidad por categoria y estado; permite distinguir pendientes de resueltos.
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
  // Incidentes usa fecha_reporte en lugar de timestamp.
  {
    "$match": {
      "fecha_reporte": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      }
    }
  },
  // ETAPA 2 — $group
  // Agrupar por categoria, estado; $sum:1 cuenta documentos de cada grupo.
  // Cada combinacion produce una fila, sin mezclar niveles o estados distintos.
  {
    "$group": {
      "_id": {
        "categoria": "$categoria",
        "estado": "$estado"
      },
      "cantidad": {
        "$sum": 1
      }
    }
  },
  // ETAPA 3 — $sort
  // Ordenar la salida: 1 es ascendente y -1 descendente.
  // Criterios en prioridad: cantidad, _id.categoria, _id.estado. Los siguientes resuelven empates.
  {
    "$sort": {
      "cantidad": -1,
      "_id.categoria": 1,
      "_id.estado": 1
    }
  }
]
