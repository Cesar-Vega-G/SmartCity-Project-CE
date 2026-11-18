# Evidencia — Sprint 2, Sebastian

Las verificaciones se realizan el 18 de noviembre de 2026 en esta computadora.
Los JSON distinguen resultados de la muestra conocida, historico y pruebas del dashboard.

`muestra_maximo.json`: entrada de cinco documentos, resultado A=2 y B=2; se ejecutaron
dos aplicaciones YARN para comprobar el maximo global y los empates.

`historico.json`: se genera con `python hadoop/verificar_integracion.py`. Cada entrada
registra filtros, ruta HDFS, aplicaciones YARN, duracion, numero de filas y una muestra.
Las referencias provienen de agregaciones independientes de MongoDB, con iguales
reglas de calidad y periodo. `aprobado: true` exige que coincidan las cinco preguntas.
Las salidas completas permanecen en las rutas HDFS registradas. La exportacion se
preparo con el cargador de Cesar; no se regeneraron ni recargaron las bases originales.

`consultas_bases.json`: diez consultas PostgreSQL y diez MongoDB verificadas contra
las cantidades de la carga de referencia. PostgreSQL se consulto en una transaccion
de solo lectura; los pipelines MongoDB no incluyen etapas de escritura.

`dashboard.json`: comprobaciones del dashboard completo con Streamlit AppTest:
arranque aunque falten indicadores Spark, ejecucion mediante boton, resultados reales
PostgreSQL/MongoDB y estado pendiente de las consultas Spark de Luis.

Las duraciones Hadoop incluyen la preparacion y arranque de cada trabajo; no son
un benchmark controlado ni se presentan como comparacion entre motores.
