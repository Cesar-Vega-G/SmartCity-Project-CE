// Pregunta complementaria: sensores que superaron limites.
// Coleccion: smartcity.alertas. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Alertas por sensor y variable cuyo valor supera su limite; no cuenta eventos deduplicados.
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
  // $type exige numeros en valor y limite; $expr permite comparar dos campos del documento.
  // $gt es estricto: valor igual a limite no entra. Son limites del proyecto, no normativa.
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      },
      "valor": {
        "$type": "number"
      },
      "limite": {
        "$type": "number"
      },
      "$expr": {
        "$gt": [
          "$valor",
          "$limite"
        ]
      }
    }
  },
  // ETAPA 2 — $group
  // Separar sensor y variable para no mezclar alertas de magnitudes diferentes.
  // $sum cuenta alertas, $max obtiene el mayor valor y $min/$max delimitan las fechas.
  {
    "$group": {
      "_id": {
        "sensor": "$id_sensor",
        "variable": "$variable"
      },
      "cantidad": {
        "$sum": 1
      },
      "maximo": {
        "$max": "$valor"
      },
      "primera": {
        "$min": "$timestamp"
      },
      "ultima": {
        "$max": "$timestamp"
      }
    }
  },
  // ETAPA 3 — $sort
  // Ordenar la salida: 1 es ascendente y -1 descendente.
  // Criterios en prioridad: cantidad, _id.sensor, _id.variable. Los siguientes resuelven empates.
  {
    "$sort": {
      "cantidad": -1,
      "_id.sensor": 1,
      "_id.variable": 1
    }
  }
]
