"""Pantalla de Sebastian: ejecutar las consultas obligatorias por tecnologia."""
import json
import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from dashboard.consultas_motores import (MONGO_NOMBRES, PG_NOMBRES, SPARK_NOMBRES, ejecutar_consulta)
from hadoop.mapreduce import NOMBRES, UNIDADES
from conexiones import origen


def mostrar(f):
    st.subheader("Consultas por tecnologia")
    tecnologia = st.selectbox("Tecnologia", ["PostgreSQL", "MongoDB", "Hadoop", "Spark"], key="consulta_motor")
    nombres = {"PostgreSQL": PG_NOMBRES, "MongoDB": MONGO_NOMBRES,
               "Hadoop": list(NOMBRES.values()), "Spark": SPARK_NOMBRES}[tecnologia]
    consulta = st.selectbox("Consulta", list(range(1, len(nombres) + 1)),
                            format_func=lambda n: "{:02d}. {}".format(n, nombres[n - 1]),
                            key="consulta_id_" + tecnologia)
    filtros = dict(f)
    if (tecnologia == "PostgreSQL" and consulta == 10) or (tecnologia == "MongoDB" and consulta == 1):
        filtros["id_sensor"] = st.text_input("Sensor", "S-00002" if tecnologia == "PostgreSQL" else "S-00001",
                                             key="consulta_sensor_" + tecnologia).strip()
    if tecnologia == "Hadoop" and consulta == 5:
        filtros["id_sensor"] = st.text_input("Sensor (vacio: todos)", "", key="mr_sensor").strip()
        filtros["variable"] = st.selectbox("Variable", list(UNIDADES),
                                          index=list(UNIDADES).index("temperatura"), key="mr_variable")
    if tecnologia == "PostgreSQL":
        st.caption("1-8: catalogo completo y ausencia de actividad historica. 9: snapshot historico materializado. "
                   "10: aplica sensor y periodo; distrito y tipo no restringen la funcion.")
    elif tecnologia == "MongoDB":
        st.caption("Aplica periodo y distritos. El tipo se aplica a lecturas; eventos, alertas e incidentes no tienen ese campo. "
                   "La consulta 10 conserva el criterio de trafico y carga > 80. Los detalles muestran hasta 100 documentos.")
    elif tecnologia == "Hadoop":
        if consulta == 3:
            filtros = {}
            st.caption("Temperatura de todo el historico: esta consulta no aplica los filtros laterales.")
        else:
            if consulta != 5 and st.checkbox("Consultar todo el historico", key="mr_historico_" + str(consulta)):
                filtros.pop("desde", None)
                filtros.pop("hasta", None)
            if consulta == 4:
                filtros.pop("tipos", None)
                st.caption("Eventos: aplica periodo y distritos; el filtro de tipo de sensor no corresponde.")
            else:
                st.caption("Aplica periodo, distritos y tipos de sensor. Las cantidades cuentan documentos crudos.")
    elif not (RAIZ / "spark/consultas.py").exists():
        st.info("Pendiente de Luis: implementar las diez consultas Spark. La pantalla y el puente de ejecucion estan listos.")
    st.caption("Fechas: se conservan los valores almacenados; no se corrige la zona horaria heredada.")
    firma = json.dumps([tecnologia, consulta, filtros], default=str, sort_keys=True)
    if st.button("Ejecutar", key="ejecutar_consulta", type="primary"):
        st.session_state.pop("consulta_resultado", None)
        try:
            with st.spinner("Ejecutando {}...".format(tecnologia)):
                tabla, detalle = ejecutar_consulta(tecnologia, consulta, filtros)
            st.session_state["consulta_resultado"] = (firma, tabla, detalle)
        except Exception as exc:
            st.error(str(exc))
    resultado = st.session_state.get("consulta_resultado")
    if resultado and resultado[0] == firma:
        _, tabla, detalle = resultado
        origen(detalle["origen"])
        if tabla.empty:
            st.info("La consulta no devolvio resultados para estos parametros.")
        else:
            st.dataframe(tabla, hide_index=True, width="stretch")
        if detalle.get("vista_limitada"):
            st.caption("Vista limitada a 1.000 filas del resultado de Spark.")
        st.caption("{} filas devueltas".format(len(tabla)))
        st.json({k: v for k, v in detalle.items() if k not in ("filas", "columnas")})
