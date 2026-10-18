# SmartCity-Project-CE

Proyecto de Bases de Datos (CE-3101, TEC): SmartCity Analytics con datos abiertos de Madrid.
Avance 1: PostgreSQL + MongoDB.

## Requisitos

- Docker Desktop
- Python 3.11 o superior

## Cómo levantar todo

1. Copiar las variables de entorno y levantar las bases:
   ```
   copy .env.example .env
   docker compose up -d
   ```
2. Instalar las librerías de Python:
   ```
   pip install -r requirements.txt
   ```
3. Descargar los datos crudos en `data/raw/` (ver `docs/generacion_datos.md`).
4. Correr los scripts en este orden:
   ```
   python data/generators/catalogo.py
   python data/generators/clima.py
   python data/generators/cargar_mongo.py
   python data/generators/cargar_postgres.py
   ```
5. Medir el rendimiento con y sin índices (opcional, tarda unos minutos):
   ```
   python postgres/rendimiento/medir_pg.py
   python mongo/rendimiento/medir_mongo.py
   ```
   Los resultados quedan en `docs/rendimiento_postgres.md` y `docs/rendimiento_mongo.md`.

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
| `docs` | Contrato de datos, generación de datos, infraestructura y rendimiento |
