"""PROPOSITO: responder las cinco preguntas de Hadoop mediante MapReduce.
Recibe: argumentos fase/consulta/filtros y registros de texto por entrada estandar.
Devuelve: pares intermedios clave-tab-valor o filas JSON por salida estandar.
Las filas finales siguen el orden de COLUMNAS; los errores de datos van a stderr.
Hadoop Streaming ejecuta este archivo con Python 3.6 en el NodeManager.
CRITERIO: contar documentos crudos y usar valores validos para las estadisticas.
El almacenamiento HDFS y la asignacion de recursos YARN quedan a cargo de Hadoop."""
import argparse
import base64
import json
import math
import sys
from datetime import datetime, timezone


# CATALOGOS: cada variable conserva su unidad; no se promedian magnitudes distintas.
UNIDADES = {
    "no2": "ug/m3", "pm10": "ug/m3", "pm25": "ug/m3", "co": "mg/m3",
    "o3": "ug/m3", "temperatura": "C", "humedad": "%", "precipitacion": "mm",
    "ruido_db": "dB", "intensidad": "veh/h", "ocupacion": "%", "carga": "0-100",
    "velocidad": "km/h", "ocupacion_parking": "%", "consumo_kwh": "kWh",
}
# Los IDs se comparten con el ejecutor y el selector del dashboard.
NOMBRES = {
    1: "Mediciones por sensor", 2: "Sensores con mas lecturas",
    3: "Temperatura promedio historica", 4: "Eventos por distrito",
    5: "Comportamiento diario de sensores en un periodo",
}
# Contrato de salida: permite convertir las listas JSON finales en tablas con encabezados.
COLUMNAS = {
    1: ["id_sensor", "cantidad"], 2: ["id_sensor", "cantidad"],
    3: ["variable", "unidad", "cantidad", "promedio", "minimo", "maximo"],
    4: ["distrito", "cantidad"],
    5: ["dia", "id_sensor", "variable", "unidad", "cantidad", "promedio", "minimo", "maximo"],
}


def fecha(valor):
    """Interpretar una fecha del archivo exportado o de los filtros.
    Recibe: valor ISO, milisegundos Unix o un objeto Extended JSON con $date.
    Devuelve: datetime con zona UTC; lanza un error si no puede interpretar el valor.
    Las fechas sin zona conservan la interpretacion UTC heredada de la ingesta."""
    # ETAPA 1: desenvolver Extended JSON relajado ($date ISO) o canonico ($numberLong).
    if isinstance(valor, dict):
        valor = valor.get("$date")
    if isinstance(valor, dict):
        valor = int(valor["$numberLong"])
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(valor / 1000.0, timezone.utc)
    if not isinstance(valor, str):
        raise ValueError("Fecha ausente o invalida")
    # ETAPA 2: adaptar Z y offsets con dos puntos al lector de fechas de Python 3.6.
    texto = valor.replace("Z", "+0000")
    if len(texto) >= 6 and texto[-6] in "+-" and texto[-3] == ":":
        texto = texto[:-3] + texto[-2:]
    for patron in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                   "%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M:%S.%f",
                   "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            resultado = datetime.strptime(texto, patron)
            # Una fecha ingenua se interpreta como UTC; esto no corrige la ingesta a hora de Madrid.
            if resultado.tzinfo is None:
                resultado = resultado.replace(tzinfo=timezone.utc)
            return resultado.astimezone(timezone.utc)
        except ValueError:
            pass
    raise ValueError("Fecha ISO invalida: " + valor)


def filtros_validos(f):
    """Validar el contrato minimo de los parametros de una consulta.
    Recibe: f, diccionario con desde/hasta opcionales y una variable conocida.
    Devuelve: el mismo diccionario; lanza ValueError ante un rango o variable invalida.
    Exigir las dos fechas y desde < hasta evita periodos incompletos o invertidos."""
    if bool(f.get("desde")) != bool(f.get("hasta")):
        raise ValueError("Indicar desde y hasta juntos")
    if f.get("desde") and fecha(f["desde"]) >= fecha(f["hasta"]):
        raise ValueError("El inicio debe ser anterior al fin")
    if f.get("variable", "temperatura") not in UNIDADES:
        raise ValueError("Variable desconocida")
    return f


