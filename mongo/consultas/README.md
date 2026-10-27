# MongoDB - Persona D, Sprint 1

CRUD, diez consultas obligatorias y cinco ejemplos complementarios para MongoDB 7.
Se conserva el modelo de Madrid del contrato del equipo. Rama de trabajo: `MDB/consultas`.

## Inicio rapido

Requiere Docker Desktop con el contenedor `smartcity_mongo` y la carga de Cesar.
El ejecutor solo necesita Python 3; usa el `mongosh` que ya incluye el contenedor.
Desde la raiz del repositorio:

```powershell
python mongo/consultas/ejecutar.py comprobar --salida mongo/consultas/evidencia_inventario_nueva
python mongo/consultas/ejecutar.py controladas --salida mongo/consultas/evidencia_controladas_nueva
python mongo/consultas/ejecutar.py completa --salida mongo/consultas/evidencia_completa_nueva
```

Cada salida debe ser una carpeta nueva. Codigo de salida 0 significa aprobado;
1 significa fallo o error. `validacion.json` contiene version, parametros, muestras,
comprobaciones y, para la prueba completa, planes e integridad. No exporta el dataset.
`todo` combina controladas y completa. `consultas` ejecuta las quince lecturas sin
oraculo ni comprobacion de integridad; `crud` ejecuta solo la demostracion aislada.
El modo `comprobar` es un inventario: consultar `volumen_minimo_cumplido`, no confundir
conexion exitosa con cumplimiento integral. Se puede cambiar `--contenedor` y `--base`.

La validacion completa recorre los datos del periodo para calcular referencias
independientes; puede tardar varios minutos. Ejecutarla sin cargas o escrituras
concurrentes. No crea indices, no recarga datos y no modifica las cuatro colecciones.

Las credenciales se leen dentro del contenedor de su entorno existente. No se
imprimen ni se incluyen en la evidencia. El ejecutor copia solo JavaScript a una
carpeta temporal unica y la limpia al terminar. No requiere `.env` en el anfitrion.

## Ejecutar archivos individuales en mongosh

Con `mongosh` instalado localmente, abrirlo desde la raiz del repositorio y
autenticarse con el usuario configurado en `.env`; `--password` solicita la clave:

```powershell
mongosh "mongodb://localhost:27017/smartcity?authSource=admin" --username smartcity --password
```

En la sesion:

```javascript
load("mongo/consultas/00_comprobar.js");
load("mongo/consultas/01_lecturas_sensor.js");
load("mongo/consultas/06_promedio_zona.js");
load("mongo/consultas/16_crud.js");
```

Los archivos numerados usan `smartcity`. Editar `const parametros = {}` en cada uno
para cambiar sus filtros. Tambien se pueden ejecutar por `mongosh --file`.
Se usa `load`, no `require`, para que mongosh adapte las operaciones asincronas de
su API. Los archivos de soporte se cargan mediante `cargar.js` y exponen `SC`,
`SC_CRUD`, `SC_TEST` y `SC_VALIDACION` en la sesion. Cargarlos no consulta ni cambia datos.

Para obtener un pipeline personalizado sin ejecutarlo:

```javascript
load("mongo/consultas/cargar.js");
const s = SC.construir(6, {
  desde: new Date("2026-07-01T00:00:00Z"),
  hasta: new Date("2026-08-01T00:00:00Z"),
  tipo: "calidad_aire", variable: "no2"
}, db.getSiblingDB("smartcity"));
printjson(s.pipeline);
// Ejecutar exactamente el mismo objeto:
SC.ejecutar(db.getSiblingDB("smartcity"), s);
```

La consulta 1, si no recibe `sensor`, busca el primer identificador existente en el
periodo (orden alfabetico). En una coleccion vacia devuelve una lista vacia.

## Compass

1. Conectar a `localhost:27017`, autenticacion en `admin`, usuario y clave del proyecto.
2. Abrir `smartcity` y la coleccion indicada en la tabla.
3. Para consultas `find`, copiar los campos `filtro`, `proyeccion`, `orden` y `limite`
   del descriptor de salida a **Filter**, **Project**, **Sort** y **Limit**.
4. Para agregaciones, abrir **Aggregations**, usar el modo de texto y pegar
   exclusivamente el arreglo `pipeline`, no el documento completo del informe.
5. Las fechas son BSON: usar `ISODate("2026-07-01T00:00:00Z")` en el editor que lo
   admita. Al importar JSON, mantener Extended JSON `{"$date":"..."}`; no reemplazar
   una fecha BSON por una cadena simple.

Si Compass ofrece shell integrado, cambiar su directorio de trabajo a la raiz
del checkout y usar los mismos `load`. El CRUD debe ejecutarse con `16_crud.js`
en esa shell o con el ejecutor Python; las pestañas de filtro no ejecutan scripts.
La evidencia automatizada corresponde a mongosh, no se presenta como validacion
manual realizada en la interfaz grafica de Compass.

## Catalogo y parametros

Todos los rangos usan `[desde, hasta)`. Predeterminado: julio de 2026.
Los detalles se limitan a 100; las estadisticas usan todos los datos filtrados.
`sensor`, `distrito` y fechas son opcionales en las consultas de lecturas, eventos y
alertas. En incidentes usar distrito y fechas: no existe un id_sensor en su modelo.

