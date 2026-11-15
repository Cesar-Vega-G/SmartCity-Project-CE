import streamlit as st

from conexiones import mongo, origen, pg_df

AMBIENTALES = ["no2", "pm10", "pm25", "co", "o3", "temperatura", "precipitacion", "ruido_db"]


# formato con punto de miles
def num(x, dec=0):
    if x is None:
        return "—"
    return f"{float(x):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def valor(df, col):
    v = df[col].iloc[0]
    return None if v is None else float(v)


@st.cache_data(ttl=600)
# sale de lo que calculo spark
def movilidad(desde, hasta, distritos):
    return pg_df("""
        SELECT SUM(vehiculos_hora) AS vehiculos, AVG(velocidad_urbana_kmh) AS vel_urbana,
               AVG(velocidad_m30_kmh) AS vel_m30, AVG(congestion) AS congestion, AVG(tiempo_min_km) AS tiempo
        FROM spark_kpi_movilidad
        WHERE hora >= %s AND hora < %s AND distrito = ANY(%s)""", (desde, hasta, list(distritos)))


@st.cache_data(ttl=600)
def ambiente(desde, hasta, distritos):
    df = pg_df("""
        SELECT variable, AVG(valor) AS promedio
        FROM v_medicion_detalle
        WHERE fecha_hora >= %s AND fecha_hora < %s AND distrito = ANY(%s)
          AND variable IN ('temperatura', 'humedad', 'pm25')
        GROUP BY variable""", (desde, hasta, list(distritos)))
    datos = {r.variable: float(r.promedio) for r in df.itertuples()}
    co2 = pg_df("""
        SELECT AVG(co2_ppm_estimado) AS co2 FROM spark_kpi_ambiente
        WHERE hora >= %s AND hora < %s AND distrito = ANY(%s)""", (desde, hasta, list(distritos)))
    datos["co2"] = valor(co2, "co2")
    return datos


@st.cache_data(ttl=600)
# variacion contra el periodo anterior del mismo largo
def energia(desde, hasta, distritos):
    sql = """SELECT SUM(valor) AS total FROM v_medicion_detalle
             WHERE variable = 'consumo_kwh' AND fecha_hora >= %s AND fecha_hora < %s AND distrito = ANY(%s)"""
    actual = valor(pg_df(sql, (desde, hasta, list(distritos))), "total")
    anterior = valor(pg_df(sql, (desde - (hasta - desde), desde, list(distritos))), "total")
    por_zona = pg_df("""
        SELECT distrito, ROUND(AVG(valor), 2)::float AS kwh FROM v_medicion_detalle
        WHERE variable = 'consumo_kwh' AND fecha_hora >= %s AND fecha_hora < %s AND distrito = ANY(%s)
        GROUP BY distrito ORDER BY kwh DESC""", (desde, hasta, list(distritos)))
    por_hora = pg_df("""
        SELECT EXTRACT(HOUR FROM fecha_hora)::int AS hora, ROUND(AVG(valor), 2)::float AS kwh FROM v_medicion_detalle
        WHERE variable = 'consumo_kwh' AND fecha_hora >= %s AND fecha_hora < %s AND distrito = ANY(%s)
        GROUP BY 1 ORDER BY 1""", (desde, hasta, list(distritos)))
    return actual, anterior, por_zona, por_hora


@st.cache_data(ttl=600)
def sensores(distritos, tipos):
    df = pg_df("""
        SELECT estado, COUNT(*) AS n FROM v_sensor_detalle
        WHERE distrito = ANY(%s) AND tipo_sensor = ANY(%s) GROUP BY estado""", (list(distritos), list(tipos)))
    return {r.estado: int(r.n) for r in df.itertuples()}


