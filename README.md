# SmartCity-Project-CE

Proyecto de Bases de Datos (CE-3101, TEC): SmartCity Analytics con datos abiertos de Madrid.
Avance 1: PostgreSQL + MongoDB.

## Requisitos

- Docker Desktop
- Python 3.11 o superior (generacion y carga inicial de datos)
- MongoDB Compass (consultas y demostracion de MongoDB)

## Cómo levantar todo

```
copy .env.example .env
docker compose up -d
pip install -r requirements.txt
python data/generators/catalogo.py
python data/generators/clima.py
python data/generators/cargar_mongo.py
python data/generators/cargar_postgres.py
python postgres/vistas_funciones/crear.py
```

Postgres queda en el puerto 5433 y Mongo en el 27017 (usuario y contraseña en `.env`).

Para medir los índices: `python postgres/rendimiento/medir_pg.py` y `python mongo/rendimiento/medir_mongo.py`. Los resultados quedan en `docs/`.

## Consultar MongoDB con Compass

Una vez cargados los datos, seguir [la guia de MongoDB](mongo/consultas/README.md):
conectar Compass, elegir la coleccion y pegar uno de los quince pipelines en
**Aggregations → TEXT → Run**. El CRUD se demuestra desde la shell integrada de
Compass con un solo archivo independiente. No hay ejecutor Python para consultas.
Cada integrante guarda sus pipelines localmente; no aparecen automaticamente al clonar.

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `postgres/init` | DDL que crea las tablas (se ejecuta solo al levantar Docker) |
| `postgres/consultas` | Consultas de PostgreSQL |
| `postgres/vistas_funciones` | Vistas, vista materializada y funciones |
| `postgres/rendimiento` | Índices de PostgreSQL y script que mide con y sin índices |
| `mongo/consultas` | Pipelines de Compass, CRUD y guia de verificacion |
| `mongo/rendimiento` | Índices de MongoDB y script que mide con y sin índices |
| `data/generators` | Scripts de carga de datos |
| `data/raw` | Datos crudos (ya vienen en el repo) |
| `docs` | Contrato de datos, datos y resultados de rendimiento |
