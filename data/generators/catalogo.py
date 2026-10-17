import random
import unicodedata
from datetime import date, datetime, timedelta

import pandas as pd

from comun import (RAW, SEMILLA, DISTRITOS, ORGANISMOS, TIPOS, VARIABLES,
                   ORG_EMT, conectar_pg)

rng = random.Random(SEMILLA)


def sin_tildes(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).strip()


def fecha_random(desde, hasta):
    d0 = date.fromisoformat(desde)
    d1 = date.fromisoformat(hasta)
    return d0 + timedelta(days=rng.randint(0, (d1 - d0).days))


def cerca(lat, lon, m=0.008):
    return round(lat + rng.uniform(-m, m), 6), round(lon + rng.uniform(-m, m), 6)


def leer_estaciones():
    ruta = next((RAW / "aire").glob("*estaciones*.csv"))
    return pd.read_csv(ruta, sep=";", encoding="utf-8-sig")


def leer_puntos_trafico():
    ruta = sorted((RAW / "trafico").glob("*.csv"))[0]
    df = pd.read_csv(ruta, sep=";", encoding="latin-1")
    df = df.dropna(subset=["distrito", "latitud", "longitud"])
    df["distrito"] = df["distrito"].astype(int)
    df["id"] = df["id"].astype(int)
    return df[df["distrito"].between(1, 21)]


def ids_con_datos():
    archivos = sorted((RAW / "trafico").glob("*/*.csv"))
    if not archivos:
        return set()
    print("Leyendo ids de", archivos[0].name, "...")
    ids = pd.read_csv(archivos[0], sep=";", usecols=["id"])["id"].unique()
    return set(int(i) for i in ids)


def distrito_cercano(lat, lon, puntos):
    d = (puntos["latitud"] - lat) ** 2 + ((puntos["longitud"] - lon) * 0.76) ** 2
    return int(puntos.loc[d.idxmin(), "distrito"])