@st.cache_data(ttl=600)
# conteos de lecturas, alertas, eventos e incidentes
def conteos_mongo(desde, hasta, distritos, tipos):
    db = mongo()
    rango = {"$gte": desde, "$lt": hasta}
    zona = {"$in": list(distritos)}
    return {
        "lecturas": db.lecturas.count_documents({"timestamp": rango, "ubicacion.distrito": zona, "tipo": {"$in": list(tipos)}}),
        "alertas": db.alertas.count_documents({"timestamp": rango, "ubicacion.distrito": zona}),
        "alertas_amb": db.alertas.count_documents({"timestamp": rango, "ubicacion.distrito": zona, "variable": {"$in": AMBIENTALES}}),
        "picos": db.eventos.count_documents({"timestamp": rango, "ubicacion.distrito": zona, "tipo_evento": "pico_consumo"}),
        "incidentes": db.incidentes.count_documents({"fecha_reporte": rango, "ubicacion.distrito": zona}),
        "accidentes": db.incidentes.count_documents({"fecha_reporte": rango, "ubicacion.distrito": zona, "categoria": "accidente_transito"}),
    }


def mostrar(f):
    d, h, dis, tip = f["desde"], f["hasta"], tuple(f["distritos"]), tuple(f["tipos"])
    m = conteos_mongo(d, h, dis, tip)

    st.subheader("Movilidad")
    mov = movilidad(d, h, dis)
    c = st.columns(6)
    c[0].metric("Vehiculos detectados", num(valor(mov, "vehiculos")))
    c[1].metric("Velocidad urbana (est.)", f"{num(valor(mov, 'vel_urbana'), 1)} km/h")
    c[2].metric("Velocidad M30", f"{num(valor(mov, 'vel_m30'), 1)} km/h")
    c[3].metric("Congestion promedio", f"{num(valor(mov, 'congestion'), 1)} / 100")
    c[4].metric("Tiempo por km (est.)", f"{num(valor(mov, 'tiempo'), 2)} min")
    c[5].metric("Accidentes / incidentes", f"{num(m['accidentes'])} / {num(m['incidentes'])}")
    origen("Spark → PostgreSQL (spark_kpi_movilidad) · incidentes: MongoDB")

    st.subheader("Ambiente")
    amb = ambiente(d, h, dis)
    c = st.columns(5)
    c[0].metric("Temperatura promedio", f"{num(amb.get('temperatura'), 1)} °C")
    c[1].metric("Humedad", f"{num(amb.get('humedad'), 0)} %")
    c[2].metric("PM2.5 promedio", f"{num(amb.get('pm25'), 1)} µg/m³")
    c[3].metric("CO₂ (est.)", f"{num(amb.get('co2'), 1)} ppm")
    c[4].metric("Alertas ambientales", num(m["alertas_amb"]))
    origen("temperatura, humedad y PM2.5: PostgreSQL · CO₂: Spark → PostgreSQL · alertas: MongoDB")

    st.subheader("Energia")
    total, anterior, por_zona, por_hora = energia(d, h, dis)
    variacion = None if not total or not anterior else (total - anterior) / anterior * 100
    c = st.columns(2)
    c[0].metric("Consumo total", f"{num(total)} kWh",
                None if variacion is None else f"{num(variacion, 1)} % vs periodo anterior")
    c[1].metric("Picos de consumo", num(m["picos"]))
    c = st.columns(2)
    with c[0]:
        st.caption("Consumo promedio por zona (kWh)")
        if not por_zona.empty:
            st.bar_chart(por_zona.set_index("distrito")["kwh"])
    with c[1]:
        st.caption("Consumo promedio por hora del dia (kWh)")
        if not por_hora.empty:
            st.line_chart(por_hora.set_index("hora")["kwh"])
    origen("consumo: PostgreSQL · picos: MongoDB (eventos)")

    st.subheader("Sensores IoT")
    s = sensores(dis, tip)
    horas = (h - d).total_seconds() / 3600
    c = st.columns(6)
    c[0].metric("Sensores", num(sum(s.values())))
    c[1].metric("Activos", num(s.get("activo", 0)))
    c[2].metric("Inactivos / mant.", f"{num(s.get('inactivo', 0))} / {num(s.get('mantenimiento', 0))}")
    c[3].metric("Lecturas recibidas", num(m["lecturas"]))
    c[4].metric("Lecturas por hora", num(m["lecturas"] / horas, 1))
    c[5].metric("Lecturas por segundo", num(m["lecturas"] / (horas * 3600), 3))
    st.metric("Alertas generadas", num(m["alertas"]))
    origen("sensores: PostgreSQL · lecturas y alertas: MongoDB")
