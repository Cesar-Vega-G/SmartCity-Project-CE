// Obligatoria 4: eventos criticos detectados.
// Coleccion: smartcity.eventos. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Eventos con severidad critica y sus detalles, del mas reciente al mas antiguo.
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
  // Eventos usa severidad; nivel pertenece a alertas. No son el mismo campo.
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      },
      "severidad": "critica"
    }
  },
  // ETAPA 2 — $sort
  // Ordenar la salida: 1 es ascendente y -1 descendente.
  // Criterios en prioridad: timestamp, _id. Los siguientes resuelven empates.
  // _id ofrece un desempate estable para documentos con la misma fecha o valor.
  {
    "$sort": {
      "timestamp": -1,
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
  // detalles conserva la informacion especifica de cada clase de evento.
  {
    "$project": {
      "id_sensor": 1,
      "tipo_evento": 1,
      "severidad": 1,
      "ubicacion": 1,
      "timestamp": 1,
      "detalles": 1
    }
  }
]
