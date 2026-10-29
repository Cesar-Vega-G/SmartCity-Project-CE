# MongoDB con Compass — Persona D

Este es el punto de entrada para las consultas del Sprint 1. Hay una sola version
editable de cada consulta: los quince archivos de `compass/`.

## Preparar y conectar

La instalacion y carga inicial siguen el [README del proyecto](../../README.md).
Docker ejecuta el servidor y los cargadores Python preparan los datos. Una vez
cargados, para consultar solo se necesita Compass y el servicio MongoDB encendido.
Compass es el cliente; instalarlo no instala ni llena el servidor.

1. Abrir Compass y crear una conexion a `localhost:27017`.
2. En Authentication usar usuario y contraseña de `.env` (`MONGO_USER`,
   `MONGO_PASSWORD`), con Authentication Database `admin`. No guardar claves en Git.
3. Conectar y abrir `smartcity`. Deben aparecer `lecturas`, `eventos`, `alertas`
   e `incidentes`. Si no aparecen, revisar la carga inicial antes de consultar.
4. Despues de la carga inicial, abrir **Open MongoDB Shell** y pegar completo
   [indices.js](../rendimiento/indices.js). Es idempotente si los indices ya coinciden.
   Repetir este paso tras recargar: el cargador recrea las colecciones y borra sus indices.
5. En Documents inspeccionar documentos; en Indexes revisar los indices existentes.

## Ejecutar una consulta

1. Elegir la coleccion de la tabla siguiente y abrir **Aggregations**.
2. Seleccionar **Create New**, luego **TEXT**.
3. Abrir el archivo `.pipeline.js` y copiar todo su contenido en el editor.
   Es un arreglo de etapas: no agregar `db.lecturas.aggregate(...)`.
4. Pulsar **Run**. Preview muestra una muestra; Run ejecuta sobre el conjunto filtrado.
5. Volver a Edit y usar **Save** para ponerle nombre. Reabrir desde **My Queries**
   o **Saved Pipelines**. STAGES permite estudiar cada etapa por separado.

Cada integrante debe pegar y guardar las consultas en su propio Compass una vez.
Clonar el repositorio o levantar Docker no las instala automaticamente en Compass.
Guardar una consulta tampoco guarda sus resultados ni modifica documentos.
Si editas el pipeline en Compass, copia el texto de vuelta al archivo del repositorio
para compartir el cambio; no existe sincronizacion automatica.

## Archivo y coleccion


| Consulta | Coleccion | Archivo |
|---|---|---|
| 01. Lecturas de sensor | lecturas | [01](compass/01_lecturas_sensor.pipeline.js) |
| 02. Rango de fechas | lecturas | [02](compass/02_lecturas_fechas.pipeline.js) |
| 03. Maximos y minimos | lecturas | [03](compass/03_extremos.pipeline.js) |
| 04. Eventos criticos | eventos | [04](compass/04_eventos_criticos.pipeline.js) |
| 05. Alertas por zona | alertas | [05](compass/05_alertas_zona.pipeline.js) |
| 06. Promedios por zona | lecturas | [06](compass/06_promedio_zona.pipeline.js) |
| 07. Promedios por tipo | lecturas | [07](compass/07_promedio_tipo.pipeline.js) |
| 08. Incidentes por categoria | incidentes | [08](compass/08_incidentes_categoria.pipeline.js) |
| 09. Cantidad por sensor | lecturas | [09](compass/09_lecturas_por_sensor.pipeline.js) |
| 10. Filtros multiples | lecturas | [10](compass/10_filtros_multiples.pipeline.js) |
| 11. Temperatura por zona | lecturas | [11](compass/11_temperatura_zona.pipeline.js) |
| 12. Sensores sobre limites | alertas | [12](compass/12_sensores_sobre_limite.pipeline.js) |
| 13. Ranking de contaminacion | lecturas | [13](compass/13_ranking_contaminacion.pipeline.js) |
| 14. Evolucion diaria | lecturas | [14](compass/14_evolucion_diaria.pipeline.js) |
| 15. Incidentes con heridos | incidentes | [15](compass/15_incidentes_heridos.pipeline.js) |

Las fechas son julio de 2026, con inicio incluido y fin excluido. Para cambiarlas,
editar los dos `ISODate` de la primera etapa. La 01 contiene un sensor concreto
existente al generar el archivo: se puede cambiar su `id_sensor` directamente.
Los filtros y unidades estan desplegados en el propio pipeline; no hay parametros ocultos.
Si cambias de variable, actualiza todas sus apariciones y el tipo de sensor cuando corresponda.


## CRUD en Compass

Las agregaciones anteriores son de lectura. Para demostrar las siete operaciones
exigidas, abrir **Open MongoDB Shell** dentro de Compass, pegar todo [crud.js](crud.js)
y pulsar Enter. No se pega en Aggregations. No requiere Python, una terminal externa
ni cargar bibliotecas. Si la shell esta deshabilitada, habilitar Enable MongoDB Shell
en Settings; no funciona en modo de solo lectura.

