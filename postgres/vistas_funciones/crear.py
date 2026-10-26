import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "data" / "generators"))
from comun import conectar_pg

ARCHIVOS = ["01_vistas.sql", "02_funciones.sql"]


def main():
    con = conectar_pg()
    cur = con.cursor()
    for nombre in ARCHIVOS:
        print(nombre)
        # sin parametros, psycopg manda el archivo completo de una vez
        cur.execute((AQUI / nombre).read_text(encoding="utf-8"))
    con.commit()

    for fila in cur.execute("""
            SELECT posicion_criticidad, distrito, pct_sobre_limite, total_mediciones
            FROM mv_ranking_zonas ORDER BY posicion_criticidad, distrito LIMIT 5""").fetchall():
        print(" ", fila)
    con.close()


if __name__ == "__main__":
    main()