def main():
    estaciones = leer_estaciones()
    puntos = leer_puntos_trafico()
    con_datos = ids_con_datos()

    con = conectar_pg()
    cur = con.cursor()
    cur.execute("""TRUNCATE medicion, ruta_estacion, vehiculo, estacion, ruta, sensor, usuario,
                   organismo, variable, tipo_sensor, categoria_sensor, ubicacion, distrito, ciudad
                   RESTART IDENTITY CASCADE""")

    id_ciudad = cur.execute(
        "INSERT INTO ciudad (nombre, pais) VALUES ('Madrid', 'Espana') RETURNING id_ciudad").fetchone()[0]

    distritos = {}
    for cod, nombre, lat, lon in DISTRITOS:
        distritos[cod] = cur.execute(
            "INSERT INTO distrito (id_ciudad, nombre) VALUES (%s, %s) RETURNING id_distrito",
            (id_ciudad, nombre)).fetchone()[0]

    categorias = {}
    for cat in sorted({c for c, _ in TIPOS.values()}):
        categorias[cat] = cur.execute(
            "INSERT INTO categoria_sensor (nombre_categoria) VALUES (%s) RETURNING id_categoria",
            (cat,)).fetchone()[0]

    tipos = {}
    for tipo, (cat, _) in TIPOS.items():
        tipos[tipo] = cur.execute(
            "INSERT INTO tipo_sensor (id_categoria, nombre) VALUES (%s, %s) RETURNING id_tipo",
            (categorias[cat], tipo)).fetchone()[0]

    cur.executemany("INSERT INTO variable (nombre, unidad, limite_alerta) VALUES (%s, %s, %s)",
                    [(v, u, l) for v, (u, l) in VARIABLES.items()])

    organismos = {}
    for nombre, responsable in ORGANISMOS:
        organismos[nombre] = cur.execute(
            "INSERT INTO organismo (nombre, responsable) VALUES (%s, %s) RETURNING id_organismo",
            (nombre, responsable)).fetchone()[0]

    nombres = ["Lucia", "Hugo", "Martina", "Daniel", "Sofia", "Pablo", "Elena", "Alvaro", "Carmen", "Javier"]
    apellidos = ["Garcia", "Lopez", "Martin", "Sanchez", "Perez", "Gomez", "Ruiz", "Diaz", "Moreno", "Navarro"]
    usuarios = []
    for i in range(20):
        n, a = nombres[i % 10], apellidos[(i * 3) % 10]
        org = ORGANISMOS[i % 4][0]
        dominio = "emt.es" if org == ORG_EMT else "madrid.es"
        usuarios.append((f"{n} {a}", f"{n.lower()}.{a.lower()}{i}@{dominio}", organismos[org]))
    cur.executemany("INSERT INTO usuario (nombre, correo, id_organismo) VALUES (%s, %s, %s)", usuarios)

    def ubicacion(cod_distrito, nombre, lat, lon):
        return cur.execute(
            "INSERT INTO ubicacion (id_distrito, nombre_zona, latitud, longitud) VALUES (%s, %s, %s, %s) RETURNING id_ubicacion",
            (distritos[cod_distrito], sin_tildes(nombre)[:100], round(float(lat), 6), round(float(lon), 6))).fetchone()[0]

    sensores = []

    def nuevo_sensor(codigo, nombre, tipo, id_ubicacion, fecha, estado="activo"):
        sid = f"S-{len(sensores) + 1:05d}"
        org = organismos[TIPOS[tipo][1]]
        sensores.append([sid, str(codigo), sin_tildes(nombre)[:150], tipos[tipo], id_ubicacion, org, fecha, estado])
        return len(sensores) - 1

    for _, e in estaciones.iterrows():
        cod_d = distrito_cercano(e["LATITUD"], e["LONGITUD"], puntos)
        u = ubicacion(cod_d, e["ESTACION"], e["LATITUD"], e["LONGITUD"])
        alta = datetime.strptime(str(e["Fecha alta"]), "%d/%m/%Y").date()
        nuevo_sensor(e["CODIGO"], f"Aire - {e['ESTACION']}", "calidad_aire", u, alta)

    generados = {"medidor_energia": [], "estacionamiento": [], "ruido": []}
    etiquetas = {"medidor_energia": ("ENE", "Energia"), "estacionamiento": ("PAR", "Parking"), "ruido": ("RUI", "Ruido")}
    for cod, nombre, lat, lon in DISTRITOS:
        u = ubicacion(cod, f"Centro de control {nombre}", lat, lon)
        nuevo_sensor(f"OM-{cod:02d}", f"Clima - {nombre}", "meteorologico", u, date(2023, 12, 1))
        for tipo, (pref, etiqueta) in etiquetas.items():
            i = nuevo_sensor(f"{pref}-{cod:02d}", f"{etiqueta} - {nombre}", tipo, u,
                             fecha_random("2018-01-01", "2023-12-31"))
            generados[tipo].append(i)

    trafico = []
    for cod, _, _, _ in DISTRITOS:
        grupo = puntos[puntos["distrito"] == cod]
        if con_datos:
            grupo = grupo[grupo["id"].isin(con_datos)]
        elegidos = grupo.sample(n=min(10, len(grupo)), random_state=SEMILLA + cod)
        for _, p in elegidos.iterrows():
            u = ubicacion(cod, p["nombre"], p["latitud"], p["longitud"])
            i = nuevo_sensor(p["id"], f"Trafico - {p['nombre']}", "trafico", u,
                             fecha_random("2010-01-01", "2026-05-31"))
            trafico.append(i)

    sin_datos = puntos[~puntos["id"].isin(con_datos)] if con_datos else puntos.iloc[0:0]
    for _, p in sin_datos.sample(n=min(6, len(sin_datos)), random_state=SEMILLA).iterrows():
        u = ubicacion(int(p["distrito"]), p["nombre"], p["latitud"], p["longitud"])
        nuevo_sensor(p["id"], f"Trafico - {p['nombre']}", "trafico", u,
                     fecha_random("2010-01-01", "2026-05-31"), "mantenimiento")

    for i in rng.sample(trafico, 8):
        sensores[i][7] = "inactivo"
    for lista in generados.values():
        a, b = rng.sample(lista, 2)
        sensores[a][7] = "inactivo"
        sensores[b][7] = "mantenimiento"

    cur.executemany("""INSERT INTO sensor (id_sensor, codigo_origen, nombre, id_tipo, id_ubicacion,
                       id_organismo, fecha_instalacion, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    sensores)

    emt = organismos[ORG_EMT]
    lineas = ["1", "2", "3", "5", "9", "14", "15", "19", "21", "27", "34", "44", "53", "61", "74",
              "111", "146", "C1", "C2", "N1"]
    rutas = []
    for l in lineas:
        rutas.append(cur.execute(
            "INSERT INTO ruta (codigo, nombre, id_organismo) VALUES (%s, %s, %s) RETURNING id_ruta",
            (f"EMT-{l}", f"Linea {l}", emt)).fetchone()[0])

    paradas = []
    for cod, nombre, lat, lon in DISTRITOS:
        for k in range(1, 6):
            la, lo = cerca(lat, lon)
            u = ubicacion(cod, f"Parada {nombre} {k}", la, lo)
            paradas.append(cur.execute(
                "INSERT INTO estacion (nombre, tipo, id_ubicacion) VALUES (%s, 'parada_bus', %s) RETURNING id_estacion",
                (f"Parada {nombre} {k}", u)).fetchone()[0])
        la, lo = cerca(lat, lon)
        u = ubicacion(cod, f"Parking {nombre}", la, lo)
        cur.execute("INSERT INTO estacion (nombre, tipo, id_ubicacion) VALUES (%s, 'estacionamiento', %s)",
                    (f"Parking {nombre}", u))
        if cod % 3 == 0:
            la, lo = cerca(lat, lon)
            u = ubicacion(cod, f"Estacion Cercanias {nombre}", la, lo)
            cur.execute("INSERT INTO estacion (nombre, tipo, id_ubicacion) VALUES (%s, 'estacion_tren', %s)",
                        (f"Estacion Cercanias {nombre}", u))

    recorridos = []
    for r in rutas:
        for orden, p in enumerate(rng.sample(paradas, rng.randint(8, 15)), start=1):
            recorridos.append((r, p, orden))
    cur.executemany("INSERT INTO ruta_estacion (id_ruta, id_estacion, orden) VALUES (%s, %s, %s)", recorridos)

    letras = "BCDFGHJKLMNPRSTVWXYZ"
    placas = set()
    vehiculos = []
    for tipo, cantidad, cap in (("bus", 150, None), ("auto", 200, 5), ("moto", 80, 2), ("bicicleta", 70, 1)):
        for _ in range(cantidad):
            placa = f"{rng.randint(0, 9999):04d} {''.join(rng.choice(letras) for _ in range(3))}"
            while placa in placas:
                placa = f"{rng.randint(0, 9999):04d} {''.join(rng.choice(letras) for _ in range(3))}"
            placas.add(placa)
            ruta = rng.choice(rutas) if tipo == "bus" else None
            vehiculos.append((placa, tipo, cap or rng.choice([70, 80, 90, 100]), ruta))
    cur.executemany("INSERT INTO vehiculo (placa, tipo, capacidad, id_ruta) VALUES (%s, %s, %s, %s)", vehiculos)

    con.commit()

    for tabla in ["distrito", "ubicacion", "sensor", "variable", "organismo", "usuario", "ruta", "estacion", "vehiculo"]:
        print(f"{tabla}: {cur.execute(f'SELECT COUNT(*) FROM {tabla}').fetchone()[0]}")
    print(cur.execute("SELECT estado, COUNT(*) FROM sensor GROUP BY estado ORDER BY estado").fetchall())
    con.close()


if __name__ == "__main__":
    main()
