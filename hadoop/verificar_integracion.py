"""PROPOSITO: verificar las cinco preguntas reales de Hadoop contra referencias MongoDB.
Recibe: la carga existente y las conexiones del proyecto; no requiere argumentos CLI.
Devuelve: mensajes de progreso y hadoop/evidencia/historico.json con el estado de la prueba.
EFECTOS: ejecuta trabajos YARN y crea resultados/evidencia; MongoDB solo se consulta.
PRECONDICION: MongoDB y la exportacion HDFS deben representar la misma carga de datos."""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

# IMPORTACIONES DEL PROYECTO: reutilizar las conexiones de Cesar y el ejecutor de Sebastian.
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "data/generators"))
from comun import conectar_mongo
from ejecutar_mapreduce import ejecutar


def comparar(actual, esperado):
    """Comprobar que dos tablas representan las mismas respuestas.
    Recibe: actual y esperado, listas de filas con las mismas columnas.
    Devuelve: None si coinciden; lanza AssertionError al encontrar una diferencia.
    Ordena las filas y admite tolerancia numerica por el distinto orden de sumas decimales."""
    # El orden de llegada puede cambiar entre motores; se comparan las filas ordenadas.
    actual, esperado = sorted(actual), sorted(esperado)
    assert len(actual) == len(esperado), (len(actual), len(esperado))
    for fila, referencia in zip(actual, esperado):
        assert len(fila) == len(referencia)
        for a, b in zip(fila, referencia):
            # La tolerancia evita tratar pequenas diferencias de punto flotante como errores analiticos.
            if isinstance(b, (float, int)):
                assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-7), (a, b)
            else:
                assert a == b, (a, b)


def referencias(db):
    """Obtener respuestas independientes utilizando agregaciones del motor MongoDB.
    Recibe: db, base smartcity ya conectada y con la carga historica existente.
    Devuelve: diccionario {ID: filas esperadas} para las cinco preguntas.
    La referencia temporal usa temperatura de julio de 2026; las otras usan todo el historico."""
    # REFERENCIAS 1 Y 2: contar documentos por sensor y seleccionar todos los maximos empatados.
    conteos = [[r["_id"], r["n"]] for r in db.lecturas.aggregate([
        {"$group": {"_id": "$id_sensor", "n": {"$sum": 1}}}])]
    mayor = max((r[1] for r in conteos), default=0)
    # CALIDAD: exigir temperatura numerica, no marcada invalida y calidad interpretable por variable.
    temperatura = {"medicion.temperatura": {"$type": "number"},
                   "invalidos": {"$nin": ["temperatura"]},
                   "$or": [{"valido": {"$ne": False}}, {"invalidos.0": {"$exists": True}}]}
    stats = {"n": {"$sum": 1}, "promedio": {"$avg": "$medicion.temperatura"},
             "minimo": {"$min": "$medicion.temperatura"}, "maximo": {"$max": "$medicion.temperatura"}}
    # REFERENCIA 3: una agregacion global da cantidad, promedio y extremos del historico.
    t = list(db.lecturas.aggregate([{"$match": temperatura}, {"$group": dict(stats, _id=None)}]))
    hist = [["temperatura", "C", r["n"], r["promedio"], r["minimo"], r["maximo"]] for r in t]
    # REFERENCIA 4: contar eventos por distrito desde su propia coleccion.
    eventos = [[r["_id"], r["n"]] for r in db.eventos.aggregate([
        {"$group": {"_id": "$ubicacion.distrito", "n": {"$sum": 1}}}])]
    # REFERENCIA 5: julio completo [1 de julio, 1 de agosto), agrupado por dia UTC y sensor.
    f = dict(temperatura, timestamp={"$gte": datetime(2026, 7, 1), "$lt": datetime(2026, 8, 1)})
    grupo = {"dia": {"$dateToString": {"date": "$timestamp", "format": "%Y-%m-%d", "timezone": "UTC"}},
             "sensor": "$id_sensor"}
    diarios = [[r["_id"]["dia"], r["_id"]["sensor"], "temperatura", "C",
                r["n"], r["promedio"], r["minimo"], r["maximo"]]
               for r in db.lecturas.aggregate([{"$match": f}, {"$group": dict(stats, _id=grupo)}])]
    return {1: conteos, 2: [r for r in conteos if r[1] == mayor], 3: hist, 4: eventos, 5: diarios}


def main():
    """Ejecutar el ensayo completo y registrar cada comparacion aprobada.
    Recibe: configuracion del proyecto, datos MongoDB y exportaciones HDFS disponibles.
    Devuelve: None; imprime progreso y guarda un informe JSON con resultados y aplicaciones.
    Solo marca aprobado cuando las cinco comparaciones terminan correctamente."""
    db = conectar_mongo()
    print("Calculando referencias de MongoDB sobre la carga existente...", flush=True)
    referencia = referencias(db)
    # EVIDENCIA: registrar la fecha de la comprobacion y los volumenes de la carga contrastada.
    informe = {"fecha_utc": datetime.now(timezone.utc).isoformat(),
               "datos": {"lecturas": sum(r[1] for r in referencia[1]),
                         "eventos": sum(r[1] for r in referencia[4])}, "consultas": []}
    destino = RAIZ / "hadoop/evidencia/historico.json"
    destino.parent.mkdir(exist_ok=True)
    # EJECUCION: cada pregunta pasa por el mismo ejecutor que usa el dashboard.
    for n in range(1, 6):
        print("Ejecutando consulta", n, "en YARN...", flush=True)
        filtros = {"desde": "2026-07-01", "hasta": "2026-08-01", "variable": "temperatura"} if n == 5 else {}
        resultado = ejecutar(n, filtros)
        # Comprobar todas las filas antes de marcar la consulta como correcta.
        comparar(resultado["filas"], referencia[n])
        # Guardar metadatos y una muestra pequena; el resultado completo permanece en HDFS.
        evidencia = {k: v for k, v in resultado.items() if k != "filas"}
        evidencia.update(ok=True, numero_filas=len(resultado["filas"]), muestra=resultado["filas"][:3])
        informe["consultas"].append(evidencia)
        # Mientras falte alguna consulta el informe queda aprobado=False; un fallo detiene el ensayo.
        informe["aprobado"] = len(informe["consultas"]) == 5
        destino.write_text(json.dumps(informe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Consulta", n, "OK:", len(resultado["filas"]), "filas;", resultado["segundos"], "s", flush=True)
    print("Cinco consultas verificadas. Evidencia:", destino, flush=True)


if __name__ == "__main__":
    main()
