"""Compara las cinco consultas reales en YARN con MongoDB, sin modificar sus datos."""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "data/generators"))
from comun import conectar_mongo
from ejecutar_mapreduce import ejecutar


def comparar(actual, esperado):
    actual, esperado = sorted(actual), sorted(esperado)
    assert len(actual) == len(esperado), (len(actual), len(esperado))
    for fila, referencia in zip(actual, esperado):
        assert len(fila) == len(referencia)
        for a, b in zip(fila, referencia):
            if isinstance(b, (float, int)):
                assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-7), (a, b)
            else:
                assert a == b, (a, b)


def referencias(db):
    conteos = [[r["_id"], r["n"]] for r in db.lecturas.aggregate([
        {"$group": {"_id": "$id_sensor", "n": {"$sum": 1}}}])]
    mayor = max((r[1] for r in conteos), default=0)
    temperatura = {"medicion.temperatura": {"$type": "number"},
                   "invalidos": {"$nin": ["temperatura"]},
                   "$or": [{"valido": {"$ne": False}}, {"invalidos.0": {"$exists": True}}]}
    stats = {"n": {"$sum": 1}, "promedio": {"$avg": "$medicion.temperatura"},
             "minimo": {"$min": "$medicion.temperatura"}, "maximo": {"$max": "$medicion.temperatura"}}
    t = list(db.lecturas.aggregate([{"$match": temperatura}, {"$group": dict(stats, _id=None)}]))
    hist = [["temperatura", "C", r["n"], r["promedio"], r["minimo"], r["maximo"]] for r in t]
    eventos = [[r["_id"], r["n"]] for r in db.eventos.aggregate([
        {"$group": {"_id": "$ubicacion.distrito", "n": {"$sum": 1}}}])]
    f = dict(temperatura, timestamp={"$gte": datetime(2026, 7, 1), "$lt": datetime(2026, 8, 1)})
    grupo = {"dia": {"$dateToString": {"date": "$timestamp", "format": "%Y-%m-%d", "timezone": "UTC"}},
             "sensor": "$id_sensor"}
    diarios = [[r["_id"]["dia"], r["_id"]["sensor"], "temperatura", "C",
                r["n"], r["promedio"], r["minimo"], r["maximo"]]
               for r in db.lecturas.aggregate([{"$match": f}, {"$group": dict(stats, _id=grupo)}])]
    return {1: conteos, 2: [r for r in conteos if r[1] == mayor], 3: hist, 4: eventos, 5: diarios}


def main():
    db = conectar_mongo()
    print("Calculando referencias de MongoDB sobre la carga existente...", flush=True)
    referencia = referencias(db)
    informe = {"fecha_utc": datetime.now(timezone.utc).isoformat(),
               "datos": {"lecturas": sum(r[1] for r in referencia[1]),
                         "eventos": sum(r[1] for r in referencia[4])}, "consultas": []}
    destino = RAIZ / "hadoop/evidencia/historico.json"
    destino.parent.mkdir(exist_ok=True)
    for n in range(1, 6):
        print("Ejecutando consulta", n, "en YARN...", flush=True)
        filtros = {"desde": "2026-07-01", "hasta": "2026-08-01", "variable": "temperatura"} if n == 5 else {}
        resultado = ejecutar(n, filtros)
        comparar(resultado["filas"], referencia[n])
        evidencia = {k: v for k, v in resultado.items() if k != "filas"}
        evidencia.update(ok=True, numero_filas=len(resultado["filas"]), muestra=resultado["filas"][:3])
        informe["consultas"].append(evidencia)
        informe["aprobado"] = len(informe["consultas"]) == 5
        destino.write_text(json.dumps(informe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Consulta", n, "OK:", len(resultado["filas"]), "filas;", resultado["segundos"], "s", flush=True)
    print("Cinco consultas verificadas. Evidencia:", destino, flush=True)


if __name__ == "__main__":
    main()
