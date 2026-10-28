# Consultas PostgreSQL — Sección de Sebastián (persona C)

## Alcance y estado de validación

Validación local del 2026-10-26T22:15:37.669714-06:00 sobre el commit `dc2b7a11db979c838e5f54c37d5c435562617973`. Las consultas 1–8 y 11–17 corresponden a persona C; las vistas, funciones y ejemplos 9–10 fueron integrados desde el trabajo de Luis mediante el PR #1.

**Resultado: 42 de 42 comprobaciones aprobadas.** Se aplicó el script de índices existente de César y se repitió la validación completa. El requisito de acceso por índice quedó comprobado localmente; la revisión grupal permanece pendiente.

Se ejecutaron 21 sentencias SELECT de los 17 archivos numerados mediante psycopg contra PostgreSQL 16.15 en Docker. No se encontró DBeaver disponible; el procedimiento manual en DBeaver queda documentado en el README. La prueba de estados se ejecutó aparte con ROLLBACK. No se reconstruyeron datos ni se cambiaron tablas o definiciones de Luis. Se instalaron los índices ya definidos en el script de César, sin modificar ese archivo ni ejecutar el programa de benchmarks.

| Dato observado | Resultado |
| --- | --- |
| Sensores | 324 |
| Distritos | 21 |
| Mediciones | 4664093 |
| Primera medición | 2024-01-01T00:00:00 |
| Última medición | 2026-08-31T23:00:00 |

La igualdad con los volúmenes de referencia comprueba tamaño y período, no una auditoría completa de calidad de la ingestión.

## Cobertura SQL

| Requisito | Ejemplos |
| --- | --- |
| SELECT, WHERE, ORDER BY | 1–8 y 11–17 |
| DISTINCT | 16 |
| INNER JOIN / LEFT JOIN | 1–2 / 3–4, 8, 12–13 |
| GROUP BY / HAVING | 3–6, 11–15 / 13 |
| COUNT, SUM, AVG, MIN, MAX | 3–6, 11–15 |
| Subconsulta / CTE | 7 y 12 / 8, 12, 14 |
| Funciones de ventana | 8 y 9a: DENSE_RANK |
| Fechas | 6, 11, 14, 15, 17 |
| Vistas / funciones / procedimiento | 9a–9c / 10a–10c / 10d |
| Poda de particiones | 17: solo medicion_2025 |
| Acceso por índice | Comprobado en 17: medicion_2025_id_sensor_fecha_hora_idx |

## Consultas, resultados e interpretación

Las tablas siguientes muestran las primeras tres filas de cada resultado, no el resultado completo. Las columnas completas y hasta cinco filas se conservan en [validacion.json](evidencia_con_indices/validacion.json). Los SQL enlazados contienen la pregunta, el criterio y la justificación detallados.

### 01. Sensores por tipo

**SQL:** [01_sensores_por_tipo.sql](01_sensores_por_tipo.sql). **Parámetros:** Sin filtros.

**Criterio y justificación:** INNER JOIN obtiene el tipo usando la FK obligatoria; conserva una fila por sensor.

**Resultado observado:** 324 filas. Es un inventario de sensores de todos los estados, no un conteo de lecturas.

| id_sensor | tipo_sensor | estado |
| --- | --- | --- |
| S-00004 | calidad_aire | activo |
| S-00008 | calidad_aire | activo |
| S-00012 | calidad_aire | activo |

### 02. Sensores por ubicación

**SQL:** [02_sensores_por_ubicacion.sql](02_sensores_por_ubicacion.sql). **Parámetros:** Sin filtros.

**Criterio y justificación:** JOIN recorre sensor, ubicación y distrito; el identificador distingue ubicaciones homónimas.

**Resultado observado:** 324 filas. Cada sensor conserva su punto específico y su distrito.

