[
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      },
      "id_sensor": "S-00001"
    }
  },
  {
    "$sort": {
      "timestamp": 1,
      "_id": 1
    }
  },
  {
    "$limit": 100
  },
  {
    "$project": {
      "_id": 1,
      "id_sensor": 1,
      "tipo": 1,
      "ubicacion": 1,
      "medicion": 1,
      "timestamp": 1,
      "valido": 1,
      "invalidos": 1
    }
  }
]
