# Generación y carga de datos

## 1. Datos reales descargados (`data/raw/`, no se suben a GitHub)

| Carpeta | Archivo | Fuente |
| --- | --- | --- |
| `aire/` | Calidad del aire, datos horarios 2024 (ZIP) y desde 2025 (CSV) | datos.madrid.es, dataset 201200 |
| `aire/` | Calidad del aire, estaciones de control (CSV) | datos.madrid.es, dataset 212629 |
| `trafico/` | Tráfico, histórico de puntos de medida: 06, 07 y 08 de 2026 | datos.madrid.es, dataset 208627 |
| `trafico/` | Tráfico, ubicación de los puntos de medida (CSV) | datos.madrid.es, dataset 202468 |
| `energia/` | Individual Household Electric Power Consumption | UCI Machine Learning Repository |
| `clima/` | Temperatura, humedad y precipitación por hora y distrito | Open-Meteo (ERA5), lo descarga `clima.py` |

Licencia de los datos de Madrid: datos abiertos del Ayuntamiento de Madrid (reutilización libre citando la fuente).

## 2. Scripts (`data/generators/`) y orden

| # | Script | Qué hace |
| --- | --- | --- |
| 1 | `catalogo.py` | Llena las tablas de catálogo de PostgreSQL |
| 2 | `clima.py` | Descarga el clima de Open-Meteo a `data/raw/clima/` |
| 3 | `cargar_mongo.py` | Carga los datos crudos a MongoDB y calcula alertas y eventos |
| 4 | `cargar_postgres.py` | Lee de MongoDB, limpia, promedia por hora y carga `medicion` |

## 3. Qué es real y qué es generado

**Real**
- 24 estaciones de calidad del aire con su ubicación, tipo y fecha de alta.
- Valores horarios de NO2, PM10, PM2.5, CO y O3 (2024-01 a 2026-08), con su marca de validez `V`/`N`.
- 210 puntos de medida de tráfico (10 por distrito, elegidos al azar con semilla fija) con su lectura cada 15 minutos (junio-agosto 2026).
- Clima por hora para el centro de cada distrito (reanálisis ERA5).

**Generado** (semilla fija `42`, así siempre sale lo mismo)
- Organismos, usuarios, rutas EMT, paradas, vehículos.
- Fechas de instalación de los sensores que no son estaciones de aire.
- Estados de los sensores: 8 puntos de tráfico y 1 sensor de cada tipo generado quedan `inactivo` (dejan de mandar datos el 2026-07-15); 1 de cada tipo generado y 6 puntos de tráfico reales sin datos quedan en `mantenimiento` (sin ninguna medición).
- Medidores de energía (1 por distrito, 2025-01 a 2026-08): consumo = base del distrito × patrón semana/hora sacado del dataset UCI × factor de estación del año × ruido aleatorio.
- Ocupación de parking y ruido (1 por distrito, 2026-06 a 2026-08): curva diaria con pico a mediodía + ruido aleatorio.
- 4000 incidentes urbanos con categoría, distrito, fecha y datos extra según la categoría.

## 4. Alertas y eventos

- **Alerta:** cada valor válido que pasa el límite de su variable (ver contrato). Nivel `critica` si pasa 1.5 veces el límite.
- **Evento** (máximo uno por sensor, día y tipo): `congestion` (carga > 80), `pico_contaminacion` (aire > 1.5 veces el límite), `ruido_excesivo` (> 75 dB), `pico_consumo` (> 500 kWh), `falla_sensor` (lectura con valores inválidos).

## 5. Limpieza de MongoDB a PostgreSQL

`cargar_postgres.py` usa un pipeline de agregación de MongoDB por tipo de sensor:
1. Trunca el `timestamp` a la hora (`$dateTrunc`).
2. Separa cada variable de `medicion` (`$objectToArray` + `$unwind`).
3. Descarta las variables marcadas en `invalidos` y los valores que no son números.
4. Promedia por sensor, hora y variable (`$group` + `$avg`).
5. Inserta el resultado en `medicion` con `COPY`.

## 6. Volúmenes aproximados

| Base | Colección / tabla | Registros aprox. |
| --- | --- | --- |
| MongoDB | lecturas | 3,2 millones |
| MongoDB | alertas, eventos, incidentes | decenas de miles |
| PostgreSQL | medicion | 4 a 5 millones |
