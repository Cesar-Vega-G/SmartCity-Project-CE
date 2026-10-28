[
  {
    "$match": {
      "timestamp": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      }
    }
  },
  {
    "$group": {
      "_id": {
        "distrito": "$ubicacion.distrito",
        "nivel": "$nivel"
      },
      "cantidad": {
        "$sum": 1
      }
    }
  },
  {
    "$sort": {
      "cantidad": -1,
      "_id.distrito": 1,
      "_id.nivel": 1
    }
  }
]
