import math
import random
from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd

from comun import (RAW, INICIO, FIN, FECHA_BAJA, SEMILLA, DISTRITOS, VARIABLES, MAGNITUDES,
                   ORG_MOV, ORG_ELEC, conectar_pg, conectar_mongo)

rng = random.Random(SEMILLA)
nrng = np.random.default_rng(SEMILLA)
INI = pd.Timestamp(INICIO)
FIN_TS = pd.Timestamp(FIN)
BAJA = pd.Timestamp(FECHA_BAJA).to_pydatetime()
TAM_LOTE = 20000


class Cargador:
    def __init__(self, db):
        self.db = db
        self.lotes = defaultdict(list)
        self.total = defaultdict(int)
        self.vistos = set()

    def agregar(self, coleccion, doc):
        self.lotes[coleccion].append(doc)
        if len(self.lotes[coleccion]) >= TAM_LOTE:
            self.vaciar(coleccion)

    def vaciar(self, coleccion):
        if self.lotes[coleccion]:
            self.db[coleccion].insert_many(self.lotes[coleccion], ordered=False)
            self.total[coleccion] += len(self.lotes[coleccion])
            self.lotes[coleccion] = []

    def cerrar(self):
        for col in list(self.lotes):
            self.vaciar(col)


def leer_sensores():
    con = conectar_pg()
    filas = con.execute("""
        SELECT s.id_sensor, s.codigo_origen, t.nombre, c.nombre_categoria, s.estado,
               u.nombre_zona, u.latitud, u.longitud, d.nombre
        FROM sensor s
        JOIN tipo_sensor t ON t.id_tipo = s.id_tipo
        JOIN categoria_sensor c ON c.id_categoria = t.id_categoria
        JOIN ubicacion u ON u.id_ubicacion = s.id_ubicacion
        JOIN distrito d ON d.id_distrito = u.id_distrito""").fetchall()
    con.close()
    sensores = {}
    for sid, cod, tipo, cat, estado, lugar, lat, lon, distrito in filas:
        sensores[(tipo, cod)] = {"id": sid, "codigo": cod, "tipo": tipo, "categoria": cat, "estado": estado,
                                 "lugar": lugar, "lat": float(lat), "lon": float(lon), "distrito": distrito}
    return sensores


def lectura(s, ts, medicion, invalidos=None, extra=None):
    doc = {
        "id_sensor": s["id"],
        "codigo_origen": s["codigo"],
        "tipo": s["tipo"],
        "categoria": s["categoria"],
        "ubicacion": {
            "distrito": s["distrito"],
            "nombre": s["lugar"],
            "geo": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
        },
        "medicion": medicion,
        "valido": not invalidos,
        "timestamp": ts,
    }
    if invalidos:
        doc["invalidos"] = invalidos
    if extra:
        doc.update(extra)
    return doc


def severidad(proporcion):
    if proporcion < 1.1:
        return "baja"
    if proporcion < 1.3:
        return "media"
    if proporcion < 1.5:
        return "alta"
    return "critica"


def evento(c, s, ts, tipo_evento, sev, detalles):
    clave = (s["id"], ts.date(), tipo_evento)
    if clave in c.vistos:
        return
    c.vistos.add(clave)
    c.agregar("eventos", {
        "tipo_evento": tipo_evento,
        "severidad": sev,
        "id_sensor": s["id"],
        "ubicacion": {"distrito": s["distrito"]},
        "timestamp": ts,
        "detalles": detalles,
    })


def revisar(c, s, doc):
    ts = doc["timestamp"]
    invalidos = doc.get("invalidos", [])
    if invalidos:
        evento(c, s, ts, "falla_sensor", "media", {"variables_invalidas": invalidos})

    for var, valor in doc["medicion"].items():
        if var in invalidos or valor is None:
            continue
        limite = VARIABLES[var][1]
        if limite is None or valor <= limite:
            continue
        prop = valor / limite
        c.agregar("alertas", {
            "id_sensor": s["id"],
            "variable": var,
            "valor": valor,
            "limite": limite,
            "nivel": "advertencia" if prop <= 1.5 else "critica",
            "ubicacion": {"distrito": s["distrito"]},
            "timestamp": ts,
            "atendida": ts < BAJA and rng.random() < 0.8,
        })
        if var == "carga":
            evento(c, s, ts, "congestion", severidad(prop), dict(doc["medicion"]))
        elif s["tipo"] == "calidad_aire" and prop > 1.5:
            evento(c, s, ts, "pico_contaminacion", "critica", {var: valor, "limite": limite})
        elif var == "ruido_db" and valor > 75:
            evento(c, s, ts, "ruido_excesivo", severidad(prop), {var: valor})
        elif var == "consumo_kwh":
            evento(c, s, ts, "pico_consumo", severidad(prop), {var: valor})


def guardar(c, s, doc):
    c.agregar("lecturas", doc)
    revisar(c, s, doc)


