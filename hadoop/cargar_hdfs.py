import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data" / "generators"))
from comun import leer_env

COLECCIONES = ["lecturas", "alertas", "eventos", "incidentes"]
CARPETAS = ["/smartcity/raw/madrid", "/smartcity/raw/mongo", "/smartcity/procesado", "/smartcity/resultados"]
MADRID = ["/datos/raw/aire", "/datos/raw/clima", "/datos/raw/energia", "/datos/raw/trafico"]


def docker(contenedor, *cmd):
    subprocess.run(["docker", "exec", contenedor, *cmd], check=True)


# corre hdfs dfs dentro del namenode
def hdfs(*args):
    print("hdfs dfs", " ".join(args))
    docker("smartcity_namenode", "hdfs", "dfs", *args)


def main():
    env = leer_env()
    usuario = env.get("MONGO_USER", "smartcity")
    clave = env.get("MONGO_PASSWORD", "smartcity123")
    uri = f"mongodb://{usuario}:{clave}@localhost:27017/smartcity?authSource=admin"

    # carpetas y datos de madrid
    hdfs("-mkdir", "-p", *CARPETAS)
    hdfs("-put", "-f", *MADRID, "/smartcity/raw/madrid/")

    # exporta cada coleccion de mongo y la sube
    for col in COLECCIONES:
        print(f"mongoexport {col}")
        docker("smartcity_mongo", "mongoexport", "--quiet", "--uri", uri,
               "--collection", col, "--out", f"/transfer/{col}.json")
        hdfs("-put", "-f", f"/transfer/{col}.json", "/smartcity/raw/mongo/")
        docker("smartcity_mongo", "rm", "-f", f"/transfer/{col}.json")

    hdfs("-du", "-h", "/smartcity/raw/madrid", "/smartcity/raw/mongo")


if __name__ == "__main__":
    main()
