"""Cinco preguntas de Hadoop. Solo biblioteca estandar; Python >= 3.6."""
import argparse
import base64
import json
import math
import sys
from datetime import datetime, timezone


UNIDADES = {
    "no2": "ug/m3", "pm10": "ug/m3", "pm25": "ug/m3", "co": "mg/m3",
    "o3": "ug/m3", "temperatura": "C", "humedad": "%", "precipitacion": "mm",
    "ruido_db": "dB", "intensidad": "veh/h", "ocupacion": "%", "carga": "0-100",
    "velocidad": "km/h", "ocupacion_parking": "%", "consumo_kwh": "kWh",
}
NOMBRES = {
    1: "Mediciones por sensor", 2: "Sensores con mas lecturas",
    3: "Temperatura promedio historica", 4: "Eventos por distrito",
    5: "Comportamiento diario de sensores en un periodo",
}
COLUMNAS = {
    1: ["id_sensor", "cantidad"], 2: ["id_sensor", "cantidad"],
    3: ["variable", "unidad", "cantidad", "promedio", "minimo", "maximo"],
    4: ["distrito", "cantidad"],
    5: ["dia", "id_sensor", "variable", "unidad", "cantidad", "promedio", "minimo", "maximo"],
}


def fecha(valor):
    """BSON Extended JSON relajado/canonico, ISO y limites del dashboard; UTC heredado."""
    if isinstance(valor, dict):
        valor = valor.get("$date")
    if isinstance(valor, dict):
        valor = int(valor["$numberLong"])
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(valor / 1000.0, timezone.utc)
    if not isinstance(valor, str):
        raise ValueError("Fecha ausente o invalida")
    texto = valor.replace("Z", "+0000")
    if len(texto) >= 6 and texto[-6] in "+-" and texto[-3] == ":":
        texto = texto[:-3] + texto[-2:]
    for patron in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                   "%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M:%S.%f",
                   "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            resultado = datetime.strptime(texto, patron)
            if resultado.tzinfo is None:
                resultado = resultado.replace(tzinfo=timezone.utc)
            return resultado.astimezone(timezone.utc)
        except ValueError:
            pass
    raise ValueError("Fecha ISO invalida: " + valor)


def filtros_validos(f):
    if bool(f.get("desde")) != bool(f.get("hasta")):
        raise ValueError("Indicar desde y hasta juntos")
    if f.get("desde") and fecha(f["desde"]) >= fecha(f["hasta"]):
        raise ValueError("El inicio debe ser anterior al fin")
    if f.get("variable", "temperatura") not in UNIDADES:
        raise ValueError("Variable desconocida")
    return f


def acepta(doc, f, consulta):
    if consulta == 3:  # Esta pregunta exige la temperatura de TODO el historico.
        return True
    if f.get("id_sensor") and doc.get("id_sensor") != f["id_sensor"]:
        return False
    distrito = (doc.get("ubicacion") or {}).get("distrito")
    if f.get("distritos") and distrito not in f["distritos"]:
        return False
    if consulta != 4 and f.get("tipos") and doc.get("tipo") not in f["tipos"]:
        return False
    if f.get("desde"):
        ts = fecha(doc.get("timestamp"))
        if not (f.get("_desde") or fecha(f["desde"])) <= ts < (f.get("_hasta") or fecha(f["hasta"])):
            return False
    return True


def valor_valido(doc, variable):
    invalidos = doc.get("invalidos")
    invalidos = invalidos if isinstance(invalidos, list) else []
    if doc.get("valido") is False and not invalidos:
        return None
    medicion = doc.get("medicion")
    v = medicion.get(variable) if isinstance(medicion, dict) else None
    if (variable in invalidos or isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v)):
        return None
    return v


def emitir(clave, valor, salida):
    salida.write(json.dumps(clave, ensure_ascii=True, separators=(",", ":")) + "\t"
                 + json.dumps(valor, allow_nan=False, separators=(",", ":")) + "\n")


