import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data" / "generators"))
from comun import conectar_mongo, conectar_pg


# una sola conexion para toda la app
@st.cache_resource
def pg():
    con = conectar_pg()
    con.autocommit = True
    return con


@st.cache_resource
def mongo():
    return conectar_mongo()


def pg_df(sql, params=None):
    with pg().cursor() as cur:
        cur.execute(sql, params)
        return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


# hdfs y spark se llaman con docker exec
def hdfs(*args):
    r = subprocess.run(["docker", "exec", "smartcity_namenode", "hdfs", "dfs", *args],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else r.stderr


def correr_spark(script):
    r = subprocess.run(["docker", "exec", "smartcity_spark_master", "/opt/spark/bin/spark-submit",
                        f"/proyecto/spark/{script}"], capture_output=True, text=True)
    return r.stdout, r.stderr


# etiqueta de fuente que pide el enunciado
def origen(texto):
    st.caption(f"Fuente: {texto}")
