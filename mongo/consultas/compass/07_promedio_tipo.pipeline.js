// Obligatoria 7: promedio por tipo de sensor.
// Coleccion: smartcity.lecturas. Compass > Aggregations > TEXT: pegar TODO y pulsar Run.
// Resultado: Una fila por tipo, variable y unidad; no mezcla variables del mismo sensor.
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
      "par.k": {
        "$in": [
          "no2",
          "pm10",
          "pm25",
          "co",
          "o3",
          "temperatura",
          "humedad",
          "precipitacion",
          "ruido_db",
          "intensidad",
          "ocupacion",
          "carga",
          "velocidad",
          "ocupacion_parking",
          "consumo_kwh"
        ]
      }
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
  // Agrupar por tipo, variable, unidad. _id identifica cada grupo de salida.
  // Separar variable y unidad evita promediar magnitudes incompatibles.
  // $sum:1 cuenta valores validos; $avg, $min y $max calculan sus estadisticas.
  // Cada valor pesa igual; cantidad permite interpretar la cobertura del promedio.
  // No hay limite previo de 100: se procesan TODOS los valores filtrados.
  {
    "$group": {
      "_id": {
        "tipo": "$tipo",
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
  // Criterios en prioridad: _id.tipo, _id.variable. Los siguientes resuelven empates.
  {
    "$sort": {
      "_id.tipo": 1,
      "_id.variable": 1
    }
  }
]