def cargar_aire(c, sensores):
    partes = []
    for f in sorted((RAW / "aire").rglob("*.csv")):
        if "estaciones" in f.name:
            continue
        df = pd.read_csv(f, sep=";", dtype=str, encoding="utf-8-sig")
        df.columns = [col.strip().strip('"') for col in df.columns]
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df = df[df["MAGNITUD"].astype(int).isin(MAGNITUDES)]

    horas = []
    for h in range(1, 25):
        t = df[["ESTACION", "MAGNITUD", "ANO", "MES", "DIA", f"H{h:02d}", f"V{h:02d}"]].copy()
        t.columns = ["est", "mag", "ano", "mes", "dia", "valor", "val"]
        t["hora"] = h - 1
        horas.append(t)
    largo = pd.concat(horas, ignore_index=True)

    largo["ts"] = pd.to_datetime(dict(year=largo["ano"].astype(int), month=largo["mes"].astype(int),
                                      day=largo["dia"].astype(int), hour=largo["hora"]), errors="coerce")
    largo = largo[(largo["ts"] >= INI) & (largo["ts"] <= FIN_TS)]
    largo["valor"] = pd.to_numeric(largo["valor"].str.replace(",", "."), errors="coerce")
    largo = largo.dropna(subset=["ts", "valor"])
    largo["var"] = largo["mag"].astype(int).map(MAGNITUDES)
    largo["codigo"] = "28079" + largo["est"].astype(int).map("{:03d}".format)
    largo["invalido"] = largo["val"].str.strip() != "V"

    valores = largo.pivot_table(index=["codigo", "ts"], columns="var", values="valor", aggfunc="first")
    malos = largo.pivot_table(index=["codigo", "ts"], columns="var", values="invalido", aggfunc="first")
    malos = malos.reindex(index=valores.index, columns=valores.columns)

    columnas = list(valores.columns)
    for (codigo, ts), fila_v, fila_m in zip(valores.index, valores.to_numpy(), malos.to_numpy()):
        s = sensores.get(("calidad_aire", codigo))
        if s is None:
            continue
        medicion, invalidos = {}, []
        for var, v, m in zip(columnas, fila_v, fila_m):
            if isinstance(v, float) and math.isnan(v):
                continue
            medicion[var] = float(v)
            if m is True or m == 1:
                invalidos.append(var)
        if medicion:
            guardar(c, s, lectura(s, ts.to_pydatetime(), medicion, invalidos))


def cargar_trafico(c, sensores):
    activos = {int(cod): s for (tipo, cod), s in sensores.items()
               if tipo == "trafico" and s["estado"] != "mantenimiento"}
    for f in sorted((RAW / "trafico").glob("*/*.csv")):
        print("  ", f.name)
        for parte in pd.read_csv(f, sep=";", chunksize=2_000_000):
            parte = parte[parte["id"].isin(list(activos))]
            parte = parte.fillna({"intensidad": -1, "ocupacion": -1, "carga": -1, "vmed": -1, "error": "N"})
            fechas = pd.to_datetime(parte["fecha"])
            for pid, ts, tipo_elem, inten, ocup, carga, vmed, error in zip(
                    parte["id"], fechas, parte["tipo_elem"], parte["intensidad"], parte["ocupacion"],
                    parte["carga"], parte["vmed"], parte["error"]):
                s = activos[pid]
                ts = ts.to_pydatetime()
                if s["estado"] == "inactivo" and ts >= BAJA:
                    continue
                medicion = {"intensidad": int(inten), "ocupacion": int(ocup), "carga": int(carga)}
                if tipo_elem in ("M30", "C30"):
                    medicion["velocidad"] = int(vmed)
                if error == "S":
                    invalidos = list(medicion)
                else:
                    invalidos = [k for k, v in medicion.items() if v < 0]
                guardar(c, s, lectura(s, ts, medicion, invalidos, {"error": error}))


def cargar_clima(c, sensores):
    for cod, nombre, _, _ in DISTRITOS:
        f = RAW / "clima" / f"clima_{cod:02d}.csv"
        if not f.exists():
            print("   falta", f.name, "(corra clima.py)")
            continue
        s = sensores[("meteorologico", f"OM-{cod:02d}")]
        df = pd.read_csv(f)
        fechas = pd.to_datetime(df["fecha"])
        for ts, temp, hum, prec in zip(fechas, df["temperatura"], df["humedad"], df["precipitacion"]):
            medicion = {}
            for k, v in (("temperatura", temp), ("humedad", hum), ("precipitacion", prec)):
                if not pd.isna(v):
                    medicion[k] = float(v)
            if medicion:
                guardar(c, s, lectura(s, ts.to_pydatetime(), medicion))


def patron_energia():
    df = pd.read_csv(RAW / "energia" / "household_power_consumption.txt", sep=";",
                     usecols=["Date", "Time", "Global_active_power"], na_values="?", low_memory=False)
    df = df.dropna()
    df["dia"] = pd.to_datetime(df["Date"], format="%d/%m/%Y").dt.dayofweek
    df["h"] = df["Time"].str[:2].astype(int)
    p = df.groupby(["dia", "h"])["Global_active_power"].mean()
    return (p / p.mean()).to_dict()