| N.º / archivo | Coleccion | Pregunta y parametros particulares | Resultado |
|---|---|---|---|
| 01_lecturas_sensor.js | lecturas | Lecturas de `sensor`; seleccion automatica si se omite | Crudos, fecha ascendente, calidad visible |
| 02_lecturas_fechas.js | lecturas | Lecturas del rango | Hasta 100 documentos ordenados |
| 03_extremos.js | lecturas | Minimos y maximos; `tipo`, `variable` opcionales | Estadisticas por variable/unidad |
| 04_eventos_criticos.js | eventos | Severidad critica; `tipoEvento` opcional | Eventos recientes y detalles |
| 05_alertas_zona.js | alertas | Alertas por distrito; `nivel` opcional | Cantidades por distrito/nivel |
| 06_promedio_zona.js | lecturas | Promedio; `tipo`, `variable` opcionales | Cantidad, promedio, minimo y maximo por distrito/variable |
| 07_promedio_tipo.js | lecturas | Promedio; `tipo`, `variable` opcionales | Estadisticas por tipo/variable |
| 08_incidentes_categoria.js | incidentes | Categoria y estado en `fecha_reporte` | Conteos por categoria/estado |
| 09_lecturas_por_sensor.js | lecturas | Cuantos documentos produjo cada sensor | Ranking; incluye documentos invalidos |
| 10_filtros_multiples.js | lecturas | `tipo=trafico`, `distrito=Centro`, `variable=carga`, `umbral=80` | Valores validos estrictamente superiores, ordenados |
| 11_temperatura_zona.js | lecturas | Temperatura, reutiliza la 6 | Estadisticas por zona en C |
| 12_sensores_sobre_limite.js | alertas | `valor > limite`; `variable` opcional | Conteo, maximo, primera y ultima alerta por sensor/variable |
| 13_ranking_contaminacion.js | lecturas | `tipo=calidad_aire`, `variable=no2` | Ranking por promedio; admite no2, pm10, pm25, co u o3 |
| 14_evolucion_diaria.js | lecturas | `tipo=meteorologico`, `variable=temperatura` | Serie por dia, distrito y variable |
| 15_incidentes_heridos.js | incidentes | Accidentes con `datos_extra.heridos > 0` | Detalle del campo dinamico |

Cambiar conjuntamente tipo y variable cuando corresponda. No enviar parametros que
la consulta no utilice. Las fechas deben ser `Date`, el rango no puede ser invertido
ni vacio y `limite` debe ser un entero entre 1 y 100. Se rechazan variables desconocidas.
Los resultados vacios son validos y no se sustituyen con datos ficticios.

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

| Requisito | Evidencia ejecutable |
|---|---|
| insertOne, insertMany, find, findOne, updateOne, updateMany, deleteOne | 16_crud.js / crud.js, con verificaciones y limpieza |
| Consultas obligatorias 1-10 | Archivos 01-10 |
| Aggregation Framework en 6-10 | `$match`, `$group`, `$sort`, `$project`, `$sum`, `$avg`, `$min`, `$max` |
| Flexibilidad documental | 03, 06, 07, 14: `$objectToArray` y `$unwind`; 15: datos_extra |
| Filtros, operadores logicos y de comparacion | 02, 10, 12, 15; calidad: `$and`, `$or`, `$not`, `$in` |
| `$gt`, `$gte`, `$lt`, `$exists`, `$expr` | Rango temporal, umbral estricto, campos dinamicos y comparacion entre campos |
| Proyecciones y ordenamiento | 01, 02, 04, 10, 15; orden de grupos en las demas |
| Cinco preguntas de ejemplo | Temperatura 11; limites 12; cantidad 09; contaminacion 13; evolucion 14 |
| Uso de indices | Tres `explain("executionStats")` en la validacion completa |
| 500.000 documentos o mas | Inventario real y comprobacion del volumen |
| Pruebas con datos completos | `ejecutar.py completa`, calculos independientes y dbHash |
| Seccion para persona B | SECCION_PERSONA_D.md |
| Preparacion de defensa | DEFENSA.md |

## Pruebas y limites de la evidencia

Las controladas escriben fixtures exclusivamente en una base de nombre unico
`smartcity_personad_pruebas_<uuid>`. Comprueban fronteras de fechas, grupos, tipos,
datos invalidos, umbrales, ausencia de datos, limite de detalles y CRUD repetido.
La base se elimina en `finally`. El CRUD limpia solo sus documentos, identificados
por corrida; tampoco depende de transacciones o replica sets.

La prueba completa compara agregaciones con un recorrido independiente del BSON
crudo en JavaScript. Compara conjuntos de grupos, conteos, promedios y extremos;
admite diferencia relativa de 1e-9 para aritmetica flotante. Conserva muestras de
cinco filas y compara `dbHash` e indices antes/despues. `dbHash` requiere permisos
administrativos; las consultas ordinarias solo requieren lectura.

Los indices y benchmarks originales pertenecen a Cesar. No ejecutar automaticamente
`mongo/rendimiento/medir_mongo.py`: elimina indices para medir el antes. La validacion
de Persona D solo explica consultas y registra si el optimizador eligio un indice.
Un COLLSCAN no implica por si mismo que una agregacion sea incorrecta.

Para comprobar el arranque de los scripts en un motor limpio:

```powershell
python mongo/consultas/prueba_limpia.py --salida mongo/consultas/evidencia_limpia_nueva
```

Usa la misma imagen local del contenedor del proyecto, sin puertos publicados ni
volumenes compartidos, ejecuta fixtures y elimina su contenedor. **No equivale a
reconstruir el stack completo ni a regenerar 3 millones de lecturas.** La reproduccion
integral de la carga y `docker compose up` queda en la verificacion grupal con Cesar.

El estado final de esta implementacion se documenta en `evidencia/README.md`.
No se abre PR ni se modifica `main`; la revision de otro integrante queda pendiente.
