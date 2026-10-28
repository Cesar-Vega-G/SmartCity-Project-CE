# Guion de demostracion — Persona D

Duracion orientativa: 10–15 minutos. Abrir Compass, los pipelines y la evidencia.

1. **Conexion y volumen.** Abrir smartcity; mostrar las cuatro colecciones y repetir
   el conteo exacto de VERIFICACION.md. Explicar cliente Compass y servidor Docker.
2. **Modelo.** En Documents mostrar medicion, ubicacion y datos_extra; explicar
   id_sensor compartido con PostgreSQL y campos variables.
3. **CRUD.** Pegar crud.js en Open MongoDB Shell. Mostrar siete OK y limpieza de
   la base temporal. Explicar `$set` sobre un campo anidado.
4. **Consultas 1–5.** Abrir los pipelines en sus colecciones y pulsar Run.
   Distinguir fechas BSON, inicio incluido, fin excluido y severidad frente a nivel.
5. **Consultas 6–10.** Usar STAGES para recorrer filtro, conversion de medicion a
   pares, unwind, calidad, grupo y orden. La 9 cuenta documentos, no variables.
6. **Complementarias.** Mostrar temperatura, limites, NO2, evolucion y heridos.
   Cambiar el distrito o las fechas de una copia y explicar el resultado.
7. **Pruebas e indices.** Mostrar Explain, la evidencia historica y su alcance.
   Distinguir validacion previa de comprobaciones hechas hoy. Guardar los pipelines
   desde Save y mostrar que quedan disponibles en My Queries localmente.

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
