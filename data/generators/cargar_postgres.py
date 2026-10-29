from comun import conectar_pg, conectar_mongo


def pipeline_horario(tipo):
    return [
        {"$match": {"tipo": tipo}},
        {"$project": {
            "id_sensor": 1,
            "hora": {"$dateTrunc": {"date": "$timestamp", "unit": "hour"}},
            "kv": {"$objectToArray": "$medicion"},
            "inv": {"$ifNull": ["$invalidos", []]},
        }},
        {"$unwind": "$kv"},
        {"$match": {"$expr": {"$and": [
            {"$not": [{"$in": ["$kv.k", "$inv"]}]},
            {"$isNumber": "$kv.v"},
        ]}}},
        {"$group": {
            "_id": {"s": "$id_sensor", "h": "$hora", "k": "$kv.k"},
            "v": {"$avg": "$kv.v"},
        }},
    ]


def main():
    db = conectar_mongo()
    con = conectar_pg()
    cur = con.cursor()

    variables = dict(cur.execute("SELECT nombre, id_variable FROM variable").fetchall())
    cur.execute("TRUNCATE medicion")
    con.commit()

    total = 0
    for tipo in sorted(db.lecturas.distinct("tipo")):
        print(f"{tipo}...", end=" ", flush=True)
        n = 0
        with cur.copy("COPY medicion (id_sensor, id_variable, fecha_hora, valor) FROM STDIN") as copia:
            for r in db.lecturas.aggregate(pipeline_horario(tipo), allowDiskUse=True, batchSize=10000):
                g = r["_id"]
                copia.write_row((g["s"], variables[g["k"]], g["h"], round(r["v"], 3)))
                n += 1
        con.commit()
        print(n)
        total += n

    cur.execute("ANALYZE medicion")
    con.commit()
    print("Total filas en medicion:", total)
    for fila in cur.execute("SELECT tableoid::regclass, COUNT(*) FROM medicion GROUP BY 1 ORDER BY 1").fetchall():
        print(" ", fila[0], fila[1])
    con.close()


if __name__ == "__main__":
    main()
