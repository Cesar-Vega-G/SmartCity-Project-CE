[
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      },
      "severidad": "critica"
    }
  },
  {
    "$sort": {
      "timestamp": -1,
      "_id": 1
    }
  },
  {
    "$limit": 100
  },
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
