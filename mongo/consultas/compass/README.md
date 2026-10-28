# Pipelines para Compass

Las quince consultas de esta carpeta se pegan completas en **Aggregations → TEXT**.
La coleccion de cada archivo y todos los pasos estan en la [guia principal](../README.md).
Esta es la unica version editable de las consultas; no hay que generar estos archivos.

[validacion.json](validacion.json) conserva la comprobacion historica de equivalencia
15/15 sobre MongoDB 7.0.45, con hashes SHA-256 y datos intactos. El validador usado
entonces fue retirado al simplificar el proyecto. Los pipelines no cambiaron.
La consulta 13 tambien se ejecuto en Compass 1.53.2 y devolvio 16 resultados.
Su guardado local en aquella computadora no instala consultas en otras computadoras.

Para repetir comprobaciones: [VERIFICACION.md](../VERIFICACION.md).
