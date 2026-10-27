# Guion de demostracion - Persona D

Duracion orientativa: 10-15 minutos. Mantener abierta la evidencia, los scripts
y una sesion de mongosh autenticada; disponer de Compass para inspeccion visual.

1. **Conexion y volumen (1 min).** Ejecutar 00_comprobar.js. Mostrar version,
   colecciones, fechas y conteos reales. Distinguir datos del proyecto y base de pruebas.
2. **Modelo (1 min).** Mostrar una lectura con varias variables, un evento con detalles,
   una alerta con limite y un incidente con datos_extra. Explicar que id_sensor se
   comparte con PostgreSQL y que distrito se duplica para consultar sin joins continuos.
3. **CRUD (2 min).** Ejecutar 16_crud.js. Explicar las siete operaciones, las cantidades
   verificadas y la limpieza. La demostracion no altera los datos historicos.
4. **Consultas 1-5 (2 min).** Mostrar sensor, rango, extremos, eventos criticos y alertas
   por zona. Senalar inicio incluido, fin excluido y los dos campos de criticidad.
5. **Consultas 6-10 (3 min).** Recorrer los pipelines en lib.js. Explicar `$objectToArray`,
   `$unwind`, filtro de calidad, agrupacion por variable/unidad y proyecciones.
   Mostrar que la 9 cuenta documentos mientras las estadisticas cuentan valores.
6. **Complementarias (2 min).** Mostrar temperatura, sensores sobre el limite, ranking
   de NO2, evolucion diaria e incidentes con personas heridas. Cambiar un parametro
   de distrito o fechas y observar el cambio real de resultados.
7. **Rendimiento y pruebas (2 min).** Mostrar un explain con indice y documentos
   examinados, los resultados del validador y los hashes de integridad. Distinguir
   el benchmark original de Cesar de las mediciones de estas consultas.

## Preguntas que debemos poder responder

**Por que MongoDB?** Las lecturas comparten sensor, ubicacion y tiempo, pero sus
mediciones varian. Incidentes y eventos contienen detalles propios de su categoria.
Mongo permite mantener esos documentos y agregarlos; conservar JSON solamente no
seria suficiente para justificarlo.

**Por que mantener PostgreSQL?** Los catalogos, relaciones y resultados limpios
requieren integridad relacional. Mongo conserva detalle crudo y estructura variable.
Duplicar distrito facilita lectura pero exige mantener coherencia en la ingesta.

**Que pasa con una lectura parcialmente mala?** Un campo marcado en invalidos se
excluye; otros campos numericos sanos pueden contribuir. Si valido es falso y no hay
detalle de variables invalidas, no hay evidencia suficiente para usarla estadisticamente.

**Un promedio mayor significa una zona peor?** Solo para la variable, unidad y periodo
elegidos, y con la cobertura observada. No demuestra causalidad ni combina contaminantes.

**Que ocurre con valores ausentes?** No son ceros. No se imputan; se informa cantidad
de muestras. Esto evita fabricar continuidad en una serie temporal.

**Como trabajan las fechas?** Se filtra el valor BSON almacenado. La carga original
no incorpora explicitamente la zona de Madrid; la limitacion esta documentada y
no se corrige sumando horas arbitrariamente dentro de cada consulta.

**Que aportan los indices?** Reducen documentos examinados cuando coinciden con
filtros selectivos. Una agregacion amplia puede leer muchos documentos aun con indice.
La evidencia registra el plan real, no promete que cada consulta use IXSCAN.

**Esta base esta distribuida?** El despliegue actual contiene un solo servicio MongoDB.
No demuestra replica sets, sharding ni tolerancia a fallos. El volumen tampoco basta
para demostrar distribucion. Esas capacidades deben explicarse sin atribuirlas a esta instancia.

**Que pasa si crece 100 veces?** Revisariamos volumen, cardinalidad, indices, retencion,
coste de almacenamiento y consultas, y evaluariamos particion distribuida segun patrones
de acceso. Hadoop y Spark cubriran procesamiento historico masivo en siguientes avances;
no se implementan ni se afirman probados en este sprint.

**Que entrega Persona D a B y Cesar?** A B: seccion tecnica, cobertura y evidencia.
A Cesar: resultados de explain y observacion sobre zona horaria. La revision de PR
y la prueba completa del stack desde cero son tareas de cierre grupal posteriores.
