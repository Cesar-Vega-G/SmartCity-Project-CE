# Verificacion y estado actual de MongoDB

Revision: **28 de octubre de 2026**, MongoDB **7.0.45**, carga local del proyecto.
Se ejecutaron los archivos actuales, incluidos sus comentarios, mediante mongosh
contra Docker. Esto comprueba las consultas del motor, no es una nueva prueba manual
de cada pantalla de Compass ni una instalacion desde cero.

## Resultado

- **15/15 pipelines ejecutados**, con las cantidades de filas esperadas.
- **22 comprobaciones aprobadas**: conteos, ejemplos, rango vacio, sensor inexistente,
  volumen y hashes documentales antes/despues.
- **CRUD aprobado dos veces**: siete operaciones y limpieza por ejecucion.
- **Script de indices comprobado dos veces**, sin cambios en el inventario existente.
- **Datos del proyecto intactos**, comprobado con dbHash de las cuatro colecciones.
- El conteo agrupado por sensor coincide con el conteo directo de documentos de julio.
- Ejemplos comprobados: Arganzuela, temperatura 29,3571 C y 744 muestras;
  Carabanchel, NO2 24,9436 ug/m3 y 1.471 muestras.

Son comprobaciones de ejecucion y resultados seleccionados, no una prueba exhaustiva
de todos los posibles datos de entrada. Al modificar consultas o datos, repetir la
verificacion y actualizar este resumen; no acumular versiones de informes.

## Volumen y consultas

| Coleccion | Documentos |
|---|---:|
| lecturas | 3,151,581 |
| eventos | 8,936 |
| alertas | 49,448 |
| incidentes | 4,000 |

Total: **3.213.965**; supera el minimo de 500.000.

| Pipeline | Coleccion | Filas |
|---|---|---:|
| 01 | lecturas | 100 |
| 02 | lecturas | 100 |
| 03 | lecturas | 15 |
| 04 | eventos | 90 |
| 05 | alertas | 32 |
| 06 | lecturas | 246 |
| 07 | lecturas | 15 |
| 08 | incidentes | 7 |
| 09 | lecturas | 312 |
| 10 | lecturas | 100 |
| 11 | lecturas | 21 |
| 12 | alertas | 136 |
| 13 | lecturas | 16 |
| 14 | lecturas | 651 |
| 15 | incidentes | 20 |

Los detalles se limitan a 100 filas; las estadisticas procesan todos los valores
filtrados. Cien filas de detalle no representan el total de coincidencias.

## Indices observados

| Acceso explicado | Indice | Documentos examinados |
|---|---|---:|
| 1 | idx_sensor_timestamp | 744 |
| 13 | idx_tipo_timestamp | 17112 |
| Alertas criticas en Centro | idx_nivel_distrito | 0 |

El filtro de alertas criticas de julio en Centro no examino documentos: no usar ese
resultado vacio para atribuir una mejora de velocidad. Los indices existentes son:
lecturas (sensor/fecha, tipo/fecha, geo), alertas (nivel/distrito, sensor/fecha), eventos
(tipo_evento/fecha), incidentes (categoria/fecha_reporte), ademas de _id en cada una.
La [tabla de rendimiento](../../docs/rendimiento_mongo.md) resume la comparacion del
equipo con y sin indices; es un experimento separado de esta revision funcional.

## Repetir desde Compass

1. Contar exactamente con `[{ $count: "documentos" }]` en Aggregations de cada
   coleccion. Una coleccion vacia devuelve `[]`.
2. Pegar los quince pipelines en las colecciones de la [guia](README.md), pulsar Run
   y contrastar filas y muestras. Preview no representa el resultado completo.
3. En una copia de la 01 poner un sensor inexistente; en una copia de la 02 igualar
   inicio y fin. Ambas deben devolver `[]`. Restaurar los archivos originales.
4. Pegar crud.js completo en Open MongoDB Shell dos veces: siete OK, limpieza y aprobado true.
5. Usar Explain en 01 y 13 y registrar indice y documentos examinados. Para el tercer
   acceso, usar el pipeline siguiente en alertas. No ejecutar el benchmark en el uso
   diario: elimina y recrea indices para comparar rendimiento.
6. Registrar fecha, version (`db.version()` en la shell), filtros, filas y muestras.
   Para verificar integridad, comparar antes/despues el campo collections de
   `db.getSiblingDB("smartcity").runCommand({dbHash:1})` en la shell, sin cargas o
   escrituras concurrentes. Esto requiere permisos administrativos.

```javascript
[
  { $match: { nivel: "critica", "ubicacion.distrito": "Centro",
      timestamp: { $gte: ISODate("2026-07-01T00:00:00Z"),
                   $lt: ISODate("2026-08-01T00:00:00Z") } } },
  { $count: "alertas" }
]
```

## Cumplimiento y pendientes

| Alcance | Estado |
|---|---|
| Cuatro colecciones y campos dinamicos | Implementado |
| Siete operaciones CRUD | Implementadas y verificadas |
| Diez consultas obligatorias | Implementadas y ejecutadas |
| Preguntas complementarias | Implementadas y ejecutadas |
| Aggregation Framework, filtros, operadores, proyeccion, orden y grupos | Pipelines 01–15 |
| Minimo 500.000 documentos | Verificado |
| Indices y comparacion de rendimiento | Scripts, Explain y tabla disponibles |
| Modelo documental, decisiones y diagrama | SECCION_PERSONA_D.md; integrar al documento grupal |
| Defensa en vivo | Guion preparado; ensayo y presentacion pendientes del equipo |
| Instalacion y carga completa desde cero en otra computadora | Pendiente de comprobar en grupo |
| Revision de otro integrante y PR a main | Pendientes; PR pospuesto por el usuario |
| Documento tecnico final y matriz comparativa entre tecnologias | Integracion grupal pendiente de verificar |
| Hadoop/HDFS, Spark y aplicacion integrada final | Fuera del alcance de Sprint 1; no implementados en este repositorio |

La parte funcional de Persona D esta cubierta. No equivale a declarar terminado el
enunciado completo ni la entrega grupal. PostgreSQL tiene su propia implementacion y
validacion; esta revision no vuelve a certificar su funcionamiento.

## Mejoras pendientes

- **Tiempo:** la ingesta de Mongo almacena fechas sin conversion explicita de zona,
  aunque el contrato pretende hora de Madrid. Las consultas respetan UTC almacenado.
  Coordinar la correccion de ingesta antes de interpretar horas locales.
- **Reproduccion:** ensayar instalacion completa, fuentes y licencias en el documento
  final. El cargador recrea colecciones; los indices se crean despues.
- **Distribucion e integracion:** un servicio Mongo no demuestra sharding, replicacion
  ni procesamiento distribuido. Compass sirve para explorar y defender Mongo; no
  sustituye la aplicacion integrada que exige el proyecto final.
