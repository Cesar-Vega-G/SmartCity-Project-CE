from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"

INICIO = "2024-01-01"
FIN = "2026-08-31 23:59:59"
FECHA_BAJA = "2026-07-15"
SEMILLA = 42

DISTRITOS = [
    (1, "Centro", 40.4155, -3.7074),
    (2, "Arganzuela", 40.3980, -3.6990),
    (3, "Retiro", 40.4110, -3.6760),
    (4, "Salamanca", 40.4300, -3.6770),
    (5, "Chamartin", 40.4580, -3.6760),
    (6, "Tetuan", 40.4600, -3.6980),
    (7, "Chamberi", 40.4340, -3.7040),
    (8, "Fuencarral-El Pardo", 40.4900, -3.7000),
    (9, "Moncloa-Aravaca", 40.4400, -3.7400),
    (10, "Latina", 40.4030, -3.7440),
    (11, "Carabanchel", 40.3830, -3.7280),
    (12, "Usera", 40.3830, -3.7060),
    (13, "Puente de Vallecas", 40.3900, -3.6680),
    (14, "Moratalaz", 40.4070, -3.6450),
    (15, "Ciudad Lineal", 40.4480, -3.6500),
    (16, "Hortaleza", 40.4720, -3.6410),
    (17, "Villaverde", 40.3460, -3.7090),
    (18, "Villa de Vallecas", 40.3720, -3.6210),
    (19, "Vicalvaro", 40.4040, -3.6080),
    (20, "San Blas-Canillejas", 40.4300, -3.6100),
    (21, "Barajas", 40.4700, -3.5800),
]

ORG_AIRE = "Ayuntamiento de Madrid - Calidad del Aire"
ORG_MOV = "Ayuntamiento de Madrid - Movilidad"
ORG_EMT = "EMT Madrid"
ORG_ELEC = "Distribuidora Electrica Madrid"

ORGANISMOS = [
    (ORG_AIRE, "Direccion General de Sostenibilidad y Control Ambiental"),
    (ORG_MOV, "Direccion General de Gestion y Vigilancia de la Circulacion"),
    (ORG_EMT, "Direccion de Operaciones EMT"),
    (ORG_ELEC, "Centro de Control de Red"),
]

# tipo: (categoria, organismo)
TIPOS = {
    "calidad_aire": ("ambiente", ORG_AIRE),
    "meteorologico": ("ambiente", ORG_AIRE),
    "ruido": ("ambiente", ORG_AIRE),
    "trafico": ("movilidad", ORG_MOV),
    "estacionamiento": ("espacios_publicos", ORG_MOV),
    "medidor_energia": ("energia", ORG_ELEC),
}

# variable: (unidad, limite)
VARIABLES = {
    "no2": ("ug/m3", 200),
    "pm10": ("ug/m3", 50),
    "pm25": ("ug/m3", 25),
    "co": ("mg/m3", 10),
    "o3": ("ug/m3", 180),
    "temperatura": ("C", 35),
    "humedad": ("%", None),
    "precipitacion": ("mm", 20),
    "ruido_db": ("dB", 65),
    "intensidad": ("veh/h", None),
    "ocupacion": ("%", None),
    "carga": ("0-100", 80),
    "velocidad": ("km/h", None),
    "ocupacion_parking": ("%", 95),
    "consumo_kwh": ("kWh", 500),
}

# codigos de magnitud del ayuntamiento
MAGNITUDES = {6: "co", 8: "no2", 9: "pm25", 10: "pm10", 14: "o3"}


def leer_env():
    datos = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.split("=", 1)
                datos[k.strip()] = v.strip()
    return datos


def conectar_pg():
    import psycopg
    env = leer_env()
    return psycopg.connect(
        host="localhost",
        port=int(env.get("PG_PORT", "5433")),
        dbname=env.get("PG_DB", "smartcity"),
        user=env.get("PG_USER", "smartcity"),
        password=env.get("PG_PASSWORD", "smartcity123"),
    )


def conectar_mongo():
    from pymongo import MongoClient
    env = leer_env()
    usuario = env.get("MONGO_USER", "smartcity")
    clave = env.get("MONGO_PASSWORD", "smartcity123")
    cliente = MongoClient(f"mongodb://{usuario}:{clave}@localhost:27017/?authSource=admin")
    return cliente["smartcity"]
