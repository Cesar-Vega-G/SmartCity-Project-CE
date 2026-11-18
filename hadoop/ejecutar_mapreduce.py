"""PROPOSITO: enviar las consultas de Sebastian a Hadoop/YARN desde Windows o Streamlit.
Recibe: un ID 1..5, filtros y rutas HDFS; la CLI tambien admite un archivo de evidencia.
Devuelve: un diccionario con filas, columnas, filtros, ruta HDFS, aplicaciones y duracion.
EFECTOS: crea salidas nuevas en HDFS y ejecuta trabajos reales; lee los historicos existentes.
JUSTIFICACION: compartir un ejecutor mantiene iguales la terminal y el dashboard."""
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

# IMPORTACION: admitir tanto importacion como modulo del dashboard como ejecucion directa de la CLI.
try:
    from .mapreduce import COLUMNAS, NOMBRES, filtros_validos
except ImportError:
    from mapreduce import COLUMNAS, NOMBRES, filtros_validos


# CLIENTE: se lanza el JAR desde el NameNode; las tareas se ejecutan mediante el NodeManager/YARN.
CONTENEDOR = "smartcity_namenode"
JAR = "/opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.4.1.jar"
SCRIPT = "/proyecto/hadoop/mapreduce.py"


def docker(*args):
    """Ejecutar un comando dentro del contenedor usado como cliente Hadoop.
    Recibe: argumentos separados del comando, sin construir una cadena de shell.
    Devuelve: subprocess.CompletedProcess con stdout/stderr si el comando termina bien.
    Lanza RuntimeError si falla o excede 30 minutos; no confirma que YARN se haya detenido."""
    try:
        r = subprocess.run(["docker", "exec", CONTENEDOR] + list(args),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Hadoop excedio 30 minutos. Revisar YARN antes de repetir el trabajo.") from exc
    # Un proceso fallido no debe devolver una tabla vacia que parezca una consulta correcta.
    if r.returncode:
        raise RuntimeError("Fallo Hadoop (codigo {}):\n{}".format(r.returncode, (r.stderr or r.stdout)[-6000:]))
    return r


def preparar_filtros(filtros):
    """Convertir los parametros del dashboard a valores transportables como JSON.
    Recibe: diccionario opcional con datetime, listas, cadenas y valores None.
    Devuelve: un diccionario nuevo, validado, con fechas ISO y sin entradas None."""
    f = {k: (v.isoformat() if isinstance(v, datetime) else v)
         for k, v in (filtros or {}).items() if v is not None}
    return filtros_validos(f)


def ejecutar(consulta, filtros=None, entrada=None, base_salida="/smartcity/resultados"):
    """Lanzar una de las cinco preguntas y recoger su respuesta de HDFS.
    Recibe: consulta, filtros opcionales, entrada HDFS alternativa y base de salida.
    Devuelve: diccionario con resultado tabular, parametros y evidencia de ejecucion.
    La 3 usa todo el historico; la 5 exige periodo; la 2 encadena dos trabajos.
    Cada llamada usa una carpeta unica para conservar las ejecuciones anteriores."""
    # ETAPA 1: validar antes de crear carpetas o lanzar trabajos.
    if consulta not in NOMBRES:
        raise ValueError("Consulta Hadoop desconocida")
    f = preparar_filtros({} if consulta == 3 else filtros)
    if consulta == 5 and not f.get("desde"):
        raise ValueError("La consulta temporal requiere desde y hasta")
    if not base_salida.startswith("/smartcity/resultados/") and base_salida != "/smartcity/resultados":
        raise ValueError("La salida debe estar dentro de /smartcity/resultados")
    # ETAPA 2: elegir lecturas o eventos; --entrada permite usar una muestra conocida.
    entrada = entrada or "/smartcity/raw/mongo/{}.json".format("eventos" if consulta == 4 else "lecturas")
    # Fecha UTC e identificador aleatorio evitan colisiones y sobrescritura de salidas.
    raiz = base_salida.rstrip("/") + "/consulta_{}_{}".format(
        consulta, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:10])
    # ETAPA 3: confirmar que la entrada existe y crear solo la carpeta contenedora de esta ejecucion.
    docker("hdfs", "dfs", "-test", "-e", entrada)
    docker("hdfs", "dfs", "-mkdir", "-p", raiz)
    # Base64 transporta JSON sin problemas de comillas; no cifra los filtros.
    token = base64.urlsafe_b64encode(json.dumps(f, ensure_ascii=True).encode("utf-8")).decode("ascii")
    logs, t = [], time.perf_counter()

    def trabajo(origen, destino, mapper, reducer):
        """Enviar una fase MapReduce a YARN utilizando Hadoop Streaming.
        Recibe: origen/destino HDFS y comandos del mapper y reducer.
        Devuelve: None; escribe los resultados en destino y agrega los logs a la lista externa.
        -files distribuye el script; el Python del NodeManager ejecuta las tareas."""
        # Un reducer por trabajo en esta configuracion; Hadoop puede repartir la lectura en tareas Map.
        r = docker("hadoop", "jar", JAR, "-D", "mapreduce.job.name=smartcity_consulta_{}".format(consulta),
                   "-files", SCRIPT, "-mapper", mapper, "-reducer", reducer,
                   "-numReduceTasks", "1", "-input", origen, "-output", destino)
        logs.append(r.stderr + r.stdout)

    # ETAPA 4: ejecutar el conteo o las estadisticas de la consulta elegida.
    salida = raiz + "/conteos" if consulta == 2 else raiz + "/resultado"
    trabajo(entrada, salida, "python3 mapreduce.py map {} --filtros {}".format(consulta, token),
            "python3 mapreduce.py reduce {}".format(consulta))
    # ETAPA 5, solo consulta 2: comparar los conteos bajo una clave comun y conservar empates.
    if consulta == 2:
        trabajo(salida + "/part-*", raiz + "/resultado", "python3 mapreduce.py max-map 2",
                "python3 mapreduce.py max-reduce 2")
        salida = raiz + "/resultado"
    # ETAPA 6: leer todas las partes finales y reconstruir las filas JSON para el consumidor.
    texto = docker("hdfs", "dfs", "-cat", salida + "/part-*").stdout
    filas = [json.loads(l) for l in texto.splitlines() if l.strip()]
    log = "\n".join(logs)
    # DEVOLUCION: los IDs YARN y la ruta permiten comprobar que el resultado provino de Hadoop.
    return {"consulta": consulta, "nombre": NOMBRES[consulta], "filtros": f,
            "entrada": entrada, "ruta_hdfs": salida, "columnas": COLUMNAS[consulta], "filas": filas,
            "aplicaciones_yarn": sorted(set(re.findall(r"application_\d+_\d+", log))),
            "segundos": round(time.perf_counter() - t, 3),
            "avisos": [l for l in log.splitlines() if "documentos_malformados=" in l]}


def main():
    """Ofrecer las mismas consultas desde la terminal.
    Recibe: ID, fechas, sensor, variable, distritos, tipos y rutas desde argparse.
    Devuelve: None; imprime el resultado JSON y opcionalmente lo guarda en --evidencia.
    Si falla la consulta, termina con codigo 1 y un mensaje de error."""
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
    # Guardar evidencia es opcional; la respuesta se imprime igualmente por la terminal.
    if a.evidencia:
        a.evidencia.parent.mkdir(parents=True, exist_ok=True)
        a.evidencia.write_text(texto + "\n", encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
