[
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      },
      "ubicacion.distrito": "Centro",
      "tipo": "trafico",
      "medicion.carga": {
        "$exists": true
      }
    }
  },
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
  {
    "$unwind": "$par"
  },
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
      "par.k": "carga"
    }
  },
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
  {
    "$match": {
      "par.v": {
        "$gt": 80
      }
    }
  },
  {
    "$project": {
      "id_sensor": 1,
      "tipo": 1,
      "distrito": "$ubicacion.distrito",
      "timestamp": 1,
      "variable": "$par.k",
      "unidad": 1,
      "valor": "$par.v"
    }
  },
  {
    "$sort": {
      "valor": -1,
      "timestamp": 1,
      "_id": 1
    }
  },
  {
    "$limit": 100
  }
]