| id_sensor | id_ubicacion | nombre_zona | distrito |
| --- | --- | --- | --- |
| S-00119 | 56 | 13XC97PM01 | Arganzuela |
| S-00122 | 59 | AV PLANETARIO O-E(SALIDA TUNEL) | Arganzuela |
| S-00128 | 65 | BATALLA DEL SALADO N-S(CANARIAS-FERROCARRIL) | Arganzuela |

### 03. Sensores por estado

**SQL:** [03_sensores_por_estado.sql](03_sensores_por_estado.sql). **Parámetros:** activo, inactivo, mantenimiento.

**Criterio y justificación:** VALUES y LEFT JOIN conservan los tres estados, incluso con cero; COUNT(id_sensor) evita contar filas vacías.

**Resultado observado:** 3 filas. El estado del catálogo no prueba por sí solo si existen mediciones.

| estado | cantidad_sensores |
| --- | --- |
| activo | 304 |
| inactivo | 11 |
| mantenimiento | 9 |

### 04. Sensores por organismo

**SQL:** [04_sensores_por_organismo.sql](04_sensores_por_organismo.sql). **Parámetros:** Sin filtros.

**Criterio y justificación:** LEFT JOIN desde organismo incluye organismos sin sensores, con cantidad cero.

**Resultado observado:** 4 filas. Muestra la distribución administrativa; la suma coincide con el catálogo.

| nombre_organismo | cantidad_sensores |
| --- | --- |
| Ayuntamiento de Madrid - Movilidad | 237 |
| Ayuntamiento de Madrid - Calidad del Aire | 66 |
| Distribuidora Electrica Madrid | 21 |

### 05. Ubicaciones con más sensores

**SQL:** [05_ubicaciones_con_mas_sensores.sql](05_ubicaciones_con_mas_sensores.sql). **Parámetros:** Todos los estados; sin LIMIT.

**Criterio y justificación:** GROUP BY por identificador de ubicación y distrito evita unir puntos con el mismo nombre.

**Resultado observado:** 261 filas. Compara puntos de instalación; no equivale al ranking de distritos.

| id_ubicacion | nombre_zona | distrito | cantidad_sensores |
| --- | --- | --- | --- |
| 25 | Centro de control Centro | Centro | 4 |
| 26 | Centro de control Arganzuela | Arganzuela | 4 |
| 27 | Centro de control Retiro | Retiro | 4 |

### 06. Instalaciones por año

**SQL:** [06_instalaciones_por_anio.sql](06_instalaciones_por_anio.sql). **Parámetros:** Todos los años registrados.

**Criterio y justificación:** EXTRACT usa fecha_instalacion; GROUP BY cuenta sensores y ORDER BY ordena cronológicamente.

**Resultado observado:** 22 filas. Los años de instalación pueden preceder al período de mediciones.

| anio | cantidad_sensores |
| --- | --- |
| 1998 | 9 |
| 1999 | 2 |
| 2001 | 1 |

### 07. Sensores sin actividad registrada

**SQL:** [07_sensores_sin_actividad.sql](07_sensores_sin_actividad.sql). **Parámetros:** Toda la historia disponible en PostgreSQL.

**Criterio y justificación:** NOT EXISTS detecta sensores sin filas de medicion, incluidas sus particiones.

**Resultado observado:** 9 filas. Los nueve sensores no tienen mediciones válidas cargadas; esto no demuestra ausencia de lecturas crudas en MongoDB.

| id_sensor | tipo_sensor | estado |
| --- | --- | --- |
| S-00079 | estacionamiento | mantenimiento |
| S-00082 | medidor_energia | mantenimiento |
| S-00088 | ruido | mantenimiento |

### 08. Ranking de distritos por sensores

**SQL:** [08_ranking_distritos.sql](08_ranking_distritos.sql). **Parámetros:** Todos los distritos y estados.

**Criterio y justificación:** La CTE separa conteo y ranking; LEFT JOIN conserva ceros; DENSE_RANK respeta empates sin saltos.

