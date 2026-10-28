[
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
  {
    "$sort": {
      "fecha_reporte": 1,
      "_id": 1
    }
  },
  {
    "$limit": 100
  },
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
