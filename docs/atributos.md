# Atributos del proyecto — AF y AC

## Analisis Financiero (AF)

El atributo se aplico al organizar el trabajo del equipo y valorar el costo en
horas, memoria, almacenamiento y configuracion de las alternativas. Se reutilizaron
los datos, las consultas y la infraestructura existente, y se eligio Hadoop Streaming
con Python para resolver las preguntas sin incorporar otro servicio de consultas.
La distribucion de responsabilidades permite trabajar en paralelo y concentrar los
recursos en los requisitos del enunciado. Su impacto social potencial consiste en
apoyar decisiones municipales sobre movilidad, ambiente y energia con herramientas
que pueden ejecutarse en equipos accesibles. La retroalimentacion de la revision
del proyecto mostro que una comparacion economica o de rendimiento requiere igualar
las magnitudes procesadas: una lectura cruda no equivale a una fila por variable y
hora. Por eso los tiempos se interpretan considerando el arranque y la granularidad,
sin atribuir ahorros monetarios que no se hayan medido.

## Aprendizaje Continuo (AC)

El atributo se aplico al aprender a distinguir el almacenamiento HDFS del procesamiento
MapReduce y al relacionar esas funciones con PostgreSQL, MongoDB y Spark. La
implementacion utiliza muestras pequenas para comprobar los resultados antes de
procesar el historico, y documenta las reglas de calidad, los periodos y la ejecucion
en YARN. Su impacto social potencial es producir indicadores urbanos mas confiables
y reproducibles, cuyo significado y limitaciones puedan explicarse a otras personas.
La retroalimentacion obtenida mediante la revision del codigo y las comprobaciones
identifico la importancia de incluir empates, respetar las variables invalidas,
calcular promedios con suma y cantidad y conservar un criterio temporal consistente.
Estos hallazgos se incorporan a las pruebas y a la documentacion para facilitar que
el equipo mantenga y amplie el proyecto.
