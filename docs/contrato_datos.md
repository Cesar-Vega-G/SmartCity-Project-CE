# Contrato de datos - SmartCity San José

Reglas que todos seguimos para que los datos de PostgreSQL y MongoDB calcen entre sí.
Si algo de aquí se cambia, se avisa al grupo antes.

## 1. Reglas generales

- La ciudad es **San José, Costa Rica**. Las coordenadas son aproximadas.
- Nombres de zonas y distritos **sin tildes** (para no fallar al escribir consultas).
- Códigos y nombres de campos en minúscula y con guion bajo: `calidad_aire`, `id_sensor`.
- Fechas en hora local de Costa Rica. Período de datos: **2024-01-01 a 2026-09-30**.
- El sensor se identifica igual en las dos bases: `id_sensor` con formato `S-00001`.

## 2. Distritos y zonas

Cada distrito tiene 3 zonas: `<Distrito> Norte`, `<Distrito> Centro` y `<Distrito> Sur`.
Ejemplo: `Pavas Norte`, `Pavas Centro`, `Pavas Sur`.

| Distrito | Latitud centro | Longitud centro |
| --- | --- | --- |
| Carmen | 9.9370 | -84.0750 |
| Merced | 9.9370 | -84.0870 |
| Hospital | 9.9300 | -84.0890 |
| Catedral | 9.9280 | -84.0750 |
| Zapote | 9.9200 | -84.0580 |
| San Francisco de Dos Rios | 9.9100 | -84.0650 |
| Uruca | 9.9530 | -84.1070 |
| Mata Redonda | 9.9330 | -84.1000 |
| Pavas | 9.9450 | -84.1350 |
| Hatillo | 9.9150 | -84.1000 |
| San Sebastian | 9.9050 | -84.0830 |

Coordenadas de cada zona: Norte = latitud + 0.006, Centro = igual, Sur = latitud - 0.006.

## 3. Categorías, tipos de sensor y variables

| Categoría | Tipo de sensor | Variables que mide |
| --- | --- | --- |
| ambiente | calidad_aire | pm25, pm10, co2, no2 |
| ambiente | meteorologico | temperatura, humedad |
| ambiente | ruido | ruido_db |
| movilidad | trafico | vehiculos, velocidad_prom |
| espacios_publicos | estacionamiento | ocupacion |
| energia | medidor_energia | consumo_kwh |

| Variable | Unidad | Límite de alerta |
| --- | --- | --- |
| pm25 | ug/m3 | 35 |
| pm10 | ug/m3 | 50 |
| co2 | ppm | 1000 |
| no2 | ug/m3 | 200 |
| temperatura | C | 32 |
| humedad | % | - |
| ruido_db | dB | 70 |
| vehiculos | veh/h | 1200 |
| velocidad_prom | km/h | - |
| ocupacion | % | 95 |
| consumo_kwh | kWh | 500 |

Si un valor pasa el límite se genera un documento en la colección `alertas` de Mongo.

## 4. Organismos responsables

| Organismo | Responsable de |
| --- | --- |
| Municipalidad de San Jose | ruido, estacionamiento |
| MINAE | calidad_aire, meteorologico |
| MOPT | trafico, rutas de bus |
| CNFL | medidor_energia |

## 5. Qué va en cada base

**PostgreSQL** (tablas en `postgres/init/01_ddl.sql`)
- Catálogo: ciudad, distritos, ubicaciones (zonas), categorías, tipos, variables, organismos, usuarios, sensores, rutas, estaciones, vehículos.
- `medicion`: **promedio por hora** de cada sensor y variable (datos ya limpios).

**MongoDB** (base `smartcity`)
- `lecturas`: lo que manda cada sensor, crudo, cada 15 minutos.
- `eventos`: cosas detectadas (congestión, pico de contaminación, falla de sensor).
- `alertas`: cuando una variable pasa su límite.
- `incidentes`: reportes urbanos (accidentes, inundaciones, cortes eléctricos...).

## 6. Formato de los documentos en Mongo

### lecturas
```json
{
  "id_sensor": "S-00001",
  "tipo": "calidad_aire",
  "categoria": "ambiente",
  "ubicacion": {
    "distrito": "Carmen",
    "zona": "Carmen Norte",
    "geo": { "type": "Point", "coordinates": [-84.0750, 9.9430] }
  },
  "medicion": { "pm25": 18.6, "pm10": 25.1, "co2": 425, "no2": 12.3 },
  "timestamp": "2025-05-01T14:15:00"
}
```
`medicion` cambia según el tipo de sensor (ver tabla de la sección 3). `geo` va con **longitud primero** (así lo pide Mongo).

### eventos
```json
{
  "tipo_evento": "congestion",
  "severidad": "alta",
  "id_sensor": "S-00120",
  "ubicacion": { "distrito": "Pavas", "zona": "Pavas Centro" },
  "timestamp": "2025-05-01T07:30:00",
  "detalles": { "vehiculos": 1450, "velocidad_prom": 12.4 }
}
```
- `tipo_evento`: congestion, pico_contaminacion, ruido_excesivo, falla_sensor, pico_consumo
- `severidad`: baja, media, alta, critica

### alertas
```json
{
  "id_sensor": "S-00001",
  "variable": "pm25",
  "valor": 41.2,
  "limite": 35,
  "nivel": "advertencia",
  "ubicacion": { "distrito": "Carmen", "zona": "Carmen Norte" },
  "timestamp": "2025-05-01T14:15:00",
  "atendida": false
}
```
- `nivel`: advertencia (hasta 1.5 veces el límite), critica (más de 1.5 veces)

### incidentes
```json
{
  "categoria": "accidente_transito",
  "descripcion": "Choque entre dos vehiculos",
  "ubicacion": { "distrito": "Uruca", "zona": "Uruca Sur" },
  "fecha_reporte": "2025-05-01T18:40:00",
  "estado": "cerrado",
  "organismo": "MOPT",
  "datos_extra": { "vehiculos_involucrados": 2, "heridos": 0 }
}
```
- `categoria`: accidente_transito, inundacion, corte_electrico, arbol_caido, manifestacion
- `estado`: abierto, en_proceso, cerrado
- `datos_extra` cambia según la categoría (es lo que muestra la flexibilidad de Mongo).

## 7. Lo que los datos generados tienen que cumplir

Para que todas las consultas obligatorias tengan resultados:

- Sensores instalados en distintos años (2019 a 2026).
- Sensores en los 3 estados: activo, inactivo, mantenimiento.
- Alrededor de un 5% de sensores **sin ninguna medición**.
- Los sensores inactivos dejan de mandar datos en algún momento.
- Patrones realistas: más tráfico en horas pico (7-9 y 17-19), más contaminación cuando hay más tráfico, más consumo eléctrico de día.
- Algunos valores pasan el límite, para que existan alertas y eventos.
- Volumen mínimo: 100.000 filas en `medicion` y 500.000 documentos en Mongo.
