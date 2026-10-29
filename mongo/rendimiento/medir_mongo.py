import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "data" / "generators"))
from comun import RAIZ, conectar_mongo

INDICES = [
    ("lecturas", [("id_sensor", 1), ("timestamp", 1)], "idx_sensor_timestamp"),
    ("lecturas", [("tipo", 1), ("timestamp", 1)], "idx_tipo_timestamp"),
    ("lecturas", [("ubicacion.geo", "2dsphere")], "idx_geo"),
    ("alertas", [("nivel", 1), ("ubicacion.distrito", 1)], "idx_nivel_distrito"),
    ("alertas", [("id_sensor", 1), ("timestamp", 1)], "idx_sensor_timestamp"),
    ("eventos", [("tipo_evento", 1), ("timestamp", 1)], "idx_tipo_timestamp"),
    ("incidentes", [("categoria", 1), ("fecha_reporte", 1)], "idx_categoria_fecha"),
]

REPETICIONES = 3
SOL = [-3.7038, 40.4168]


def consultas(sensor_trafico):
    return [
        ("m1", "Lecturas de un sensor en marzo 2025", "lecturas", "find",
         {"filter": {"id_sensor": "S-00002",
                     "timestamp": {"$gte": datetime(2025, 3, 1), "$lt": datetime(2025, 4, 1)}}}),
        ("m2", "Ultimas 24 lecturas de un sensor de trafico", "lecturas", "find",
         {"filter": {"id_sensor": sensor_trafico}, "sort": {"timestamp": -1}, "limit": 24}),
        ("m3", "Promedio de NO2 por distrito en enero 2025", "lecturas", "aggregate",
         {"pipeline": [
             {"$match": {"tipo": "calidad_aire",
                         "timestamp": {"$gte": datetime(2025, 1, 1), "$lt": datetime(2025, 2, 1)}}},
             {"$group": {"_id": "$ubicacion.distrito", "promedio": {"$avg": "$medicion.no2"}}},
             {"$sort": {"promedio": -1}}]}),
        ("m4", "Lecturas a menos de 1 km de Puerta del Sol en julio 2026", "lecturas", "count",
         {"filter": {"ubicacion.geo": {"$geoWithin": {"$centerSphere": [SOL, 1 / 6378.1]}},
                     "timestamp": {"$gte": datetime(2026, 7, 1), "$lt": datetime(2026, 8, 1)}}}),
        ("m5", "Cantidad de alertas criticas por distrito", "alertas", "aggregate",
         {"pipeline": [
             {"$match": {"nivel": "critica"}},
             {"$group": {"_id": "$ubicacion.distrito", "total": {"$sum": 1}}},
             {"$sort": {"total": -1}}]}),
    ]


def ejecutar(db, col, tipo, args):
    c = db[col]
    if tipo == "find":
        cur = c.find(args["filter"])
        if "sort" in args:
            cur = cur.sort(list(args["sort"].items()))
        if "limit" in args:
            cur = cur.limit(args["limit"])
        return len(list(cur))
    if tipo == "count":
        return c.count_documents(args["filter"])
    return len(list(c.aggregate(args["pipeline"], allowDiskUse=True)))


def explicar(db, col, tipo, args):
    if tipo == "aggregate":
        cmd = {"aggregate": col, "pipeline": args["pipeline"], "cursor": {}}
    else:
        cmd = {"find": col, "filter": args["filter"]}
        if "sort" in args:
            cmd["sort"] = args["sort"]
        if "limit" in args:
            cmd["limit"] = args["limit"]
    return db.command("explain", cmd, verbosity="executionStats")


def recorrer(nodo, etapas, docs):
    if isinstance(nodo, dict):
        if "stage" in nodo:
            etapas.add(nodo["stage"])
        if "totalDocsExamined" in nodo:
            docs.append(nodo["totalDocsExamined"])
        for v in nodo.values():
            recorrer(v, etapas, docs)
    elif isinstance(nodo, list):
        for v in nodo:
            recorrer(v, etapas, docs)


def resumen(plan):
    etapas, docs = set(), []
    recorrer(plan, etapas, docs)
    if "IXSCAN" in etapas:
        tipo = "IXSCAN"
    elif "COLLSCAN" in etapas:
        tipo = "COLLSCAN"
    else:
        tipo = ", ".join(sorted(etapas))
    return tipo, (max(docs) if docs else 0)


def correr(db, lista, etapa, carpeta):
    res = {}
    for clave, nombre, col, tipo, args in lista:
        tiempos = []
        n = 0
        for _ in range(REPETICIONES):
            t = time.perf_counter()
            n = ejecutar(db, col, tipo, args)
            tiempos.append((time.perf_counter() - t) * 1000)
        plan = explicar(db, col, tipo, args)
        etapa_plan, docs = resumen(plan)
        (carpeta / f"{clave}_{etapa}.json").write_text(json.dumps(plan, default=str, indent=2), encoding="utf-8")
        res[clave] = (statistics.median(tiempos), etapa_plan, docs, n)
        print(f"  {clave} {etapa}: {res[clave][0]:.1f} ms  [{etapa_plan}, {docs} docs revisados, {n} resultados]")
    return res


def main():
    carpeta = AQUI / "planes"
    carpeta.mkdir(exist_ok=True)
    db = conectar_mongo()

    print("Quitando indices para medir el antes...")
    for col in {c for c, _, _ in INDICES}:
        db[col].drop_indexes()

    sensor_trafico = db.lecturas.find_one({"tipo": "trafico"}, {"id_sensor": 1})["id_sensor"]
    lista = consultas(sensor_trafico)

    print("Sin indices:")
    antes = correr(db, lista, "antes", carpeta)

    print("Creando indices (puede tardar unos minutos)...")
    for col, claves, nombre in INDICES:
        db[col].create_index(claves, name=nombre)
        print("  ", col, nombre)

    print("Con indices:")
    despues = correr(db, lista, "despues", carpeta)

    filas = ["| Consulta | Sin índice (ms) | Con índice (ms) | Mejora | Plan sin índice | Plan con índice | Docs revisados sin → con | Resultados |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for clave, nombre, col, _, _ in lista:
        a, d = antes[clave], despues[clave]
        mejora = f"{a[0] / d[0]:.0f}x" if d[0] > 0 else "-"
        filas.append(f"| {clave}. {nombre} | {a[0]:.1f} | {d[0]:.1f} | {mejora} | {a[1]} | {d[1]} | "
                     f"{a[2]:,} → {d[2]:,} | {d[3]:,} |".replace(",", "."))

    st = db.command("collStats", "lecturas")
    mb = lambda b: f"{b / 1024 / 1024:.0f} MB"
    texto = ["# Rendimiento en MongoDB", "",
             f"Colección `lecturas`: {st['count']:,} documentos".replace(",", ".")
             + f"; datos: {mb(st['size'])}; índices: {mb(st['totalIndexSize'])}.",
             f"Cada tiempo es la mediana de {REPETICIONES} ejecuciones medidas desde Python; "
             "el plan y los documentos revisados salen de `explain(\"executionStats\")`.",
             "Los planes completos están en `mongo/rendimiento/planes/`.", ""] + filas + [
             "", "Índices usados: `mongo/rendimiento/indices.js`."]
    (RAIZ / "docs" / "rendimiento_mongo.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    print("\nResultados guardados en docs/rendimiento_mongo.md")


if __name__ == "__main__":
    main()