**Resultado observado:** 21 filas. La posición mide cobertura por cantidad de sensores, no contaminación.

| posicion | distrito | total_sensores | sensores_activos |
| --- | --- | --- | --- |
| 1 | Fuencarral-El Pardo | 18 | 17 |
| 2 | Barajas | 17 | 17 |
| 2 | Carabanchel | 17 | 15 |

### 09a. Ranking materializado de zonas

**SQL:** [09_consulta_vistas.sql](../vistas_funciones/09_consulta_vistas.sql). **Parámetros:** Toda la historia; snapshot existente comprobado contra las tablas.

**Criterio y justificación:** La vista materializada guarda agregados y tres rankings; el porcentaje usa solo mediciones de variables con límite.

**Resultado observado:** 21 filas. Sensores, actividad y criticidad son criterios distintos. La criticidad combina excedencias de distintas variables y no es un índice sanitario oficial.

| posicion_criticidad | distrito | pct_sobre_limite | posicion_sensores | total_sensores |
| --- | --- | --- | --- | --- |
| 1 | Carabanchel | 2.161 | 2 | 17 |
| 2 | Moratalaz | 1.911 | 2 | 17 |
| 3 | Puente de Vallecas | 1.857 | 4 | 15 |

### 09b. Contaminación por distrito mediante vista

**SQL:** [09_consulta_vistas.sql](../vistas_funciones/09_consulta_vistas.sql). **Parámetros:** NO2; [2025-01-01, 2025-02-01).

**Criterio y justificación:** La vista aporta uniones y límite; AVG y MAX agregan solo NO2; FILTER cuenta excedencias.

**Resultado observado:** 16 filas. horas_medidas y horas_sobre_limite cuentan registros sensor-hora de NO2: varias estaciones pueden contribuir a una misma hora.

| distrito | horas_medidas | promedio_no2 | horas_sobre_limite |
| --- | --- | --- | --- |
| Villaverde | 735 | 39.95 | 0 |
| Salamanca | 734 | 39.50 | 0 |
| Carabanchel | 1471 | 37.61 | 0 |

### 09c. Organismo, categoría y estados mediante vista

**SQL:** [09_consulta_vistas.sql](../vistas_funciones/09_consulta_vistas.sql). **Parámetros:** Todos los sensores.

**Criterio y justificación:** Agrupa v_sensor_detalle por organismo y categoría; FILTER separa los tres estados.

**Resultado observado:** 4 filas. Cada categoría conserva el reparto de estados, sin multiplicar sensores por sus mediciones.

| organismo | categoria | total_sensores | activos | inactivos | en_mantenimiento |
| --- | --- | --- | --- | --- | --- |
| Ayuntamiento de Madrid - Calidad del Aire | ambiente | 66 | 64 | 1 | 1 |
| Ayuntamiento de Madrid - Movilidad | espacios_publicos | 21 | 19 | 1 | 1 |
| Ayuntamiento de Madrid - Movilidad | movilidad | 216 | 202 | 8 | 6 |

### 10a. Resumen parametrizado de un sensor

**SQL:** [10_consulta_funciones.sql](../vistas_funciones/10_consulta_funciones.sql). **Parámetros:** S-00002; [2025-03-01, 2025-04-01).

**Criterio y justificación:** fn_resumen_sensor valida sensor y fechas y devuelve una fila por variable, con unidad y agregados.

**Resultado observado:** 5 filas. Las cinco variables suman las 3.666 mediciones de la consulta 17. Los promedios se redondean a tres decimales.

| variable | unidad | cantidad_mediciones | promedio | minimo | maximo |
| --- | --- | --- | --- | --- | --- |
| co | mg/m3 | 730 | 0.273 | 0.200 | 1.000 |
| no2 | ug/m3 | 732 | 26.480 | 6.000 | 90.000 |
| o3 | ug/m3 | 732 | 56.999 | 3.000 | 100.000 |

