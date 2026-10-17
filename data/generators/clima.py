import csv
import json
import time
import urllib.request

from comun import RAW, DISTRITOS

URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
       "&start_date=2024-01-01&end_date=2026-08-31"
       "&hourly=temperature_2m,relative_humidity_2m,precipitation&timezone=Europe%2FMadrid")


def main():
    carpeta = RAW / "clima"
    carpeta.mkdir(parents=True, exist_ok=True)

    for cod, nombre, lat, lon in DISTRITOS:
        destino = carpeta / f"clima_{cod:02d}.csv"
        if destino.exists():
            print(f"{nombre}: ya existe, se salta")
            continue

        with urllib.request.urlopen(URL.format(lat=lat, lon=lon), timeout=120) as r:
            datos = json.loads(r.read())["hourly"]

        with open(destino, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fecha", "temperatura", "humedad", "precipitacion"])
            for fila in zip(datos["time"], datos["temperature_2m"],
                            datos["relative_humidity_2m"], datos["precipitation"]):
                w.writerow(fila)

        print(f"{nombre}: {len(datos['time'])} horas")
        time.sleep(1)


if __name__ == "__main__":
    main()
