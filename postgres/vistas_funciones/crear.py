# Crea en PostgreSQL las vistas, la vista materializada, las funciones y los
# procedimientos de esta carpeta. Se corre después de cargar los datos.

import sys
from pathlib import Path

# Carpeta donde está este script.
AQUI = Path(__file__).resolve().parent

# La conexión a la base la define Cesar en data/generators/comun.py. Se agrega esa
# carpeta a la lista donde Python busca módulos para poder importarla desde aquí,
# igual que hacen los scripts de rendimiento.
sys.path.insert(0, str(AQUI.parents[1] / "data" / "generators"))
from comun import conectar_pg

# El orden importa: las funciones y los procedimientos usan las vistas.
ARCHIVOS = ["01_vistas.sql", "02_funciones.sql"]


def main():
    con = conectar_pg()
    cur = con.cursor()
    for nombre in ARCHIVOS:
        print(nombre)
        # Si no se le pasan parámetros, psycopg puede mandar el archivo completo de
        # una vez aunque tenga varias instrucciones.
        cur.execute((AQUI / nombre).read_text(encoding="utf-8"))
    # Confirma todo al final: si un archivo falla, no queda nada creado a medias.
    con.commit()

    # Muestra los primeros cinco distritos del ranking como prueba rápida de que la
    # vista materializada quedó creada y con datos.
    for fila in cur.execute("""
            SELECT posicion_criticidad, distrito, pct_sobre_limite, total_mediciones
            FROM mv_ranking_zonas ORDER BY posicion_criticidad, distrito LIMIT 5""").fetchall():
        print(" ", fila)
    con.close()


if __name__ == "__main__":
    main()
