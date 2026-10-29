# Contrato de datos

Nombres y reglas que usamos todos para que Postgres y Mongo calcen. Si se cambia algo, avisar al grupo.

## Reglas

- Ciudad: Madrid. Zona = distrito (21).
- Nombres sin tildes y en minúscula con guion bajo: `Chamartin`, `calidad_aire`, `id_sensor`.
- Periodo previsto: 2024-01-01 a 2026-08-31, hora de Madrid. La ingesta actual de Mongo entrega fechas sin zona y PyMongo las almacena como UTC; las consultas respetan esos valores sin desplazarlos. Revisar esta discrepancia antes de hacer interpretaciones de hora local.
- `id_sensor` (`S-00001`) es el mismo en las dos bases. `codigo_origen` es el código original de Madrid.

Distritos: Centro, Arganzuela, Retiro, Salamanca, Chamartin, Tetuan, Chamberi, Fuencarral-El Pardo, Moncloa-Aravaca, Latina, Carabanchel, Usera, Puente de Vallecas, Moratalaz, Ciudad Lineal, Hortaleza, Villaverde, Villa de Vallecas, Vicalvaro, San Blas-Canillejas, Barajas.

## Sensores y variables

| Tipo de sensor | Variables | Límite de alerta |
| --- | --- | --- |
| calidad_aire | no2, pm10, pm25, co, o3 | 200, 50, 25, 10, 180 |
| meteorologico | temperatura, humedad, precipitacion | 35, -, 20 |
| ruido | ruido_db | 65 |
| trafico | intensidad, ocupacion, carga, velocidad | carga 80 |
| estacionamiento | ocupacion_parking | 95 |
| medidor_energia | consumo_kwh | 500 |

Estados de sensor: `activo`, `inactivo`, `mantenimiento`.

## Qué va en cada base

**PostgreSQL**: catálogos (distritos, sensores, rutas, etc.) y `medicion`, que es el promedio por hora de cada sensor y variable, solo con valores válidos.

**MongoDB** (base `smartcity`):

`lecturas`: el dato crudo, como llega (tráfico cada 15 min), con `valido: false` si viene malo.
```json
{ "id_sensor": "S-00012", "codigo_origen": "28079008", "tipo": "calidad_aire", "categoria": "ambiente",
  "ubicacion": { "distrito": "Salamanca", "nombre": "Escuelas Aguirre",
                 "geo": { "type": "Point", "coordinates": [-3.6823, 40.4215] } },
  "medicion": { "no2": 41, "pm10": 22 }, "valido": true, "timestamp": "2025-05-01T14:00:00" }
```

`alertas`: cuando un valor pasa su límite (`nivel`: advertencia o critica si pasa 1.5 veces).
```json
{ "id_sensor": "S-00012", "variable": "no2", "valor": 215, "limite": 200, "nivel": "advertencia",
  "ubicacion": { "distrito": "Salamanca" }, "timestamp": "2025-01-15T09:00:00", "atendida": false }
```

`eventos`: `tipo_evento` congestion, pico_contaminacion, ruido_excesivo, falla_sensor, pico_consumo.
```json
{ "tipo_evento": "congestion", "severidad": "alta", "id_sensor": "S-00350",
  "ubicacion": { "distrito": "Chamartin" }, "timestamp": "2025-05-01T08:15:00", "detalles": { "carga": 92 } }
```

`incidentes`: `datos_extra` cambia según la categoría.
```json
{ "categoria": "accidente_transito", "descripcion": "Choque en la M-30", "ubicacion": { "distrito": "Arganzuela" },
  "fecha_reporte": "2025-05-01T18:40:00", "estado": "cerrado", "organismo": "Ayuntamiento de Madrid - Movilidad",
  "datos_extra": { "vehiculos_involucrados": 2, "heridos": 0 } }
```