def acepta(doc, f, consulta):
    """Decidir si un documento pertenece al alcance solicitado.
    Recibe: doc, filtros f y numero de consulta; f puede traer fechas ya interpretadas.
    Devuelve: True si pasa los filtros de sensor, distrito, tipo y periodo; False si no.
    La consulta 3 usa todo el historico. La 4 no filtra por tipo de sensor.
    La calidad de cada valor estadistico se comprueba despues, en valor_valido."""
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
    """Seleccionar una medicion util para promedio, minimo y maximo.
    Recibe: un documento y el nombre de la variable solicitada.
    Devuelve: el numero original si es valido y finito; None si debe excluirse.
    Una variable sana puede contribuir aunque otra este marcada en invalidos."""
    # CALIDAD: una lista por variable permite rescatar las mediciones sanas del documento.
    invalidos = doc.get("invalidos")
    invalidos = invalidos if isinstance(invalidos, list) else []
    if doc.get("valido") is False and not invalidos:
        return None
    medicion = doc.get("medicion")
    v = medicion.get(variable) if isinstance(medicion, dict) else None
    # bool es subclase de int en Python: excluirlo junto con texto, nulos, NaN e infinitos.
    if (variable in invalidos or isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v)):
        return None
    return v


def emitir(clave, valor, salida):
    """Escribir un par con el formato que Hadoop Streaming puede agrupar.
    Recibe: clave y valor serializables a JSON, y salida, un flujo de texto escribible.
    Devuelve: None; escribe una linea clave JSON + tabulador + valor JSON.
    Escapar la clave en ASCII da una representacion estable para ordenar y agrupar."""
    salida.write(json.dumps(clave, ensure_ascii=True, separators=(",", ":")) + "\t"
                 + json.dumps(valor, allow_nan=False, separators=(",", ":")) + "\n")


def mapear(consulta, filtros, entrada, salida):
    """Transformar cada documento de entrada en una contribucion al calculo.
    Recibe: ID de consulta, filtros, entrada iterable de lineas JSON y flujo de salida.
    Devuelve: None; emite pares intermedios mediante emitir y contadores en stderr.
    1/2 cuentan por sensor; 4 cuenta por distrito; 3/5 acumulan estadisticas de valores.
    Se procesa linea por linea para no cargar el archivo historico entero en memoria."""
    # ETAPA 1: copiar los filtros y convertir sus fechas una vez por tarea Map.
    filtros = dict(filtros_validos(filtros))
    if filtros.get("desde"):
        filtros["_desde"], filtros["_hasta"] = fecha(filtros["desde"]), fecha(filtros["hasta"])
    # ETAPA 2: leer y filtrar documentos sin confundir datos invalidos con registros malformados.
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
            # CONTEOS: cada documento aporta 1; su numero de variables y valido no cambian ese conteo.
            if consulta in (1, 2):
                if doc.get("id_sensor"):
                    emitir([doc["id_sensor"]], 1, salida)
            # EVENTOS: la entrada de esta consulta es eventos.json; la clave es el distrito.
            elif consulta == 4:
                distrito = (doc.get("ubicacion") or {}).get("distrito")
                if distrito:
                    emitir([distrito], 1, salida)
            else:
                variable = "temperatura" if consulta == 3 else filtros.get("variable", "temperatura")
                valor = valor_valido(doc, variable)
                if valor is None:
                    continue
                # ESTADISTICAS: la 3 agrupa todo por variable/unidad; la 5 separa dia y sensor.
                if consulta == 3:
                    clave = [variable, UNIDADES[variable]]
                else:
                    if not doc.get("id_sensor"):
                        continue
                    clave = [fecha(doc.get("timestamp")).strftime("%Y-%m-%d"),
                             doc["id_sensor"], variable, UNIDADES[variable]]
                # La contribucion lleva [cantidad, suma, minimo, maximo]; un valor aporta una muestra.
                emitir(clave, [1, valor, valor, valor], salida)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            descartados += 1
    # DIAGNOSTICO: stderr transporta contadores YARN y mantiene stdout reservado para datos.
    if descartados:
        sys.stderr.write("reporter:counter:SmartCity,documentos_malformados,{}\n".format(descartados))


