"""Prueba los scripts desde cero en un MongoDB efimero de la misma imagen local.

No reproduce la descarga ni la carga completa de Cesar; esas son responsabilidades
de integracion. No publica puertos ni monta volumenes del proyecto.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

from ejecutar import AQUI, comando


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--origen", default="smartcity_mongo")
    p.add_argument("--salida", type=Path, required=True)
    args = p.parse_args()
    if args.salida.exists():
        p.error("La salida ya existe")
    imagen = comando(["docker", "inspect", "--format", "{{.Image}}", args.origen]).strip()
    nombre = "smartcity_personad_limpio_" + uuid.uuid4().hex
    creado = False
    try:
        comando(["docker", "run", "-d", "--name", nombre, "--label", "smartcity.persona=d", imagen])
        creado = True
        for _ in range(30):
            r = subprocess.run(["docker", "exec", nombre, "mongosh", "--quiet", "--eval", "db.runCommand({ping:1})"], capture_output=True)
            if r.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("El MongoDB temporal no inicio")
        codigo = subprocess.call([sys.executable, str(AQUI/"ejecutar.py"), "controladas", "--contenedor", nombre, "--salida", str(args.salida)])
        (args.salida/"entorno.json").write_text(json.dumps({"imagen_id":imagen,"contenedor_temporal":nombre,
            "volumenes_del_proyecto":False,"puertos_publicados":False,"alcance":"Scripts y fixtures; no carga masiva ni stack completo"},indent=2)+"\n",encoding="utf-8")
        return codigo
    finally:
        if creado:
            # Solo el contenedor de nombre aleatorio creado arriba y sus volumenes anonimos.
            comando(["docker", "rm", "-f", "-v", nombre])


if __name__ == "__main__":
    sys.exit(main())
