[
  {
    "$match": {
      "fecha_reporte": {
        "$gte": ISODate("2026-07-01T00:00:00Z"),
        "$lt": ISODate("2026-08-01T00:00:00Z")
      }
    }
  },
  {
    "$group": {
      "_id": {
        "categoria": "$categoria",
        "estado": "$estado"
      },
      "cantidad": {
        "$sum": 1
      }
    }
  },
  {
    "$sort": {
      "cantidad": -1,
      "_id.categoria": 1,
      "_id.estado": 1
    }
  }
]
