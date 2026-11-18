"""PROPOSITO: pantalla de Sebastian para ejecutar las consultas obligatorias por motor.
Recibe: filtros compartidos del dashboard y elecciones de tecnologia, consulta y parametros.
Devuelve: elementos Streamlit con una tabla y metadatos; la funcion mostrar retorna None.
CRITERIO: las consultas se envian al motor unicamente al pulsar Ejecutar.
El resultado guardado pertenece a una combinacion concreta de consulta y filtros."""
import json
import sys
from pathlib import Path

import streamlit as st

# IMPORTACIONES: permitir que el dashboard encuentre los adaptadores y el paquete Hadoop del repo.
RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from dashboard.consultas_motores import (MONGO_NOMBRES, PG_NOMBRES, SPARK_NOMBRES, ejecutar_consulta)
from hadoop.mapreduce import NOMBRES, UNIDADES
from conexiones import origen


def mostrar(f):
    """Construir la pantalla y atender la ejecucion solicitada por el usuario.
    Recibe: f, diccionario con desde/hasta datetime, distritos y tipos del panel lateral.
    Devuelve: None; dibuja controles, mensajes, tabla y parametros en la sesion Streamlit.
    Guarda el resultado en session_state para conservarlo entre reejecuciones de la pagina."""
    # ETAPA 1: elegir motor e ID. Las claves de los controles distinguen los catalogos de cada motor.
    st.subheader("Consultas por tecnologia")
    tecnologia = st.selectbox("Tecnologia", ["PostgreSQL", "MongoDB", "Hadoop", "Spark"], key="consulta_motor")
    nombres = {"PostgreSQL": PG_NOMBRES, "MongoDB": MONGO_NOMBRES,
               "Hadoop": list(NOMBRES.values()), "Spark": SPARK_NOMBRES}[tecnologia]
    consulta = st.selectbox("Consulta", list(range(1, len(nombres) + 1)),
                            format_func=lambda n: "{:02d}. {}".format(n, nombres[n - 1]),
                            key="consulta_id_" + tecnologia)
    # ETAPA 2: copiar filtros compartidos para no modificar los de las otras secciones.
    filtros = dict(f)
    # Solo las consultas que lo necesitan muestran un sensor obligatorio.
    if (tecnologia == "PostgreSQL" and consulta == 10) or (tecnologia == "MongoDB" and consulta == 1):
        filtros["id_sensor"] = st.text_input("Sensor", "S-00002" if tecnologia == "PostgreSQL" else "S-00001",
                                             key="consulta_sensor_" + tecnologia).strip()
    # La consulta temporal permite un sensor opcional y seleccion de variable con unidad conocida.
    if tecnologia == "Hadoop" and consulta == 5:
        filtros["id_sensor"] = st.text_input("Sensor (vacio: todos)", "", key="mr_sensor").strip()
        filtros["variable"] = st.selectbox("Variable", list(UNIDADES),
                                          index=list(UNIDADES).index("temperatura"), key="mr_variable")
    # ETAPA 3: explicar y ajustar los filtros que realmente aplica cada consulta.
    if tecnologia == "PostgreSQL":
        st.caption("1-8: catalogo completo y ausencia de actividad historica. 9: snapshot historico materializado. "
                   "10: aplica sensor y periodo; distrito y tipo no restringen la funcion.")
    elif tecnologia == "MongoDB":
        st.caption("Aplica periodo y distritos. El tipo se aplica a lecturas; eventos, alertas e incidentes no tienen ese campo. "
                   "La consulta 10 conserva el criterio de trafico y carga > 80. Los detalles muestran hasta 100 documentos.")
    elif tecnologia == "Hadoop":
        if consulta == 3:
            # La pregunta de temperatura historica exige toda la carga: se ignoran los filtros laterales.
            filtros = {}
            st.caption("Temperatura de todo el historico: esta consulta no aplica los filtros laterales.")
        else:
            if consulta != 5 and st.checkbox("Consultar todo el historico", key="mr_historico_" + str(consulta)):
                # El checkbox elimina solo el periodo; los distritos y tipos seleccionados se conservan.
                filtros.pop("desde", None)
                filtros.pop("hasta", None)
            if consulta == 4:
                # Los documentos de eventos no tienen tipo de sensor: ese filtro no se aplica.
                filtros.pop("tipos", None)
                st.caption("Eventos: aplica periodo y distritos; el filtro de tipo de sensor no corresponde.")
            else:
                st.caption("Aplica periodo, distritos y tipos de sensor. Las cantidades cuentan documentos crudos.")
    elif not (RAIZ / "spark/consultas.py").exists():
        st.info("Pendiente de Luis: implementar las diez consultas Spark. La pantalla y el puente de ejecucion estan listos.")
    st.caption("Fechas: se conservan los valores almacenados; no se corrige la zona horaria heredada.")
    # ETAPA 4: identificar de forma estable la combinacion actual de motor, consulta y filtros.
    firma = json.dumps([tecnologia, consulta, filtros], default=str, sort_keys=True)
    # ETAPA 5: Streamlit reejecuta la pagina al interactuar; solo el boton inicia procesamiento.
    if st.button("Ejecutar", key="ejecutar_consulta", type="primary"):
        # Quitar la respuesta anterior antes de intentar otra ejecucion evita conservarla ante un error.
        st.session_state.pop("consulta_resultado", None)
        try:
            with st.spinner("Ejecutando {}...".format(tecnologia)):
                tabla, detalle = ejecutar_consulta(tecnologia, consulta, filtros)
            # Persistir tabla y metadatos solo si el motor termino correctamente.
            st.session_state["consulta_resultado"] = (firma, tabla, detalle)
        except Exception as exc:
            st.error(str(exc))
    # ETAPA 6: recuperar la respuesta de esta sesion y mostrarla solo si su firma coincide.
    resultado = st.session_state.get("consulta_resultado")
    if resultado and resultado[0] == firma:
        _, tabla, detalle = resultado
        # Etiquetar la tecnologia que produjo los datos, como solicita el enunciado.
        origen(detalle["origen"])
        if tabla.empty:
            st.info("La consulta no devolvio resultados para estos parametros.")
        else:
            st.dataframe(tabla, hide_index=True, width="stretch")
        if detalle.get("vista_limitada"):
            st.caption("Vista limitada a 1.000 filas del resultado de Spark.")
        st.caption("{} filas devueltas".format(len(tabla)))
        # Los datos van en la tabla; el JSON inferior muestra filtros y evidencia sin duplicar las filas.
        st.json({k: v for k, v in detalle.items() if k not in ("filas", "columnas")})
