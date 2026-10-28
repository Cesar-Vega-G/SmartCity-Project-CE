// Ejemplo adicional: informacion dinamica no estructurada.
// Coleccion: smartcity.incidentes. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Accidentes con heridos: datos_extra cambia segun la categoria de incidente.
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
  // $in selecciona las categorias permitidas y $and combina condiciones del campo anidado.
  // Exigir existencia, tipo numerico y heridos > 0 evita tratar faltantes como accidentes con heridos.
  {
    "$match": {
      "fecha_reporte": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      },
      "categoria": {
        "$in": [
          "accidente_transito"
        ]
      },
      "$and": [
        {
          "datos_extra.heridos": {
            "$exists": true
          }
        },
        {
          "datos_extra.heridos": {
            "$type": "number",
            "$gt": 0
          }
        }
      ]
    }
  },
  // ETAPA 2 — $sort
  // Ordenar la salida: 1 es ascendente y -1 descendente.
  // Criterios en prioridad: fecha_reporte, _id. Los siguientes resuelven empates.
  // _id ofrece un desempate estable para documentos con la misma fecha o valor.
  {
    "$sort": {
      "fecha_reporte": 1,
      "_id": 1
    }
  },
  // ETAPA 3 — $limit
  // Mostrar como maximo 100 documentos de detalle para una demostracion manejable.
  // Va despues del ordenamiento para seleccionar los primeros del orden solicitado.
  // Este numero no representa el total de coincidencias en la coleccion.
  {
    "$limit": 100
  },
  // ETAPA 4 — $project
  // Preparar la salida: 1 conserva campos; una ruta con $ permite renombrarlos.
  // _id se conserva por defecto salvo exclusion explicita.
  // datos_extra deja visible el campo dinamico heridos y otros detalles del incidente.
  {
    "$project": {
      "categoria": 1,
      "estado": 1,
      "ubicacion": 1,
      "fecha_reporte": 1,
      "datos_extra": 1
    }
  }
]
