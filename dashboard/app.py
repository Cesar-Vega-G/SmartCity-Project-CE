from datetime import date, datetime, timedelta

import streamlit as st

from conexiones import pg_df
from secciones import consultas, detalle, graficos, indicadores

st.set_page_config(page_title="SmartCity Analytics", layout="wide")
st.title("SmartCity Analytics · Madrid")


@st.cache_data(ttl=3600)
def opciones():
    distritos = pg_df("SELECT nombre FROM distrito ORDER BY nombre")["nombre"].tolist()
    tipos = pg_df("SELECT nombre FROM tipo_sensor ORDER BY nombre")["nombre"].tolist()
    return distritos, tipos


distritos, tipos = opciones()

with st.sidebar:
    st.header("Filtros")
    rango = st.date_input("Periodo", (date(2026, 7, 1), date(2026, 7, 31)),
                          min_value=date(2024, 1, 1), max_value=date(2026, 8, 31))
    sel_distritos = st.multiselect("Distrito", distritos, placeholder="Todos")
    sel_tipos = st.multiselect("Tipo de sensor", tipos, placeholder="Todos")

if len(rango) != 2:
    st.stop()

filtros = {
    "desde": datetime.combine(rango[0], datetime.min.time()),
    "hasta": datetime.combine(rango[1], datetime.min.time()) + timedelta(days=1),
    "distritos": sel_distritos or distritos,
    "tipos": sel_tipos or tipos,
}

tab1, tab2, tab3, tab4 = st.tabs(["Indicadores", "Graficos", "Mapa y detalle", "Consultas por tecnologia"])
with tab1:
    indicadores.mostrar(filtros)
with tab2:
    graficos.mostrar(filtros)
with tab3:
    detalle.mostrar(filtros)
with tab4:
    consultas.mostrar(filtros)
