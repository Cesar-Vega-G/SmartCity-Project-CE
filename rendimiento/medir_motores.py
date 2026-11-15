import json
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data" / "generators"))
from comun import RAIZ, conectar_mongo, conectar_pg

REP = 3
STREAMING = "/opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-*.jar"

# mismas 3 consultas en los 4 motores
CONSULTAS = {
    "c1": "Lecturas de S-00002 en marzo 2025 (busqueda puntual)",
    "c2": "NO2 promedio por distrito, enero 2025 (agregacion)",
    "c3": "Lecturas por tipo de sensor y anio (recorre todo)",
}

PG = {
    "c1": """SELECT * FROM medicion WHERE id_sensor = 'S-00002'
             AND fecha_hora >= '2025-03-01' AND fecha_hora < '2025-04-01'""",
    "c2": """SELECT distrito, AVG(valor) FROM v_medicion_detalle WHERE variable = 'no2'
             AND fecha_hora >= '2025-01-01' AND fecha_hora < '2025-02-01' GROUP BY distrito""",
    "c3": """SELECT tipo_sensor, EXTRACT(YEAR FROM fecha_hora), COUNT(*) FROM v_medicion_detalle GROUP BY 1, 2""",
}


# mediana de 3 corridas como en el sprint 1
def medir(f):
    tiempos, res = [], None
    for _ in range(REP):
        t = time.perf_counter()
        res = f()
        tiempos.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(tiempos), 1), res


def resumir(c, filas):
    if c == "c1":
        return f"{len(filas)} filas"
    if c == "c2":
        vals = [float(v) for _, v in filas]
        return f"{len(vals)} distritos, prom. {sum(vals) / len(vals):.2f}"
    return f"{len(filas)} grupos, {sum(int(n) for n in [f[-1] for f in filas])} total"


def postgres():
    con = conectar_pg()
    out = {}
    for c, sql in PG.items():
        def q():
            with con.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
        ms, filas = medir(q)
        out[c] = (ms, resumir(c, filas))
    con.close()
    return out


def mongo():
    db = conectar_mongo()
    ene = {"$gte": datetime(2025, 1, 1), "$lt": datetime(2025, 2, 1)}
    mar = {"$gte": datetime(2025, 3, 1), "$lt": datetime(2025, 4, 1)}
    consultas = {
        "c1": lambda: list(db.lecturas.find({"id_sensor": "S-00002", "timestamp": mar})),
        "c2": lambda: [(d["_id"], d["no2"]) for d in db.lecturas.aggregate([
            {"$match": {"tipo": "calidad_aire", "timestamp": ene, "medicion.no2": {"$ne": None}, "invalidos": {"$ne": "no2"}}},
            {"$group": {"_id": "$ubicacion.distrito", "no2": {"$avg": "$medicion.no2"}}}])],
        "c3": lambda: [(d["_id"], d["n"]) for d in db.lecturas.aggregate([
            {"$group": {"_id": {"tipo": "$tipo", "anio": {"$year": "$timestamp"}}, "n": {"$sum": 1}}}])],
    }
    out = {}
    for c, f in consultas.items():
        ms, filas = medir(f)
        out[c] = (ms, resumir(c, filas))
    return out


# spark mide adentro, aqui solo se lee el resultado
def spark():
    t = time.perf_counter()
    r = subprocess.run(["docker", "exec", "smartcity_spark_master", "/opt/spark/bin/spark-submit",
                        "/proyecto/spark/medir_spark.py"], capture_output=True, text=True)
    total = round((time.perf_counter() - t) * 1000)
    linea = [l for l in r.stdout.splitlines() if l.startswith("RESULTADO ")]
    if not linea:
        print(r.stderr[-2000:])
        raise SystemExit("spark fallo")
    datos = json.loads(linea[0][len("RESULTADO "):])
    out = {}
    for c, d in datos.items():
        res = d["resultado"]
        if c == "c1":
            txt = f"{res} filas"
        elif c == "c2":
            txt = f"{res[0]} distritos, prom. {res[1]:.2f}"
        else:
            txt = f"{res[0]} grupos, {res[1]} total"
        out[c] = (d["ms"], txt)
    return out, total


# cada trabajo incluye arrancar, por eso tarda ~40 s
def mapreduce():
    out = {}
    for c in CONSULTAS:
        salida = f"/smartcity/resultados/rend_{c}"
        cmd = (f"hdfs dfs -rm -r -f -skipTrash {salida} > /dev/null && "
               f"hadoop jar {STREAMING} -files /proyecto/hadoop/rendimiento_mr.py "
               f"-mapper 'python3 rendimiento_mr.py map {c}' -reducer 'python3 rendimiento_mr.py reduce {c}' "
               f"-input /smartcity/raw/mongo/lecturas.json -output {salida}")

        def job():
            r = subprocess.run(["docker", "exec", "smartcity_namenode", "bash", "-c", cmd],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stderr[-2000:])
                raise SystemExit(f"mapreduce {c} fallo")
            cat = subprocess.run(["docker", "exec", "smartcity_namenode", "bash", "-c",
                                  f"hdfs dfs -cat {salida}/part-*"], capture_output=True, text=True)
            return [l.split("\t") for l in cat.stdout.splitlines() if l]

        print(f"  mapreduce {c}...")
        ms, filas = medir(job)
        if c == "c1":
            txt = f"{filas[0][1] if filas else 0} filas"
        else:
            txt = resumir(c, filas)
        out[c] = (ms, txt)
    return out


def main():
    print("postgres...")
    pg = postgres()
    print("mongo...")
    mg = mongo()
    print("spark...")
    sp, sp_total = spark()
    print("mapreduce (tarda varios minutos)...")
    mr = mapreduce()

    lineas = [
        "# Rendimiento de los 4 motores",
        "",
        f"Medido el {datetime.now():%d/%m/%Y %H:%M} con `rendimiento/medir_motores.py`. Mediana de {REP} ejecuciones, en ms.",
        "",
        "| Consulta | PostgreSQL | MongoDB | Spark | MapReduce |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c, nombre in CONSULTAS.items():
        lineas.append(f"| {nombre} | {pg[c][0]} | {mg[c][0]} | {sp[c][0]} | {mr[c][0]} |")
    lineas += ["", "Resultados (para comprobar que responden lo mismo):", "",
               "| Consulta | PostgreSQL | MongoDB | Spark | MapReduce |", "| --- | --- | --- | --- | --- |"]
    for c in CONSULTAS:
        lineas.append(f"| {c} | {pg[c][1]} | {mg[c][1]} | {sp[c][1]} | {mr[c][1]} |")
    lineas += ["", f"Spark completo (arrancar + 9 consultas + cerrar): {sp_total} ms. "
               "El tiempo de Spark de la tabla es solo la consulta; el de MapReduce incluye arrancar cada trabajo."]

    texto = "\n".join(lineas) + "\n"
    (RAIZ / "docs" / "rendimiento_motores.md").write_text(texto, encoding="utf-8")
    print()
    print(texto)


if __name__ == "__main__":
    main()
