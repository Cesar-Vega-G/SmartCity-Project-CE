# Vistas y funciones de PostgreSQL

Consultas obligatorias 9 (vistas) y 10 (funciones y procedimientos).

## Cómo crearlas

Después de cargar los datos (`cargar_postgres.py`):

```
python postgres/vistas_funciones/crear.py
```

Ejecuta `01_vistas.sql` y `02_funciones.sql` y muestra las primeras filas del ranking.
También se pueden abrir y ejecutar los dos archivos en DBeaver, en ese orden.
Se pueden volver a correr sin problema.

Si se recargan las mediciones, hay que recalcular la vista materializada:
`CALL sp_refrescar_ranking_zonas();`

## Qué hay

| Objeto | Tipo | Para qué |
| --- | --- | --- |
| `v_sensor_detalle` | vista | Sensor con tipo, categoría, organismo, ubicación y distrito |
| `v_medicion_detalle` | vista | Medición con variable, unidad, límite, distrito y si pasó el límite |
| `mv_ranking_zonas` | vista materializada | Ranking de distritos por criticidad (% sobre el límite) y por actividad |
| `fn_nivel_alerta(valor, limite)` | función escalar | normal / advertencia / critica, misma regla que las alertas de Mongo |
| `fn_resumen_sensor(id, desde, hasta)` | función que devuelve tabla | Resumen por variable de un sensor en un período |
| `sp_actualizar_estado_sensores(fecha, horas)` | procedimiento | Marca inactivo/activo según si llegaron datos |
| `sp_refrescar_ranking_zonas(concurrente)` | procedimiento | Recalcula `mv_ranking_zonas` |

Las consultas que las usan están en `09_consulta_vistas.sql` y `10_consulta_funciones.sql`.
Cada objeto tiene arriba un comentario con qué resuelve y por qué se hizo así.

## Por qué vista normal o materializada

- Las vistas normales no guardan datos: Postgres las expande dentro de la consulta,
  así que siempre están al día y los filtros por fecha siguen podando particiones y
  usando los índices de `medicion`.
- El ranking de zonas sí se materializa: recorre las 4.6 millones de mediciones para
  dar 21 filas que solo cambian con una carga nueva. Leerlo ya calculado es inmediato,
  que es lo que necesita el dashboard.

## Notas

- Ni el procedimiento de estados ni las consultas usan `now()`: el dataset termina el
  2026-08-31, así que la fecha de referencia es un parámetro.
- `10_consulta_funciones.sql` corre el procedimiento de estados dentro de
  `BEGIN ... ROLLBACK` para no cambiar la base durante la demostración.
- `medir_pg.py` borra y crea índices, pero no toca estos objetos.