### 10b. Sensores de un distrito mediante función

**SQL:** [10_consulta_funciones.sql](../vistas_funciones/10_consulta_funciones.sql). **Parámetros:** Centro; también se probó centro.

**Criterio y justificación:** fn_sensores_por_distrito compara sin distinguir mayúsculas; incluye todos los estados.

**Resultado observado:** 16 filas. Un distrito inexistente genera una excepción; no se confunde con un distrito existente vacío.

| id_sensor | tipo_sensor | estado | nombre_zona |
| --- | --- | --- | --- |
| S-00009 | calidad_aire | activo | Plaza del Carmen |
| S-00027 | estacionamiento | activo | Centro de control Centro |
| S-00026 | medidor_energia | activo | Centro de control Centro |

### 10c. Mediciones altas y nivel de alerta

**SQL:** [10_consulta_funciones.sql](../vistas_funciones/10_consulta_funciones.sql). **Parámetros:** PM2.5; julio de 2026; las primeras 20.

**Criterio y justificación:** fn_nivel_alerta clasifica con > límite y > 1,5 veces el límite. Se comparó con CASE sobre tablas base.

**Resultado observado:** 20 filas. Un valor igual al límite es normal; igual a 1,5 veces es advertencia; una variable sin límite retorna sin_limite.

| fecha_hora | id_sensor | distrito | valor | nivel |
| --- | --- | --- | --- | --- |
| 2026-07-25T13:00:00 | S-00024 | Fuencarral-El Pardo | 128.000 | critica |
| 2026-07-24T22:00:00 | S-00024 | Fuencarral-El Pardo | 125.000 | critica |
| 2026-07-25T01:00:00 | S-00024 | Fuencarral-El Pardo | 121.000 | critica |

### 11. Temperatura por distrito

**SQL:** [11_temperatura_por_distrito.sql](11_temperatura_por_distrito.sql). **Parámetros:** temperatura; [2026-07-01, 2026-08-01).

**Criterio y justificación:** Filtra una variable antes de AVG, MIN y MAX; valida mediante sumas y conteos por sensor agregados después.

**Resultado observado:** 21 filas. Cada medición disponible pesa igual. No se imputan faltantes ni se mezclan unidades.

| distrito | unidad | cantidad_mediciones | temperatura_promedio | temperatura_minima | temperatura_maxima |
| --- | --- | --- | --- | --- | --- |
| Arganzuela | C | 744 | 29.3571236559139785 | 16.900 | 39.100 |
| Carabanchel | C | 744 | 29.3571236559139785 | 16.900 | 39.100 |
| Centro | C | 744 | 29.3571236559139785 | 16.900 | 39.100 |

### 12. Distritos sobre el promedio municipal

**SQL:** [12_distritos_sobre_promedio.sql](12_distritos_sobre_promedio.sql). **Parámetros:** Madrid; todos los distritos.

**Criterio y justificación:** CTE, AVG y SUM calculan promedio y total antes del filtro; una subconsulta selecciona los superiores al promedio.

**Resultado observado:** 9 filas. Los porcentajes de los nueve distritos seleccionados no tienen que sumar 100 %. El denominador municipal es 324.

| distrito | cantidad_sensores | promedio_sensores_por_distrito | total_sensores_ciudad | participacion_porcentaje |
| --- | --- | --- | --- | --- |
| Fuencarral-El Pardo | 18 | 15.4285714285714286 | 324 | 5.56 |
| Barajas | 17 | 15.4285714285714286 | 324 | 5.25 |
| Carabanchel | 17 | 15.4285714285714286 | 324 | 5.25 |

### 13. Distritos sobre un umbral

**SQL:** [13_distritos_sobre_umbral.sql](13_distritos_sobre_umbral.sql). **Parámetros:** Más de 15 sensores.

**Criterio y justificación:** HAVING filtra después de GROUP BY; la comparación es estricta.

