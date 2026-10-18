# SmartCity-Project-CE

Proyecto de Bases de Datos (CE-3101, TEC): SmartCity Analytics con datos abiertos de Madrid.
Avance 1: PostgreSQL + MongoDB.

## Requisitos

- Docker Desktop
- Python 3.11 o superior

## Cómo levantar todo

```
copy .env.example .env
docker compose up -d
pip install -r requirements.txt
python data/generators/catalogo.py
python data/generators/clima.py
python data/generators/cargar_mongo.py
python data/generators/cargar_postgres.py
```

Postgres queda en el puerto 5433 y Mongo en el 27017 (usuario y contraseña en `.env`).

Para medir los índices: `python postgres/rendimiento/medir_pg.py` y `python mongo/rendimiento/medir_mongo.py`. Los resultados quedan en `docs/`.

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `postgres/init` | DDL que crea las tablas (se ejecuta solo al levantar Docker) |
| `postgres/consultas` | Consultas de PostgreSQL |
| `postgres/vistas_funciones` | Vistas, vista materializada y funciones |
| `postgres/rendimiento` | Índices de PostgreSQL y script que mide con y sin índices |
| `mongo/consultas` | Consultas de MongoDB |
| `mongo/rendimiento` | Índices de MongoDB y script que mide con y sin índices |
| `data/generators` | Scripts de carga de datos |
| `data/raw` | Datos crudos (ya vienen en el repo) |
| `docs` | Contrato de datos, datos y resultados de rendimiento |