def mapear(consulta, filtros, entrada, salida):
    filtros = dict(filtros_validos(filtros))
    if filtros.get("desde"):
        filtros["_desde"], filtros["_hasta"] = fecha(filtros["desde"]), fecha(filtros["hasta"])
    descartados = 0
    for linea in entrada:
        if not linea.strip():
            continue
        try:
            doc = json.loads(linea)
            if not isinstance(doc, dict):
                raise ValueError("Se esperaba un documento")
            if not acepta(doc, filtros, consulta):
                continue
            if consulta in (1, 2):
                if doc.get("id_sensor"):
                    emitir([doc["id_sensor"]], 1, salida)
            elif consulta == 4:
                distrito = (doc.get("ubicacion") or {}).get("distrito")
                if distrito:
                    emitir([distrito], 1, salida)
            else:
                variable = "temperatura" if consulta == 3 else filtros.get("variable", "temperatura")
                valor = valor_valido(doc, variable)
                if valor is None:
                    continue
                if consulta == 3:
                    clave = [variable, UNIDADES[variable]]
                else:
                    if not doc.get("id_sensor"):
                        continue
                    clave = [fecha(doc.get("timestamp")).strftime("%Y-%m-%d"),
                             doc["id_sensor"], variable, UNIDADES[variable]]
                emitir(clave, [1, valor, valor, valor], salida)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            descartados += 1
    if descartados:
        sys.stderr.write("reporter:counter:SmartCity,documentos_malformados,{}\n".format(descartados))


def reducir(consulta, entrada, salida):
    actual, acumulado = None, None

    def cerrar():
        if actual is None:
            return
        clave = json.loads(actual)
        if consulta in (1, 2, 4):
            resultado = clave + [acumulado]
        else:
            n, suma, minimo, maximo = acumulado
            resultado = clave + [n, suma / n, minimo, maximo]
        salida.write(json.dumps(resultado, ensure_ascii=True, allow_nan=False) + "\n")

    for linea in entrada:
        clave, texto = linea.rstrip("\r\n").split("\t", 1)
        valor = json.loads(texto)
        if clave != actual:
            cerrar()
            actual = clave
            acumulado = 0 if consulta in (1, 2, 4) else [0, 0.0, float("inf"), float("-inf")]
        if consulta in (1, 2, 4):
            acumulado += valor
        else:
            acumulado[0] += valor[0]
            acumulado[1] += valor[1]
            acumulado[2] = min(acumulado[2], valor[2])
            acumulado[3] = max(acumulado[3], valor[3])
    cerrar()


def mapear_maximo(entrada, salida):
    for linea in entrada:
        sensor, cantidad = json.loads(linea)
        emitir(["maximo"], [sensor, cantidad], salida)


def reducir_maximo(entrada, salida):
    mayor, sensores = -1, []
    for linea in entrada:
        _, texto = linea.rstrip("\r\n").split("\t", 1)
        sensor, cantidad = json.loads(texto)
        if cantidad > mayor:
            mayor, sensores = cantidad, [sensor]
        elif cantidad == mayor:
            sensores.append(sensor)
    for sensor in sorted(sensores):
        salida.write(json.dumps([sensor, mayor]) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("fase", choices=["map", "reduce", "max-map", "max-reduce"])
    p.add_argument("consulta", type=int, choices=sorted(NOMBRES))
    p.add_argument("--filtros", default="e30=")
    a = p.parse_args()
    f = json.loads(base64.urlsafe_b64decode(a.filtros.encode("ascii")).decode("utf-8"))
    if a.fase == "map":
        mapear(a.consulta, f, sys.stdin, sys.stdout)
    elif a.fase == "reduce":
        reducir(a.consulta, sys.stdin, sys.stdout)
    elif a.fase == "max-map":
        mapear_maximo(sys.stdin, sys.stdout)
    else:
        reducir_maximo(sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
