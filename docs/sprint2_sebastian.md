# Sprint 2 — aporte de Sebastian

## Implementacion

El flujo de esta parte es MongoDB exportado -> HDFS -> Hadoop Streaming/MapReduce
-> pantalla de consultas de Streamlit. Se reutilizan la carga y los servicios de
Cesar. Las cinco preguntas, sus reglas y comandos se detallan en
[Hadoop](../hadoop/README.md). HDFS conserva datos historicos; MapReduce recorre
esos archivos en tareas y genera resultados agregados. Una consulta interactiva
selectiva sigue siendo apropiada para PostgreSQL o MongoDB; el arranque de un
trabajo batch introduce un costo que se debe reconocer en la defensa.

La pantalla `Consultas por tecnologia` incluye las diez consultas PostgreSQL,
las diez MongoDB, las cinco Hadoop y el catalogo de diez consultas Spark del
enunciado. Solo se ejecutan al pulsar Ejecutar. El resultado muestra motor,
parametros y, para Hadoop, ruta HDFS, aplicaciones YARN y duracion. Al cambiar
parametros se oculta el resultado anterior para evitar atribuirlo al filtro nuevo.

Si faltan las tablas de indicadores Spark, el dashboard muestra un aviso y permite
seguir usando las consultas. El puerto MongoDB es configurable mediante MONGO_PORT;
en esta computadora se utiliza 27018 para evitar otra instancia que responde en 27017.
Las credenciales y las bases historicas se conservan.

PostgreSQL reutiliza las consultas 1-8, la vista 9a y la funcion 10a. Las primeras
nueve mantienen su alcance historico/de catalogo; la funcion recibe sensor y periodo.
No se ejecutan los procedimientos de escritura del archivo 10. MongoDB carga los
pipelines de Compass, interpreta ISODate sin evaluar JavaScript y adapta el primer
filtro al periodo y distritos seleccionados. Los tipos solo se aplican a lecturas;
el filtro multiple conserva la condicion de trafico y carga > 80. Las agregaciones
mantienen todas sus entradas; el limite de 100 afecta solo las consultas de detalle.

## Interfaz pendiente de Luis para Spark

No estan disponibles en la base recibida las diez consultas analiticas de Luis.
La interfaz muestra esa dependencia explicitamente y no presenta datos inventados.
El puente `spark/consultas_dashboard.py` esta preparado para el siguiente contrato:

```python
# spark/consultas.py, a implementar por Luis
def ejecutar_consulta(spark, consulta, filtros):
    # consulta es un entero 1..10 del catalogo del enunciado.
    # filtros: desde/hasta ISO (fin exclusivo), distritos, tipos.
    # Devuelve un pyspark.sql.DataFrame con el resultado de la consulta elegida.
    ...
```

El puente crea la sesion mediante comun_spark, llama a esa funcion y devuelve una
tabla serializada al dashboard. Muestra hasta 1.000 filas del resultado final;
ese limite se aplica despues del procesamiento. No es necesario cambiar la pantalla
cuando se incorpore el modulo. La ejecucion Spark completa queda pendiente hasta
recibirlo y ensayarlo con Luis.

## Verificacion

```powershell
python -m unittest discover -s hadoop/tests -v
python -m unittest discover -s dashboard/tests -v
python hadoop/verificar_integracion.py
python -m streamlit run dashboard/app.py
```

Las pruebas locales comprueban conteos, empates globales, suma y cantidad,
variables parcialmente invalidas, fechas Extended JSON, limites temporales, entradas
vacias, documentos malformados y adaptacion de las consultas existentes.
La evidencia de ejecucion real debe distinguir muestras de prueba e historico y
registrar las aplicaciones YARN y la comparacion contra la misma exportacion MongoDB.

Evidencias de esta implementacion en `hadoop/evidencia/`:

- `muestra_maximo.json`: trabajo real con dos sensores empatados; dos aplicaciones YARN.
- `historico.json`: resultados y comparacion de las cinco preguntas sobre el historico.
- `consultas_bases.json`: ejecucion de las diez consultas PostgreSQL y diez MongoDB.
- `dashboard.json`: prueba del dashboard completo mediante Streamlit AppTest, incluidos
  los botones reales de PostgreSQL y MongoDB, ocultamiento de resultados anteriores y
  aviso de la dependencia Spark pendiente.

## Pendientes grupales de la revision

| Responsable | Cierre requerido |
| --- | --- |
| Luis con Cesar | Diagrama E-R y justificacion 3FN del DDL vigente en el documento final. |
| Cesar | Incluir indices PostgreSQL en la instalacion y comparar motores con granularidad equivalente. |
| Equipo | Acordar la zona horaria de ingesta y actualizar las limitaciones documentadas. |
| Luis | Entregar las diez consultas Spark y ensayar el puente de ejecucion. |
| Equipo | Revision del PR, integracion del informe, ensayo de defensa y entrega. |

Los atributos AF y AC estan en [atributos](atributos.md). Esta seccion documenta el
aporte de Sebastian; los graficos, mapa, KPIs y consultas Spark conservan sus
responsables del cronograma.
