"""Ejecutor local: envia los trabajos reales a Hadoop/YARN mediante Docker."""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from .mapreduce import COLUMNAS, NOMBRES, filtros_validos
except ImportError:
    from mapreduce import COLUMNAS, NOMBRES, filtros_validos


CONTENEDOR = "smartcity_namenode"
JAR = "/opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.4.1.jar"
SCRIPT = "/proyecto/hadoop/mapreduce.py"


def docker(*args):
    try:
        r = subprocess.run(["docker", "exec", CONTENEDOR] + list(args),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Hadoop excedio 30 minutos. Revisar YARN antes de repetir el trabajo.") from exc
    if r.returncode:
        raise RuntimeError("Fallo Hadoop (codigo {}):\n{}".format(r.returncode, (r.stderr or r.stdout)[-6000:]))
    return r


def preparar_filtros(filtros):
    f = {k: (v.isoformat() if isinstance(v, datetime) else v)
         for k, v in (filtros or {}).items() if v is not None}
    return filtros_validos(f)


def ejecutar(consulta, filtros=None, entrada=None, base_salida="/smartcity/resultados"):
    if consulta not in NOMBRES:
        raise ValueError("Consulta Hadoop desconocida")
    f = preparar_filtros({} if consulta == 3 else filtros)
    if consulta == 5 and not f.get("desde"):
        raise ValueError("La consulta temporal requiere desde y hasta")
    if not base_salida.startswith("/smartcity/resultados/") and base_salida != "/smartcity/resultados":
        raise ValueError("La salida debe estar dentro de /smartcity/resultados")
    entrada = entrada or "/smartcity/raw/mongo/{}.json".format("eventos" if consulta == 4 else "lecturas")
    raiz = base_salida.rstrip("/") + "/consulta_{}_{}".format(
        consulta, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:10])
    docker("hdfs", "dfs", "-test", "-e", entrada)
    docker("hdfs", "dfs", "-mkdir", "-p", raiz)
    token = base64.urlsafe_b64encode(json.dumps(f, ensure_ascii=True).encode("utf-8")).decode("ascii")
    logs, t = [], time.perf_counter()

    def trabajo(origen, destino, mapper, reducer):
        r = docker("hadoop", "jar", JAR, "-D", "mapreduce.job.name=smartcity_consulta_{}".format(consulta),
                   "-files", SCRIPT, "-mapper", mapper, "-reducer", reducer,
                   "-numReduceTasks", "1", "-input", origen, "-output", destino)
        logs.append(r.stderr + r.stdout)

    salida = raiz + "/conteos" if consulta == 2 else raiz + "/resultado"
    trabajo(entrada, salida, "python3 mapreduce.py map {} --filtros {}".format(consulta, token),
            "python3 mapreduce.py reduce {}".format(consulta))
    if consulta == 2:
        trabajo(salida + "/part-*", raiz + "/resultado", "python3 mapreduce.py max-map 2",
                "python3 mapreduce.py max-reduce 2")
        salida = raiz + "/resultado"
    texto = docker("hdfs", "dfs", "-cat", salida + "/part-*").stdout
    filas = [json.loads(l) for l in texto.splitlines() if l.strip()]
    log = "\n".join(logs)
    return {"consulta": consulta, "nombre": NOMBRES[consulta], "filtros": f,
            "entrada": entrada, "ruta_hdfs": salida, "columnas": COLUMNAS[consulta], "filas": filas,
            "aplicaciones_yarn": sorted(set(re.findall(r"application_\d+_\d+", log))),
            "segundos": round(time.perf_counter() - t, 3),
            "avisos": [l for l in log.splitlines() if "documentos_malformados=" in l]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("consulta", type=int, choices=sorted(NOMBRES))
    p.add_argument("--desde")
    p.add_argument("--hasta")
    p.add_argument("--sensor")
    p.add_argument("--variable", default="temperatura")
    p.add_argument("--distrito", action="append", default=[])
    p.add_argument("--tipo", action="append", default=[])
    p.add_argument("--entrada", help="Ruta HDFS alternativa, para comprobar con muestras")
    p.add_argument("--evidencia", type=Path, help="Guardar el resultado JSON tambien en este archivo local")
    a = p.parse_args()
    f = {"desde": a.desde, "hasta": a.hasta, "id_sensor": a.sensor,
         "variable": a.variable, "distritos": a.distrito, "tipos": a.tipo}
    try:
        resultado = ejecutar(a.consulta, f, a.entrada)
    except (ValueError, RuntimeError, OSError) as exc:
        p.exit(1, str(exc) + "\n")
    texto = json.dumps(resultado, ensure_ascii=False, indent=2)
    if a.evidencia:
        a.evidencia.parent.mkdir(parents=True, exist_ok=True)
        a.evidencia.write_text(texto + "\n", encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