**Resultado observado:** 9 filas. Exactamente 15 no cumple. No se interpreta el umbral como calidad de cobertura.

| distrito | cantidad_sensores |
| --- | --- |
| Fuencarral-El Pardo | 18 |
| Barajas | 17 |
| Carabanchel | 17 |

### 14. Sensores que dejaron de registrar

**SQL:** [14_sensores_que_dejaron_de_registrar.sql](14_sensores_que_dejaron_de_registrar.sql). **Parámetros:** Corte 2026-07-15; cierre exclusivo 2026-09-01.

**Criterio y justificación:** La CTE obtiene última actividad anterior al cierre; exige historia y última medición anterior al corte.

**Resultado observado:** 14 filas. Los 14 sensores tienen historia previa. Se distinguen de los nueve sin historia de la consulta 7.

| id_sensor | tipo_sensor | estado | distrito | ultima_medicion |
| --- | --- | --- | --- | --- |
| S-00019 | calidad_aire | activo | Barajas | 2024-12-31T23:00:00 |
| S-00207 | trafico | activo | Latina | 2026-06-17T01:00:00 |
| S-00201 | trafico | activo | Latina | 2026-07-01T12:00:00 |

### 15. Carga promedio por hora del día

**SQL:** [15_carga_promedio_por_hora.sql](15_carga_promedio_por_hora.sql). **Parámetros:** carga; [2026-07-01, 2026-08-01).

**Criterio y justificación:** Filtra carga y agrupa EXTRACT(HOUR) entre todos los días y sensores; no agrega variables incompatibles.

**Resultado observado:** 24 filas. Son 24 franjas horarias. La mayor carga promedio identifica una franja, no una fecha concreta ni un conteo de vehículos.

| hora_del_dia | unidad | carga_promedio | cantidad_mediciones |
| --- | --- | --- | --- |
| 14 | 0-100 | 25.2236967887687591 | 6197 |
| 15 | 0-100 | 24.2676206285253828 | 6205 |
| 13 | 0-100 | 24.0764042861746697 | 6206 |

### 16. Tipos presentes en un distrito

**SQL:** [16_tipos_de_sensor_por_distrito.sql](16_tipos_de_sensor_por_distrito.sql). **Parámetros:** Centro.

**Criterio y justificación:** DISTINCT elimina repeticiones de tipo después de relacionar distrito, ubicaciones y sensores.

**Resultado observado:** 6 filas. Centro tiene seis tipos en el catálogo; esto no implica que todos tengan actividad reciente.

| distrito | tipo_sensor |
| --- | --- |
| Centro | calidad_aire |
| Centro | estacionamiento |
| Centro | medidor_energia |

### 17. Mediciones de un sensor durante un mes

**SQL:** [17_mediciones_sensor_por_mes.sql](17_mediciones_sensor_por_mes.sql). **Parámetros:** S-00002; [2025-03-01, 2025-04-01).

**Criterio y justificación:** Igualdad por sensor y rango directo por fecha permiten poda y acceso por índice si este existe; se ordena con desempates.

**Resultado observado:** 3666 filas. Devuelve 3.666 mediciones con variables y unidades separadas. La poda funciona y el plan usa el índice medicion_2025_id_sensor_fecha_hora_idx.

| id_sensor | fecha_hora | variable | unidad | valor |
| --- | --- | --- | --- | --- |
| S-00002 | 2025-03-01T00:00:00 | no2 | ug/m3 | 18.000 |
| S-00002 | 2025-03-01T00:00:00 | pm10 | ug/m3 | 19.000 |
| S-00002 | 2025-03-01T00:00:00 | pm25 | ug/m3 | 8.000 |

### 10d. Procedimiento de estados y reversión

Se usó la referencia 2026-09-01 y una ventana de 72 horas. La selección de sensores con lecturas recientes se calculó por separado; se comparó el estado de cada identificador, no solamente los totales. Nueve sensores cambiaron temporalmente; los de mantenimiento se conservaron.

