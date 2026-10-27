"""Ejecuta los mismos JavaScript en mongosh del contenedor. Solo requiere Python y Docker.

No carga datos, no cambia indices y no necesita copiar credenciales al equipo anfitrion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

AQUI = Path(__file__).resolve().parent


def comando(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError((r.stderr.strip() or r.stdout.strip() or f"Fallo: {args[0]}")[-4000:])
    return r.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modo", choices=["comprobar", "consultas", "crud", "controladas", "completa", "todo"])
    parser.add_argument("--contenedor", default="smartcity_mongo")
    parser.add_argument("--base", default="smartcity")
    parser.add_argument("--salida", type=Path, help="Carpeta NUEVA para la evidencia; no sobrescribe resultados anteriores")
    args = parser.parse_args()
    if args.salida and args.salida.exists():
        parser.error("La carpeta de salida ya existe; elegir otra para preservar la evidencia")
    destino = "/tmp/smartcity_personad_" + uuid.uuid4().hex
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
              for f in sorted(AQUI.iterdir()) if f.suffix in (".js", ".py")}
    comando(["docker", "exec", args.contenedor, "mkdir", "-p", destino])
    try:
        for archivo in sorted(AQUI.glob("*.js")):
            comando(["docker", "cp", str(archivo), f"{args.contenedor}:{destino}/{archivo.name}"])
        print(f"Ejecutando {args.modo} en {args.contenedor}/{args.base}...", file=sys.stderr, flush=True)
        texto = comando(["docker", "exec", "-e", f"SC_CONSULTAS_DIR={destino}", "-e", f"SC_MODO={args.modo}",
                         "-e", f"SC_BASE={args.base}", args.contenedor, "mongosh", "--quiet", "--file", destino+"/entrada.js"])
        resultado = json.loads(texto)
        resultado["codigo_sha256"] = hashes
        if args.salida:
            args.salida.mkdir(parents=True, exist_ok=False)
            (args.salida/"validacion.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"modo":args.modo, "aprobado":resultado.get("aprobado"),
                          "salida":str(args.salida) if args.salida else None,
                          "resumen":resultado.get("resumen")}, ensure_ascii=False, indent=2))
        if not args.salida:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0 if resultado.get("aprobado", True) else 1
    finally:
        # Ruta literal generada por este proceso dentro de /tmp; nunca incluye datos del proyecto.
        comando(["docker", "exec", args.contenedor, "rm", "-rf", "--", destino])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
