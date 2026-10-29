// Pregunta complementaria: zonas con mayor contaminacion.
// Coleccion: smartcity.lecturas. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Ranking del promedio de NO2 por distrito; no es un indice integral de calidad del aire.
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
  // $exists solo comprueba presencia: mas adelante se valida que el valor sea numerico.
  // Si cambias de variable, revisa tanto medicion.<variable> aqui como par.k mas adelante.
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      },
      "tipo": "calidad_aire",
      "medicion.no2": {
        "$exists": true
      }
    }
  },
  // ETAPA 2 — $set
  // Crear una lista auxiliar segura: si invalidos no es un arreglo, usar [].
  // Esto permite usar $size y $in sin errores de tipo en las etapas siguientes.
  {
    "$set": {
      "_invalidos": {
        "$cond": [
          {
            "$isArray": "$invalidos"
          },
          "$invalidos",
          []
        ]
      }
    }
  },
  // ETAPA 3 — $match
  // Excluir documentos con valido:false sin detalle de variables invalidas.
  // $or permite continuar si no esta marcado falso o si hay detalle para evaluar por variable.
  // Aun no acepta todas las mediciones: el filtro posterior revisa cada variable.
  {
    "$match": {
      "$expr": {
        "$or": [
          {
            "$ne": [
              "$valido",
              false
            ]
          },
          {
            "$gt": [
              {
                "$size": "$_invalidos"
              },
              0
            ]
          }
        ]
      }
    }
  },
  // ETAPA 4 — $project
  // Conservar los campos necesarios y transformar medicion con $objectToArray.
  // Ejemplo: {temperatura:20, humedad:60} pasa a pares {k:"temperatura", v:20}, etc.
  // Si medicion no es un objeto, usar {}: no inventar mediciones ni fallar por su tipo.
  {
    "$project": {
      "id_sensor": 1,
      "tipo": 1,
      "ubicacion": 1,
      "timestamp": 1,
      "_invalidos": 1,
      "par": {
        "$objectToArray": {
          "$cond": [
            {
              "$eq": [
                {
                  "$type": "$medicion"
                },
                "object"
              ]
            },
            "$medicion",
            {}
          ]
        }
      }
    }
  },
  // ETAPA 5 — $unwind
  // Crear una fila de trabajo por par variable/valor.
  // Una lectura con tres variables produce tres filas; por eso el conteo estadistico es de valores.
  // Un arreglo vacio no aporta filas. Los documentos originales siguen intactos.
  {
    "$unwind": "$par"
  },
  // ETAPA 6 — $match
  // Validar cada valor DESPUES de separar las variables.
  // par.k es el nombre y par.v es el valor. $isNumber descarta nulos y texto.
  // $not + $in excluyen variables marcadas en invalidos; una variable sana puede pasar.
  // El filtro par.k selecciona la variable solicitada o el catalogo conocido.
  // No reemplazar valores ausentes o invalidos por cero: alteraria los resultados.
  {
    "$match": {
      "$expr": {
        "$and": [
          {
            "$isNumber": "$par.v"
          },
          {
            "$not": [
              {
                "$in": [
                  "$par.k",
                  "$_invalidos"
                ]
              }
            ]
          }
        ]
      },
      "par.k": "no2"
    }
  },
  // ETAPA 7 — $set
  // Asignar la unidad del contrato a cada variable mediante $switch.
  // Por ejemplo NO2 usa ug/m3 y CO mg/m3: no se deben mezclar en un promedio.
  // El catalogo completo permite interpretar diferentes estructuras de medicion.
  {
    "$set": {
      "unidad": {
        "$switch": {
          "branches": [
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "no2"
                ]
              },
              "then": "ug/m3"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "pm10"
                ]
              },
              "then": "ug/m3"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "pm25"
                ]
              },
              "then": "ug/m3"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "co"
                ]
              },
              "then": "mg/m3"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "o3"
                ]
              },
              "then": "ug/m3"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "temperatura"
                ]
              },
              "then": "C"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "humedad"
                ]
              },
              "then": "%"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "precipitacion"
                ]
              },
              "then": "mm"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "ruido_db"
                ]
              },
              "then": "dB"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "intensidad"
                ]
              },
              "then": "veh/h"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "ocupacion"
                ]
              },
              "then": "%"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "carga"
                ]
              },
              "then": "0-100"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "velocidad"
                ]
              },
              "then": "km/h"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "ocupacion_parking"
                ]
              },
              "then": "%"
            },
            {
              "case": {
                "$eq": [
                  "$par.k",
                  "consumo_kwh"
                ]
              },
              "then": "kWh"
            }
          ],
          "default": "desconocida"
        }
      }
    }
  },
  // ETAPA 8 — $group
  // Agrupar por distrito, variable, unidad. _id identifica cada grupo de salida.
  // Separar variable y unidad evita promediar magnitudes incompatibles.
  // $sum:1 cuenta valores validos; $avg, $min y $max calculan sus estadisticas.
  // Cada valor pesa igual; cantidad permite interpretar la cobertura del promedio.
  // No hay limite previo de 100: se procesan TODOS los valores filtrados.
  {
    "$group": {
      "_id": {
        "distrito": "$ubicacion.distrito",
        "variable": "$par.k",
        "unidad": "$unidad"
      },
      "cantidad": {
        "$sum": 1
      },
      "promedio": {
        "$avg": "$par.v"
      },
      "minimo": {
        "$min": "$par.v"
      },
      "maximo": {
        "$max": "$par.v"
      }
    }
  },
  // ETAPA 9 — $sort
  // Ordenar la salida: 1 es ascendente y -1 descendente.
  // Criterios en prioridad: promedio, _id.distrito. Los siguientes resuelven empates.
  // El mayor promedio de NO2 aparece primero; no se suman contaminantes diferentes.
  {
    "$sort": {
      "promedio": -1,
      "_id.distrito": 1
    }
  }
]
