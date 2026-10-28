[
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
  {
    "$sort": {
      "cantidad": -1,
      "_id.sensor": 1,
      "_id.variable": 1
    }
  }
]
