# Datos

## Fuentes (`data/raw/`)

| Carpeta | Qué es | Fuente |
| --- | --- | --- |
| `aire/` | Calidad del aire por hora (2024-2026) y estaciones | datos.madrid.es |
| `trafico/` | Tráfico cada 15 min (jun-ago 2026) y ubicación de los puntos | datos.madrid.es |
| `clima/` | Temperatura, humedad y lluvia por hora y distrito | Open-Meteo |
| `energia/` | Consumo eléctrico de una casa (para sacar el patrón por hora) | UCI |

Los archivos de tráfico originales pesan ~800 MB cada uno, así que en el repo solo quedan las filas de los 210 puntos que usamos. `ids_con_datos.txt` tiene la lista de todos los puntos que traían datos.

Lo que no hay en datos abiertos (organismos, usuarios, rutas, vehículos, energía, parking, ruido, incidentes) se genera con semilla 42, así siempre sale igual.

## Scripts (`data/generators/`), en este orden

1. `catalogo.py`: llena los catálogos de Postgres.
2. `clima.py`: descarga el clima (si ya está en `data/raw/clima` se lo salta).
3. `cargar_mongo.py`: carga los datos crudos a Mongo y saca alertas y eventos.
4. `cargar_postgres.py`: lee de Mongo, quita los inválidos, promedia por hora y llena `medicion`.

## Resultado

| Base | Tabla / colección | Registros |
| --- | --- | --- |
| PostgreSQL | sensor | 324 |
| PostgreSQL | medicion | 4.664.093 |
| MongoDB | lecturas | 3.151.581 |
| MongoDB | alertas | 49.448 |
| MongoDB | eventos | 8.936 |
| MongoDB | incidentes | 4.000 |
