# Contrato de datos - SmartCity Madrid

Reglas que todos seguimos para que los datos de PostgreSQL y MongoDB calcen entre sí.
Si algo de aquí se cambia, se avisa al grupo antes.

## 1. Reglas generales

- La ciudad es **Madrid, España**. Se usan datos abiertos reales del Ayuntamiento de Madrid.
- **Zona = distrito.** Cuando una consulta dice "por zona", se agrupa por distrito (son 21).
- Nombres sin tildes (para no fallar al escribir consultas): `Chamartin`, `Tetuan`, `Chamberi`...
- Códigos y nombres de campos en minúscula y con guion bajo: `calidad_aire`, `id_sensor`.
- Fechas en hora local de Madrid. Período de datos: **2024-01-01 a 2026-08-31**.
- Cada sensor tiene dos códigos:
  - `id_sensor`: el nuestro, formato `S-00001`. Es el que se usa para cruzar Postgres y Mongo.
  - `codigo_origen`: el código que trae el dato abierto de Madrid (ej: estación `28079008`, punto de tráfico `3409`).

## 2. Distritos

| Código | Distrito | Latitud | Longitud |
| --- | --- | --- | --- |
| 1 | Centro | 40.4155 | -3.7074 |
| 2 | Arganzuela | 40.3980 | -3.6990 |
| 3 | Retiro | 40.4110 | -3.6760 |
| 4 | Salamanca | 40.4300 | -3.6770 |
| 5 | Chamartin | 40.4580 | -3.6760 |
| 6 | Tetuan | 40.4600 | -3.6980 |
| 7 | Chamberi | 40.4340 | -3.7040 |
| 8 | Fuencarral-El Pardo | 40.4900 | -3.7000 |
| 9 | Moncloa-Aravaca | 40.4400 | -3.7400 |
| 10 | Latina | 40.4030 | -3.7440 |
| 11 | Carabanchel | 40.3830 | -3.7280 |
| 12 | Usera | 40.3830 | -3.7060 |
| 13 | Puente de Vallecas | 40.3900 | -3.6680 |
| 14 | Moratalaz | 40.4070 | -3.6450 |
| 15 | Ciudad Lineal | 40.4480 | -3.6500 |
| 16 | Hortaleza | 40.4720 | -3.6410 |
| 17 | Villaverde | 40.3460 | -3.7090 |
| 18 | Villa de Vallecas | 40.3720 | -3.6210 |
| 19 | Vicalvaro | 40.4040 | -3.6080 |
| 20 | San Blas-Canillejas | 40.4300 | -3.6100 |
| 21 | Barajas | 40.4700 | -3.5800 |

Coordenadas aproximadas del centro de cada distrito. Los sensores reales usan sus propias coordenadas.
El código es el mismo número de distrito que usan los archivos de tráfico de Madrid.

## 3. Fuentes de datos

| Tipo de sensor | Fuente | ¿Real? |
| --- | --- | --- |
| calidad_aire | Ayuntamiento de Madrid: Calidad del aire, datos horarios + estaciones de control | Real |
| trafico | Ayuntamiento de Madrid: Tráfico, histórico de puntos de medida (cada 15 min) + ubicación de los puntos | Real |
| meteorologico | Open-Meteo (reanálisis ERA5), una estación virtual por distrito | Real (modelo) |
| medidor_energia | Generado con el patrón horario del dataset UCI Individual Household Electric Power Consumption | Sintético con patrón real |
| estacionamiento | Generado | Sintético |
| ruido | Generado | Sintético |

También son generados: organismos, usuarios, rutas, estaciones, vehículos, fechas de instalación, estados de los sensores, eventos e incidentes.
El mecanismo de generación se documenta en `docs/generacion_datos.md`.

## 4. Categorías, tipos de sensor y variables

| Categoría | Tipo de sensor | Variables |
| --- | --- | --- |
| ambiente | calidad_aire | no2, pm10, pm25, co, o3 (según lo que mida cada estación) |
| ambiente | meteorologico | temperatura, humedad, precipitacion |
| ambiente | ruido | ruido_db |
| movilidad | trafico | intensidad, ocupacion, carga, velocidad |
| espacios_publicos | estacionamiento | ocupacion_parking |
| energia | medidor_energia | consumo_kwh |

| Variable | Unidad | Límite de alerta | Código magnitud Madrid |
| --- | --- | --- | --- |
| no2 | ug/m3 | 200 | 8 |
| pm10 | ug/m3 | 50 | 10 |
| pm25 | ug/m3 | 25 | 9 |
| co | mg/m3 | 10 | 6 |
| o3 | ug/m3 | 180 | 14 |
| temperatura | C | 35 | - |
| humedad | % | - | - |
| precipitacion | mm | 20 | - |
| ruido_db | dB | 65 | - |
| intensidad | veh/h | - | - |
| ocupacion | % | - | - |
| carga | 0-100 | 80 | - |
| velocidad | km/h | - | - |
| ocupacion_parking | % | 95 | - |
| consumo_kwh | kWh | 500 | - |