def serie(desde, hasta):
    return pd.date_range(desde, hasta, freq="h")


def cargar_generados(c, sensores):
    print("   patron de energia (UCI)...")
    perfil = patron_energia()
    for (tipo, cod), s in sensores.items():
        if tipo not in ("medidor_energia", "estacionamiento", "ruido") or s["estado"] == "mantenimiento":
            continue
        if tipo == "medidor_energia":
            horas = serie("2025-01-01", FIN_TS)
            base = rng.uniform(180, 260)
            estacion = 1 + 0.12 * np.abs(np.cos(2 * np.pi * horas.dayofyear / 365))
            forma = np.array([perfil[(d, h)] for d, h in zip(horas.dayofweek, horas.hour)])
            valores = base * forma * estacion * nrng.normal(1, 0.06, len(horas))
            var = "consumo_kwh"
        elif tipo == "estacionamiento":
            horas = serie("2026-06-01", FIN_TS)
            base = rng.uniform(45, 70)
            pico = 28 * np.exp(-((horas.hour - 13) / 4) ** 2)
            finde = np.where(horas.dayofweek >= 5, 0.8, 1.0)
            valores = np.clip((base + pico) * finde + nrng.normal(0, 5, len(horas)), 0, 100)
            var = "ocupacion_parking"
        else:
            horas = serie("2026-06-01", FIN_TS)
            dia = 10 * np.exp(-((horas.hour - 14) / 5) ** 2) + 4 * np.exp(-((horas.hour - 8) / 1.5) ** 2)
            valores = 50 + dia + nrng.normal(0, 4, len(horas))
            var = "ruido_db"

        for ts, v in zip(horas, valores):
            ts = ts.to_pydatetime()
            if s["estado"] == "inactivo" and ts >= BAJA:
                break
            guardar(c, s, lectura(s, ts, {var: round(float(v), 2)}))


def cargar_incidentes(c, n=4000):
    categorias = {
        "accidente_transito": (0.45, ORG_MOV, "Accidente de transito en {d}"),
        "arbol_caido": (0.15, ORG_MOV, "Arbol caido sobre la via en {d}"),
        "inundacion": (0.1, ORG_MOV, "Calle inundada por lluvia en {d}"),
        "corte_electrico": (0.15, ORG_ELEC, "Corte de luz en varias manzanas de {d}"),
        "manifestacion": (0.15, ORG_MOV, "Manifestacion con corte de calles en {d}"),
    }
    nombres = list(categorias)
    pesos = [categorias[k][0] for k in nombres]
    segundos = int((FIN_TS - INI).total_seconds())
    limite_abiertos = (FIN_TS - timedelta(days=30)).to_pydatetime()

    for _ in range(n):
        cat = rng.choices(nombres, pesos)[0]
        _, org, texto = categorias[cat]
        distrito = rng.choice(DISTRITOS)[1]
        fecha = (INI + timedelta(seconds=rng.randint(0, segundos))).to_pydatetime()
        if fecha < limite_abiertos:
            estado = "cerrado" if rng.random() < 0.95 else "en_proceso"
        else:
            estado = rng.choice(["abierto", "en_proceso", "cerrado"])

        if cat == "accidente_transito":
            extra = {"vehiculos_involucrados": rng.randint(1, 4), "heridos": rng.choice([0, 0, 0, 1, 2])}
        elif cat == "arbol_caido":
            extra = {"bloquea_via": rng.random() < 0.4}
        elif cat == "inundacion":
            extra = {"nivel_agua_cm": rng.randint(5, 60), "calles_cerradas": rng.randint(0, 3)}
        elif cat == "corte_electrico":
            extra = {"clientes_afectados": rng.randint(50, 5000), "duracion_min": rng.randint(10, 480)}
        else:
            extra = {"asistentes_estimados": rng.randint(100, 20000), "calles_cortadas": rng.randint(1, 6)}

        c.agregar("incidentes", {
            "categoria": cat,
            "descripcion": texto.format(d=distrito),
            "ubicacion": {"distrito": distrito},
            "fecha_reporte": fecha,
            "estado": estado,
            "organismo": org,
            "datos_extra": extra,
        })


def main():
    sensores = leer_sensores()
    db = conectar_mongo()
    for col in ["lecturas", "alertas", "eventos", "incidentes"]:
        db[col].drop()

    c = Cargador(db)
    print("Calidad del aire...")
    cargar_aire(c, sensores)
    print("Trafico...")
    cargar_trafico(c, sensores)
    print("Clima...")
    cargar_clima(c, sensores)
    print("Energia, parking y ruido...")
    cargar_generados(c, sensores)
    print("Incidentes...")
    cargar_incidentes(c)
    c.cerrar()

    for col in ["lecturas", "alertas", "eventos", "incidentes"]:
        print(f"{col}: {db[col].count_documents({})}")


if __name__ == "__main__":
    main()