| Momento | Activos | Inactivos | Mantenimiento |
| --- | --- | --- | --- |
| Antes | 304 | 11 | 9 |
| Dentro de la transacción | 295 | 20 | 9 |
| Después de ROLLBACK | 304 | 11 | 9 |

Las pruebas de sensor inexistente, distrito inexistente, fechas invertidas, iguales y nulas produjeron las excepciones esperadas en conexiones separadas.

### Refresco del ranking

El snapshot existente coincidió con el conteo de sensores, los agregados de mediciones y los tres rankings calculados desde las tablas. No fue necesario recrearlo ni refrescarlo. La ejecución del procedimiento de refresco queda pendiente para el ensayo; su CALL final está fuera del ROLLBACK del archivo 10 y debe ejecutarse por separado, después de cerrar la sesión de lectura.

## Evidencia de acceso por índice — resuelto

Se aplicó `postgres/rendimiento/indices.sql` sin modificarlo. El script crea los índices faltantes con IF NOT EXISTS; no elimina datos ni índices. Después se repitieron las 42 comprobaciones y todas aprobaron.

La consulta 17 devuelve 3.666 filas y accede únicamente a medicion_2025 mediante el índice `medicion_2025_id_sensor_fecha_hora_idx`. EXPLAIN observó 2.835 ms en esta ejecución. Es una observación puntual, no una mediana ni una comparación controlada de rendimiento.

[Plan aprobado](evidencia_con_indices/consulta_17_explain.json). [Informe aprobado e inventario de índices](evidencia_con_indices/validacion.json).


## Límites de interpretación

- PostgreSQL contiene promedios horarios de valores válidos; MongoDB conserva documentos crudos. Los conteos y promedios entre ambos no deben compararse sin igualar limpieza, variable y granularidad.

- Estado inactivo, ausencia de historia y cese de actividad desde un corte son criterios diferentes; ninguno demuestra por sí solo una falla física.

- El período disponible termina en agosto de 2026. No usar la fecha actual para evaluar este histórico. Los TIMESTAMP se interpretan según el contrato del proyecto, en hora de Madrid, sin conversión automática.

- Una fila sensor-variable-hora no equivale a una hora única de la ciudad. Promediar carga no cuenta vehículos; intensidad está expresada en vehículos/hora.

- Las consultas cubren las diez obligatorias y siete complementarias. No se implementa aquí una medición de utilización de rutas: contar vehículos asignados sería otra magnitud.

- Las pruebas sobre la carga real no crean distritos vacíos, empates o valores frontera artificiales. Los casos aislados documentados el 22 de octubre se mantienen como evidencia histórica separada; no se presentan como nuevas pruebas en PostgreSQL 16.

## Entrega y ensayo

- [x] Integración remota y local de Luis comprobada; consultas 1–17 ejecutadas.

- [x] Resultados contrastados, errores esperados probados y estados restaurados.

- [x] Sección técnica y evidencia preparadas para incorporar al documento grupal.

- [x] Índices locales instalados desde el script de César y EXPLAIN de la 17 aprobado.

- [ ] Equipo: probar el refresco del ranking y el arranque completo desde una instalación aislada.

- [ ] Luis: incorporar esta sección al documento y confirmar recepción en el PR.

- [ ] Otro integrante: revisar el PR; equipo: ensayo y entrega del avance.

Guion de ensayo: consulta 4 para explicar LEFT JOIN y ceros; 7 frente a 14 para explicar actividad; 8 para CTE y DENSE_RANK; 9a para materialización; 10a frente a 17 para comprobar una función; 10d para transacciones. Explicar la elección PostgreSQL/MongoDB mediante granularidad, limpieza e identificador compartido. La rama también contiene infraestructura y datos previos del equipo; su incorporación a main requiere revisión de César.