def reducir(consulta, entrada, salida):
    """Acumular las contribuciones de cada clave ya agrupada por Hadoop.
    Recibe: ID de consulta, lineas clave-tab-valor ordenadas por clave y salida.
    Devuelve: None; escribe una fila JSON por grupo con el orden definido en COLUMNAS.
    Para 2 produce conteos por sensor; el maximo global se obtiene en otro trabajo."""
    actual, acumulado = None, None

    def cerrar():
        """Terminar el grupo que se esta acumulando.
        Recibe: ningun argumento; usa actual, acumulado, consulta y salida del reducer.
        Devuelve: None; escribe el grupo actual, o no escribe nada si aun no hay grupo.
        En estadisticas divide la suma entre la cantidad real de muestras del grupo."""
        if actual is None:
            return
        clave = json.loads(actual)
        if consulta in (1, 2, 4):
            resultado = clave + [acumulado]
        else:
            n, suma, minimo, maximo = acumulado
            resultado = clave + [n, suma / n, minimo, maximo]
        salida.write(json.dumps(resultado, ensure_ascii=True, allow_nan=False) + "\n")

    # ETAPA REDUCE: Hadoop entrega las claves contiguas; solo se conserva un grupo en memoria.
    for linea in entrada:
        clave, texto = linea.rstrip("\r\n").split("\t", 1)
        valor = json.loads(texto)
        # Al cambiar de clave se cierra el grupo anterior y se inicializa el siguiente.
        if clave != actual:
            cerrar()
            actual = clave
            acumulado = 0 if consulta in (1, 2, 4) else [0, 0.0, float("inf"), float("-inf")]
        if consulta in (1, 2, 4):
            acumulado += valor
        else:
            # Sumar cantidades y sumas permite combinar aportes de distinto tamano sin sesgar el promedio.
            acumulado[0] += valor[0]
            acumulado[1] += valor[1]
            acumulado[2] = min(acumulado[2], valor[2])
            acumulado[3] = max(acumulado[3], valor[3])
    # Cerrar tambien el ultimo grupo: no existe una siguiente clave que lo dispare.
    cerrar()


def mapear_maximo(entrada, salida):
    """Preparar los conteos del primer trabajo para buscar el maximo global.
    Recibe: filas JSON [sensor, cantidad] y un flujo de salida.
    Devuelve: None; emite todos los conteos bajo la clave comun ["maximo"].
    Una clave comun hace que el siguiente reducer compare los sensores entre si."""
    for linea in entrada:
        sensor, cantidad = json.loads(linea)
        emitir(["maximo"], [sensor, cantidad], salida)


def reducir_maximo(entrada, salida):
    """Encontrar el mayor conteo y conservar todos los sensores empatados.
    Recibe: pares de la segunda fase Map, con [sensor, cantidad] como valor.
    Devuelve: None; escribe filas JSON [sensor, maximo], ordenadas por sensor.
    Si no recibe registros, la salida queda vacia en lugar de inventar un ganador."""
    mayor, sensores = -1, []
    for linea in entrada:
        _, texto = linea.rstrip("\r\n").split("\t", 1)
        sensor, cantidad = json.loads(texto)
        # Un nuevo maximo reemplaza los candidatos; un empate agrega otro sensor al resultado.
        if cantidad > mayor:
            mayor, sensores = cantidad, [sensor]
        elif cantidad == mayor:
            sensores.append(sensor)
    for sensor in sorted(sensores):
        salida.write(json.dumps([sensor, mayor]) + "\n")


def main():
    """Elegir la fase que Hadoop solicito ejecutar en este proceso.
    Recibe: fase, consulta y filtros Base64 desde los argumentos de la terminal.
    Devuelve: None; conecta stdin/stdout con el mapper o reducer correspondiente.
    El valor e30= representa {}: filtros vacios cuando no se especifican otros."""
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
