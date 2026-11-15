import json
import sys


def leer():
    for linea in sys.stdin:
        try:
            yield json.loads(linea)
        except ValueError:
            continue


# map: cada linea es una lectura de mongo
def mapear(c):
    for doc in leer():
        fecha = doc["timestamp"]["$date"]
        if c == "c1":
            if doc["id_sensor"] == "S-00002" and fecha.startswith("2025-03"):
                print("S-00002\t1")
        elif c == "c2":
            no2 = (doc.get("medicion") or {}).get("no2")
            malo = "no2" in (doc.get("invalidos") or [])
            if doc["tipo"] == "calidad_aire" and fecha.startswith("2025-01") and no2 is not None and not malo:
                print("%s\t%s" % (doc["ubicacion"]["distrito"], no2))
        elif c == "c3":
            print("%s|%s\t1" % (doc["tipo"], fecha[:4]))


def emitir(c, clave, suma, n):
    if c == "c2":
        print("%s\t%.3f" % (clave, suma / n))
    else:
        print("%s\t%d" % (clave, int(suma)))


# reduce: llegan ordenadas por clave, se suman
def reducir(c):
    actual, suma, n = None, 0.0, 0
    for linea in sys.stdin:
        clave, valor = linea.rstrip("\n").split("\t")
        if clave != actual:
            if actual is not None:
                emitir(c, actual, suma, n)
            actual, suma, n = clave, 0.0, 0
        suma += float(valor)
        n += 1
    if actual is not None:
        emitir(c, actual, suma, n)


if __name__ == "__main__":
    if sys.argv[1] == "map":
        mapear(sys.argv[2])
    else:
        reducir(sys.argv[2])