`carga` es el indicador de congestión de Madrid: 0 = vía vacía, 100 = colapso. Si pasa de 80 se considera congestión.
Si un valor pasa su límite se genera un documento en la colección `alertas` de Mongo.

## 5. Organismos responsables

| Organismo | Responsable de |
| --- | --- |
| Ayuntamiento de Madrid - Calidad del Aire | calidad_aire, meteorologico, ruido |
| Ayuntamiento de Madrid - Movilidad | trafico, estacionamiento |
| EMT Madrid | rutas de bus, estaciones y vehiculos |
| Distribuidora Electrica Madrid | medidor_energia |

## 6. Qué va en cada base

**PostgreSQL** (tablas en `postgres/init/01_ddl.sql`)
- Catálogo: ciudad, distritos, ubicaciones, categorías, tipos, variables, organismos, usuarios, sensores, rutas, estaciones, vehículos.
- `medicion`: **promedio por hora** de cada sensor y variable, **solo con datos válidos** (datos limpios).

**MongoDB** (base `smartcity`)
- `lecturas`: el dato crudo, con la frecuencia original (tráfico cada 15 min, aire y clima cada hora), **incluyendo los inválidos** marcados con `valido: false`.
- `eventos`: cosas detectadas (congestión, pico de contaminación, falla de sensor).
- `alertas`: cuando una variable pasa su límite.
- `incidentes`: reportes urbanos (accidentes, inundaciones, cortes eléctricos...).

## 7. Limpieza (de Mongo a Postgres)

- Calidad del aire: Madrid marca cada valor horario con `V` (válido) o `N` (no válido). A Postgres solo pasan los `V`.
- Tráfico: los valores negativos significan "sin dato" y `error = S` significa dato erróneo. Esos no pasan a Postgres. Los 4 valores de 15 min se promedian por hora.
- Clima, energía, parking y ruido: se promedian por hora.

## 8. Formato de los documentos en Mongo

### lecturas
```json
{
  "id_sensor": "S-00012",
  "codigo_origen": "28079008",
  "tipo": "calidad_aire",
  "categoria": "ambiente",
  "ubicacion": {
    "distrito": "Salamanca",
    "nombre": "Escuelas Aguirre",
    "geo": { "type": "Point", "coordinates": [-3.6823, 40.4215] }
  },
  "medicion": { "no2": 41, "pm10": 22, "pm25": 11 },
  "valido": true,
  "timestamp": "2025-05-01T14:00:00"
}
```
- `medicion` cambia según el tipo de sensor (ver sección 4). Por ejemplo, tráfico trae `intensidad`, `ocupacion`, `carga` y `velocidad`.
- `geo` va con **longitud primero** (así lo pide Mongo).

### eventos
```json
{
  "tipo_evento": "congestion",
  "severidad": "alta",
  "id_sensor": "S-00350",
  "ubicacion": { "distrito": "Chamartin" },
  "timestamp": "2025-05-01T08:15:00",
  "detalles": { "carga": 92, "intensidad": 1840 }
}
```
- `tipo_evento`: congestion, pico_contaminacion, ruido_excesivo, falla_sensor, pico_consumo
- `severidad`: baja, media, alta, critica

### alertas
```json
{
  "id_sensor": "S-00012",
  "variable": "no2",
  "valor": 215,
  "limite": 200,
  "nivel": "advertencia",
  "ubicacion": { "distrito": "Salamanca" },
  "timestamp": "2025-01-15T09:00:00",
  "atendida": false
}
```
- `nivel`: advertencia (hasta 1.5 veces el límite), critica (más de 1.5 veces)

### incidentes
```json
{
  "categoria": "accidente_transito",
  "descripcion": "Choque entre dos vehiculos en la M-30",
  "ubicacion": { "distrito": "Arganzuela" },
  "fecha_reporte": "2025-05-01T18:40:00",
  "estado": "cerrado",
  "organismo": "Ayuntamiento de Madrid - Movilidad",
  "datos_extra": { "vehiculos_involucrados": 2, "heridos": 0 }
}
```
- `categoria`: accidente_transito, inundacion, corte_electrico, arbol_caido, manifestacion
- `estado`: abierto, en_proceso, cerrado
- `datos_extra` cambia según la categoría (es lo que muestra la flexibilidad de Mongo).

## 9. Lo que los datos tienen que cumplir

Para que todas las consultas obligatorias tengan resultados:

- Sensores instalados en distintos años (las estaciones de aire traen su fecha real de alta; el resto se genera entre 2010 y 2026).
- Sensores en los 3 estados: activo, inactivo, mantenimiento.
- Algunos sensores **sin ninguna medición** (los datos reales ya traen puntos de tráfico sin datos).
- Los sensores inactivos dejan de mandar datos en algún momento.
- Algunos valores pasan el límite, para que existan alertas y eventos.
- Volumen mínimo: 100.000 filas en `medicion` y 500.000 documentos en Mongo.