El archivo ejecuta `insertOne`, `insertMany`, `find`, `findOne`, `updateOne`,
`updateMany` y `deleteOne`, imprime una comprobacion por operacion y elimina su base
temporal incluso si falla. Se puede repetir. Usa una base nueva `smartcity_demo_<id>`;
no modifica `smartcity`. La cuenta debe poder crear y eliminar esa base temporal.
El resultado esperado es siete lineas OK, confirmacion de limpieza y `aprobado: true`.

## Calidad, unidades y significado


- Zona significa distrito, no coordenada ni estacion individual.
- Las consultas de detalle conservan `valido` e `invalidos`.
- Las estadisticas aceptan valores numericos de campos conocidos que no aparezcan
  en `invalidos`. Si `valido:false` carece de una lista no vacia de variables invalidas,
  se excluye el documento de las estadisticas. Una variable sana puede contribuir
  aunque otra variable del documento sea invalida.
- Campos ausentes, nulos o de texto no representan cero. No se imputan faltantes.
- Cada valor valido pesa igual. No se iguala artificialmente la cobertura de sensores
  o dias. La cantidad de muestras acompana al promedio; no se redondea antes de agrupar.
- `no2`, `pm10`, `pm25`, `o3`: ug/m3; `co`: mg/m3; temperatura: C; humedad, ocupacion
  y parking: %; lluvia: mm; ruido: dB; intensidad: veh/h; carga: escala 0-100;
  velocidad: km/h; consumo: kWh. Se conserva la definicion del equipo en `comun.py`.
- La 9 cuenta documentos; una lectura con tres variables cuenta como uno.
- La 12 cuenta alertas generadas por la carga, no eventos deduplicados por dia.
  Los limites son criterios del proyecto, no una afirmacion normativa o sanitaria.
- La 13 clasifica concentracion media del contaminante seleccionado; no es un indice
  integral de calidad del aire ni prueba causal de riesgo.
- `eventos.severidad=critica` y `alertas.nivel=critica` son campos de entidades distintas.

### Fechas: limitacion heredada

El contrato menciona hora de Madrid, pero `cargar_mongo.py` entrega fechas sin zona
explicita y PyMongo las interpreta como UTC. Estas consultas preservan los valores
almacenados: limites con `Z` y agrupacion diaria en UTC, sin sumar/restar horas.
No se afirma que esto represente correctamente el horario de verano de Madrid.
Corregir la zona en la ingesta requeriria coordinacion y recarga fuera de Persona D.
[Referencia oficial](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/data-formats/dates-and-times/).


## Cobertura del cronograma y del enunciado

| Requisito | Entrega |
|---|---|
| Siete operaciones CRUD | [crud.js](crud.js), shell integrada de Compass |
| Diez consultas obligatorias | Pipelines 01–10 |
| Aggregation Framework | Todos los pipelines; especialmente 06–10 |
| Campos variables y documentos anidados | 03, 06, 07, 14: `$objectToArray`, `$unwind`; 15: `datos_extra.heridos` |
| Filtros, comparaciones y logica | 02, 10, 12, 15; `$gt`, `$gte`, `$lt`, `$in`, `$exists`, `$expr`, `$and`, `$or`, `$not` |
| Proyeccion, orden y grupos | `$project`, `$sort`, `$group` en los archivos |
| Preguntas complementarias | Temperatura 11; limites 12; cantidad 09; contaminacion 13; evolucion 14 |
| Volumen, resultados e indices | [Verificacion y estado actual](VERIFICACION.md) |
| Documento tecnico y defensa | [Seccion D](SECCION_PERSONA_D.md), [guion](DEFENSA.md) |

## Estructura y mantenimiento

- `compass/`: los quince pipelines comentados; unica version editable de cada consulta.
- `crud.js`: demostracion de las siete operaciones en la shell integrada.
- `VERIFICACION.md`: resultados de la revision actual, comprobaciones y pendientes.
- `SECCION_PERSONA_D.md`: modelo documental y justificacion para el documento del equipo.
- `DEFENSA.md`: orden sugerido para demostrar y explicar el trabajo.

Si modificas una consulta, copia el cambio al archivo y repite las comprobaciones.
El dataset de entrada y los cargadores son necesarios para reproducir el proyecto.
Los informes antiguos y los archivos auxiliares de versiones anteriores no forman parte
de esta entrega. La medicion de indices se resume en [rendimiento Mongo](../../docs/rendimiento_mongo.md).

Referencias oficiales: [Aggregations](https://www.mongodb.com/docs/compass/create-agg-pipeline/)
y [shell integrada](https://www.mongodb.com/docs/compass/embedded-shell/).
