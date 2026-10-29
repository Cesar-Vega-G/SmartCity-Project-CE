import re
import statistics
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "data" / "generators"))
from comun import RAIZ, conectar_pg

INDICES = ["idx_medicion_sensor_fecha", "idx_medicion_variable_fecha", "idx_sensor_tipo", "idx_sensor_ubicacion",
           "idx_sensor_organismo", "idx_ubicacion_distrito", "idx_vehiculo_ruta", "idx_ruta_estacion_estacion",
           "idx_sensor_estado", "idx_sensor_fecha_instalacion"]

CONSULTAS = [
    ("q1", "Mediciones de un sensor en marzo 2025", """
        SELECT fecha_hora, id_variable, valor
        FROM medicion
        WHERE id_sensor = 'S-00002'
          AND fecha_hora >= '2025-03-01' AND fecha_hora < '2025-04-01'"""),
    ("q2", "Ultimas 24 mediciones de NO2 de un sensor", """
        SELECT m.fecha_hora, m.valor
        FROM medicion m
        JOIN variable v ON v.id_variable = m.id_variable
        WHERE m.id_sensor = 'S-00002' AND v.nombre = 'no2'
        ORDER BY m.fecha_hora DESC
        LIMIT 24"""),
    ("q3", "Promedio de NO2 por distrito en enero 2025", """
        SELECT d.nombre, ROUND(AVG(m.valor), 2) AS promedio
        FROM medicion m
        JOIN variable v ON v.id_variable = m.id_variable
        JOIN sensor s ON s.id_sensor = m.id_sensor
        JOIN ubicacion u ON u.id_ubicacion = s.id_ubicacion
        JOIN distrito d ON d.id_distrito = u.id_distrito
        WHERE v.nombre = 'no2'
          AND m.fecha_hora >= '2025-01-01' AND m.fecha_hora < '2025-02-01'
        GROUP BY d.nombre
        ORDER BY promedio DESC"""),
    ("q4", "Horas con carga de trafico mayor a 80 en julio 2026", """
        SELECT COUNT(*)
        FROM medicion m
        JOIN variable v ON v.id_variable = m.id_variable
        WHERE v.nombre = 'carga' AND m.valor > 80
          AND m.fecha_hora >= '2026-07-01' AND m.fecha_hora < '2026-08-01'"""),
    ("q5", "Sensores sin ninguna medicion", """
        SELECT s.id_sensor, s.nombre
        FROM sensor s
        WHERE NOT EXISTS (SELECT 1 FROM medicion m WHERE m.id_sensor = s.id_sensor)"""),
]

REPETICIONES = 3


def resumen_plan(lineas):
    texto = "\n".join(lineas)
    tipos = []
    for nombre in ["Index Only Scan", "Bitmap Index Scan", "Index Scan", "Seq Scan"]:
        if nombre in texto:
            tipos.append(nombre)
            texto = texto.replace(nombre, "")
    particiones = sorted(set(re.findall(r"medicion_(\d{4}|default)", "\n".join(lineas))))
    return ", ".join(tipos), ", ".join(particiones)


def medir(cur, sql):
    tiempos = []
    lineas = []
    for _ in range(REPETICIONES):
        lineas = [f[0] for f in cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql).fetchall()]
        ms = float(re.search(r"Execution Time: ([\d.]+) ms", lineas[-1]).group(1))
        tiempos.append(ms)
    return statistics.median(tiempos), lineas


def correr(cur, etapa, carpeta):
    resultados = {}
    for clave, nombre, sql in CONSULTAS:
        ms, lineas = medir(cur, sql)
        plan, particiones = resumen_plan(lineas)
        resultados[clave] = (ms, plan, particiones)
        (carpeta / f"{clave}_{etapa}.txt").write_text(sql.strip() + "\n\n" + "\n".join(lineas), encoding="utf-8")
        print(f"  {clave} {etapa}: {ms:.1f} ms  [{plan}]")
    return resultados


def main():
    carpeta = AQUI / "planes"
    carpeta.mkdir(exist_ok=True)

    con = conectar_pg()
    con.autocommit = True
    cur = con.cursor()

    print("Quitando indices para medir el antes...")
    for idx in INDICES:
        cur.execute(f"DROP INDEX IF EXISTS {idx}")
    cur.execute("ANALYZE")

    print("Sin indices:")
    antes = correr(cur, "antes", carpeta)

    print("Creando indices (puede tardar un poco)...")
    cur.execute((AQUI / "indices.sql").read_text(encoding="utf-8"))
    cur.execute("ANALYZE")

    print("Con indices:")
    despues = correr(cur, "despues", carpeta)

    filas = ["| Consulta | Sin índice (ms) | Con índice (ms) | Mejora | Plan sin índice | Plan con índice | Particiones leídas |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for clave, nombre, _ in CONSULTAS:
        a, d = antes[clave], despues[clave]
        mejora = f"{a[0] / d[0]:.0f}x" if d[0] > 0 else "-"
        filas.append(f"| {clave}. {nombre} | {a[0]:.1f} | {d[0]:.1f} | {mejora} | {a[1]} | {d[1]} | {d[2]} |")

    tam = cur.execute("""SELECT pg_size_pretty(SUM(pg_relation_size(inhrelid)))
                         FROM pg_inherits WHERE inhparent = 'medicion'::regclass""").fetchone()[0]
    tam_idx = cur.execute("""SELECT pg_size_pretty(SUM(pg_relation_size(i.indexrelid)))
                             FROM pg_index i JOIN pg_class c ON c.oid = i.indrelid
                             WHERE c.relname LIKE 'medicion%'""").fetchone()[0]
    total = int(cur.execute("SELECT COUNT(*) FROM medicion").fetchone()[0])

    texto = ["# Rendimiento en PostgreSQL", "",
             f"Tabla `medicion`: {total:,} filas".replace(",", ".") + f"; datos: {tam}; índices: {tam_idx}.",
             f"Cada tiempo es la mediana de {REPETICIONES} ejecuciones de `EXPLAIN (ANALYZE, BUFFERS)`.",
             "Los planes completos están en `postgres/rendimiento/planes/`.", ""] + filas + [
             "", "Índices usados: `postgres/rendimiento/indices.sql`."]
    (RAIZ / "docs" / "rendimiento_postgres.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    print("\nResultados guardados en docs/rendimiento_postgres.md")
    con.close()


if __name__ == "__main__":
    main()
